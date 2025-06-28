from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from services.automated_trading_engine import trading_engine, TradingMode
import asyncio
import logging
import random

logger = logging.getLogger(__name__)

class SymbolRequest(BaseModel):
    symbol: str

router = APIRouter()

@router.post("/start")
async def start_automated_trading(background_tasks: BackgroundTasks):
    """Start the automated trading engine"""
    if trading_engine.is_running:
        raise HTTPException(status_code=400, detail="Trading engine is already running")
    
    # Start the trading engine in the background
    background_tasks.add_task(trading_engine.start_trading)
    
    return {
        "message": "Automated trading engine started",
        "status": "running"
    }

@router.post("/stop")
async def stop_automated_trading():
    """Stop the automated trading engine"""
    if not trading_engine.is_running:
        raise HTTPException(status_code=400, detail="Trading engine is not running")
    
    await trading_engine.stop_trading()
    
    return {
        "message": "Automated trading engine stopped",
        "status": "stopped"
    }

@router.get("/status")
async def get_trading_engine_status():
    """Get the current status of the trading engine"""
    return trading_engine.get_engine_status()

@router.put("/config")
async def update_trading_config(
    max_daily_trades: int = None,
    analysis_interval: int = None,
    trading_symbols: list = None
):
    """Update trading engine configuration"""
    if trading_engine.is_running:
        raise HTTPException(status_code=400, detail="Cannot update config while engine is running")
    
    config_updated = {}
    
    try:
        if max_daily_trades is not None:
            trading_engine.update_max_daily_trades(max_daily_trades)
            config_updated["max_daily_trades"] = max_daily_trades
        
        if analysis_interval is not None:
            trading_engine.update_analysis_interval(analysis_interval)
            config_updated["analysis_interval"] = analysis_interval
        
        if trading_symbols is not None:
            if not isinstance(trading_symbols, list) or len(trading_symbols) == 0:
                raise HTTPException(status_code=400, detail="trading_symbols must be a non-empty list")
            trading_engine.update_trading_symbols(trading_symbols)
            config_updated["trading_symbols"] = trading_engine.trading_symbols
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "message": "Trading engine configuration updated",
        "updated_config": config_updated,
        "current_config": trading_engine.get_engine_status()
    }

@router.get("/symbols")
async def get_trading_symbols():
    """Get current trading symbols"""
    return {
        "symbols": trading_engine.trading_symbols,
        "count": len(trading_engine.trading_symbols)
    }

@router.put("/symbols")
async def update_trading_symbols(symbols: list[str]):
    """Update trading symbols list"""
    if trading_engine.is_running:
        raise HTTPException(status_code=400, detail="Cannot update symbols while engine is running")
    
    try:
        trading_engine.update_trading_symbols(symbols)
        return {
            "message": "Trading symbols updated successfully",
            "symbols": trading_engine.trading_symbols,
            "count": len(trading_engine.trading_symbols)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/symbols/add")
async def add_trading_symbol(request: SymbolRequest):
    """Add a new symbol to the trading list"""
    if trading_engine.is_running:
        raise HTTPException(status_code=400, detail="Cannot modify symbols while engine is running")
    
    symbol = request.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol cannot be empty")
    
    if symbol in trading_engine.trading_symbols:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} is already in the trading list")
    
    try:
        new_symbols = trading_engine.trading_symbols + [symbol]
        trading_engine.update_trading_symbols(new_symbols)
        return {
            "message": f"Symbol {symbol} added successfully",
            "symbols": trading_engine.trading_symbols,
            "count": len(trading_engine.trading_symbols)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/symbols/{symbol}")
async def remove_trading_symbol(symbol: str):
    """Remove a symbol from the trading list"""
    if trading_engine.is_running:
        raise HTTPException(status_code=400, detail="Cannot modify symbols while engine is running")
    
    symbol = symbol.strip().upper()
    if symbol not in trading_engine.trading_symbols:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found in trading list")
    
    if len(trading_engine.trading_symbols) <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last symbol. At least one symbol is required.")
    
    try:
        new_symbols = [s for s in trading_engine.trading_symbols if s != symbol]
        trading_engine.update_trading_symbols(new_symbols)
        return {
            "message": f"Symbol {symbol} removed successfully",
            "symbols": trading_engine.trading_symbols,
            "count": len(trading_engine.trading_symbols)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/recent-activity")
async def get_recent_trading_activity():
    """Get recent trading activity and decisions"""
    try:
        # Get recent AI decisions and trades from the database
        from services.ai_service import AITradingService
        from services.db_portfolio_service import DatabasePortfolioService
        
        ai_service = AITradingService()
        portfolio_service = DatabasePortfolioService()
        
        # Get recent decisions and trades
        recent_decisions = await ai_service.get_ai_decisions_history(limit=20)
        recent_trades = await portfolio_service.get_trade_history()
        
        # Filter trades from the last 24 hours
        from datetime import datetime, timedelta, timezone
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        recent_trades_24h = []
        for trade in recent_trades:
            try:
                # Handle both timezone-aware and naive timestamps
                timestamp_str = trade.get('timestamp', '2000-01-01')
                if 'T' in timestamp_str:
                    # ISO format datetime
                    trade_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if trade_time.tzinfo is None:
                        trade_time = trade_time.replace(tzinfo=timezone.utc)
                else:
                    # Fallback for simple date
                    trade_time = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
                
                if trade_time >= cutoff_time:
                    recent_trades_24h.append(trade)
            except (ValueError, TypeError):
                # Skip trades with invalid timestamps
                continue
        
        # Count decisions from today
        today_decisions_count = 0
        today_date = datetime.now(timezone.utc).date()
        
        for decision in recent_decisions:
            try:
                created_at_str = decision.get('created_at', '2000-01-01')
                decision_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if decision_time.tzinfo is None:
                    decision_time = decision_time.replace(tzinfo=timezone.utc)
                
                if decision_time.date() == today_date:
                    today_decisions_count += 1
            except (ValueError, TypeError):
                continue
        
        return {
            "recent_decisions": recent_decisions[:10],
            "recent_trades_24h": recent_trades_24h,
            "total_decisions_today": today_decisions_count,
            "total_trades_today": len(recent_trades_24h),
            "engine_status": trading_engine.get_engine_status()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recent activity: {str(e)}")

@router.post("/execute-manual-analysis")
async def execute_manual_analysis(symbol: str):
    """Manually trigger analysis for a specific symbol"""
    try:
        from services.stock_service import StockService
        from services.news_service import NewsService
        from services.ai_service import AITradingService
        from services.db_portfolio_service import DatabasePortfolioService
        
        stock_service = StockService()
        news_service = NewsService()
        ai_service = AITradingService()
        portfolio_service = DatabasePortfolioService()
        
        # Get stock information
        stock_info = await stock_service.get_stock_info(symbol.upper())
        if not stock_info:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        # Get related news and portfolio context
        news_items = await news_service.get_stock_news(symbol)
        portfolio = await portfolio_service.get_portfolio()
        portfolio_context = {
            "cash_balance": portfolio.cash_balance,
            "total_value": portfolio.total_value,
            "holdings": portfolio.holdings
        }
        
        # Get AI decision
        decision = await ai_service.analyze_and_decide(stock_info, news_items, portfolio_context)
        
        return {
            "symbol": symbol.upper(),
            "analysis_completed": True,
            "decision": {
                "action": decision.action,
                "quantity": decision.quantity,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "suggested_price": decision.suggested_price,
                "decision_id": getattr(decision, 'decision_id', None)
            },
            "stock_info": {
                "current_price": stock_info.current_price,
                "change_percent": stock_info.change_percent,
                "volume": stock_info.volume
            },
            "news_count": len(news_items)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing manual analysis: {str(e)}")

@router.post("/mode/{mode}")
async def set_trading_mode(mode: str):
    """Set the trading mode (analysis_only or full_control)"""
    if trading_engine.is_running:
        raise HTTPException(status_code=400, detail="Cannot change mode while engine is running")
    
    try:
        if mode == "analysis_only":
            trading_mode = TradingMode.ANALYSIS_ONLY
        elif mode == "full_control":
            trading_mode = TradingMode.FULL_CONTROL
        else:
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'analysis_only' or 'full_control'")
        
        trading_engine.set_trading_mode(trading_mode)
        
        return {
            "message": f"Trading mode set to {mode}",
            "mode": mode,
            "description": {
                "analysis_only": "AI will analyze stocks and portfolio but won't execute trades automatically",
                "full_control": "AI will analyze and execute trades automatically based on confidence threshold"
            }[mode]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/mode")
async def get_trading_mode():
    """Get current trading mode"""
    status = trading_engine.get_engine_status()
    return {
        "current_mode": status["trading_mode"],
        "modes": {
            "analysis_only": "AI analysis only - no automatic trades",
            "full_control": "AI makes and executes trades automatically"
        },
        "confidence_threshold": status.get("min_confidence_threshold", 0.75)
    }

@router.put("/confidence-threshold")
async def update_confidence_threshold(threshold: float):
    """Update the minimum confidence threshold for trade execution"""
    if trading_engine.is_running:
        raise HTTPException(status_code=400, detail="Cannot update confidence threshold while engine is running")
    
    try:
        trading_engine.update_confidence_threshold(threshold)
        return {
            "message": f"Confidence threshold updated to {threshold:.1%}",
            "threshold": threshold
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ai-recommend-stocks")
async def ai_recommend_stocks(count: int = 5):
    """Let AI recommend stocks for trading with comprehensive analysis like professional trading agents"""
    try:
        from services.ai_service import AITradingService
        from services.stock_service import StockService
        from services.news_service import NewsService
        
        ai_service = AITradingService()
        stock_service = StockService()
        news_service = NewsService()
        
        # Professional AI trading agent approach: Multi-tier stock universe
        # Tier 1: Large-cap stocks (most liquid and stable)
        large_cap_stocks = [
            # Technology Leaders (highest weight)
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "ORCL", "ADBE",
            # Financial Giants
            "JPM", "BAC", "V", "MA", "WFC", "GS", "MS", "BRK.B",
            # Healthcare Leaders
            "UNH", "JNJ", "PFE", "ABBV", "TMO", "ABT", "MRK", "LLY",
            # Consumer & Retail
            "WMT", "HD", "PG", "KO", "DIS", "NKE", "MCD", "COST"
        ]
        
        # Tier 2: Growth and emerging leaders
        growth_stocks = [
            "NFLX", "CRM", "PYPL", "INTC", "IBM", "CVX", "XOM", "PEP",
            "SHOP", "ROKU", "SQ", "SPOT", "ZOOM", "TWLO", "BA", "CAT"
        ]
        
        # Professional approach: Analyze both tiers with emphasis on large-cap
        large_cap_sample = random.sample(large_cap_stocks, min(15, len(large_cap_stocks)))
        growth_sample = random.sample(growth_stocks, min(10, len(growth_stocks)))
        
        # Combine for diversified analysis (70% large-cap, 30% growth)
        selected_candidates = large_cap_sample + growth_sample
        
        recommended_stocks = []
        analyzed_count = 0
        
        logger.info(f"🤖 AI RECOMMENDATIONS: Starting professional analysis of {len(selected_candidates)} stocks")
        
        for symbol in selected_candidates:
            try:
                analyzed_count += 1
                logger.info(f"📊 Analyzing {symbol} ({analyzed_count}/{len(selected_candidates)})")
                
                # Get comprehensive stock data
                stock_info = await stock_service.get_stock_info(symbol)
                if not stock_info:
                    logger.warning(f"⚠️ No data available for {symbol}")
                    continue
                
                # CRITICAL: Include news analysis for professional AI recommendations
                news_items = []
                try:
                    news_items = await news_service.get_stock_news(symbol, limit=5)
                    logger.info(f"📰 Found {len(news_items)} news items for {symbol}")
                except Exception as e:
                    logger.warning(f"Could not fetch news for {symbol}: {e}")
                
                # Get AI decision with news context (like professional trading systems)
                decision = await ai_service.analyze_and_decide(stock_info, news_items)
                
                # Professional criteria: Only recommend BUY decisions with high confidence
                if (decision.action in ['buy'] and 
                    decision.confidence > 0.65 and  # Higher threshold for recommendations
                    stock_info.current_price > 1.0):  # Avoid penny stocks
                    
                    recommended_stocks.append({
                        'symbol': symbol,
                        'confidence': decision.confidence,
                        'action': decision.action.value,
                        'reasoning': decision.reasoning,
                        'current_price': stock_info.current_price,
                        'change_percent': stock_info.change_percent or 0,
                        'market_cap': stock_info.market_cap,
                        'volume': stock_info.volume,
                        'news_articles_analyzed': len(news_items)
                    })
                    logger.info(f"✅ {symbol} recommended with {decision.confidence:.1%} confidence")
                else:
                    logger.info(f"⚠️ {symbol} not recommended: {decision.action} with {decision.confidence:.1%} confidence")
                    
            except Exception as e:
                logger.error(f"❌ Error analyzing {symbol}: {e}")
                continue
        
        # Professional sorting: Confidence first, then market cap for stability
        recommended_stocks.sort(key=lambda x: (x['confidence'], x.get('market_cap', 0)), reverse=True)
        
        # Return top recommendations with analysis summary
        final_recommendations = recommended_stocks[:count]
        
        logger.info(f"🎯 AI RECOMMENDATIONS COMPLETE: {len(final_recommendations)}/{analyzed_count} stocks recommended")
        
        return {
            "recommended_stocks": final_recommendations,
            "analysis_summary": f"AI analyzed {analyzed_count} professional-grade stocks with news sentiment. Found {len(final_recommendations)} high-confidence opportunities.",
            "total_analyzed": analyzed_count,
            "with_news_analysis": True,
            "criteria": "Large-cap focus, news-enhanced analysis, confidence > 65%"
        }
        
        return {
            "recommended_stocks": recommended_stocks[:count],
            "analysis_summary": f"AI analyzed {len(candidate_stocks)} stocks and found {len(recommended_stocks)} good opportunities",
            "total_analyzed": len(candidate_stocks)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI recommendations: {str(e)}")

@router.post("/ai-add-recommended")
async def ai_add_recommended_stocks():
    """Add AI-recommended stocks to trading list"""
    try:
        # Get AI recommendations
        recommendations_response = await ai_recommend_stocks(count=3)
        recommended_stocks = recommendations_response["recommended_stocks"]
        
        added_symbols = []
        errors = []
        
        for stock in recommended_stocks:
            symbol = stock['symbol']
            
            # Check if not already in list
            if symbol not in trading_engine.trading_symbols:
                try:
                    new_symbols = trading_engine.trading_symbols + [symbol]
                    trading_engine.update_trading_symbols(new_symbols)
                    added_symbols.append({
                        'symbol': symbol,
                        'confidence': stock['confidence'],
                        'reasoning': stock['reasoning']
                    })
                except Exception as e:
                    errors.append(f"Failed to add {symbol}: {str(e)}")
        
        return {
            "message": f"AI added {len(added_symbols)} recommended stocks",
            "added_symbols": added_symbols,
            "current_symbols": trading_engine.trading_symbols,
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add AI recommendations: {str(e)}")
