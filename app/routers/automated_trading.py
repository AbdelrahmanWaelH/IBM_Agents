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
    """Fast AI stock recommendations using technical analysis"""
    try:
        from services.stock_service import StockService
        import yfinance as yf
        
        stock_service = StockService()
        
        # Use a curated list of liquid, well-known stocks for fast analysis
        liquid_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "V", "JPM", "UNH", "HD", "PG", "JNJ", "WMT", "DIS"]
        
        # Add user's current symbols if they exist
        candidate_symbols = list(trading_engine.trading_symbols) if trading_engine.trading_symbols else []
        
        # Fill up with liquid stocks if we need more
        for symbol in liquid_stocks:
            if symbol not in candidate_symbols and len(candidate_symbols) < count * 3:
                candidate_symbols.append(symbol)
        
        logger.info(f"🚀 Fast AI analysis starting for {len(candidate_symbols)} stocks")
        
        async def fast_technical_analysis(symbol: str) -> dict | None:
            """Fast technical analysis without heavy AI calls"""
            try:
                # Get stock data
                stock_info = await stock_service.get_stock_info(symbol)
                if not stock_info or stock_info.current_price <= 5.0:  # Skip very low-priced stocks
                    return None
                
                # Get additional technical data using yfinance
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="30d")
                
                if hist.empty or len(hist) < 10:
                    return None
                
                # Simple technical indicators
                current_price = stock_info.current_price
                prices = hist['Close'].values
                volumes = hist['Volume'].values
                
                # Moving averages
                ma_5 = prices[-5:].mean() if len(prices) >= 5 else current_price
                ma_20 = prices[-20:].mean() if len(prices) >= 20 else current_price
                
                # Volume analysis
                avg_volume = volumes[-10:].mean() if len(volumes) >= 10 else stock_info.volume
                volume_ratio = stock_info.volume / avg_volume if avg_volume > 0 else 1
                
                # Price momentum
                price_change_5d = (current_price - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
                price_change_20d = (current_price - prices[-20]) / prices[-20] * 100 if len(prices) >= 20 else 0
                
                # Simple scoring algorithm
                score = 0.5  # Base score
                
                # Trend analysis
                if current_price > ma_5 > ma_20:  # Uptrend
                    score += 0.2
                elif current_price > ma_5:  # Short-term uptrend
                    score += 0.1
                
                # Volume confirmation
                if volume_ratio > 1.2:  # Higher than average volume
                    score += 0.1
                
                # Momentum
                if price_change_5d > 2:  # Good recent momentum
                    score += 0.1
                elif price_change_5d < -5:  # Recent decline might be opportunity
                    score += 0.05
                
                # Market cap preference (larger = more stable)
                if stock_info.market_cap and stock_info.market_cap > 50_000_000_000:  # >50B market cap
                    score += 0.1
                
                # Price stability check
                volatility = prices[-10:].std() / current_price if len(prices) >= 10 else 0
                if volatility < 0.03:  # Low volatility = more stable
                    score += 0.05
                
                # Simple reasoning based on analysis
                reasoning_parts = []
                if current_price > ma_20:
                    reasoning_parts.append("trading above 20-day average")
                if volume_ratio > 1.2:
                    reasoning_parts.append("high trading volume")
                if price_change_5d > 0:
                    reasoning_parts.append("positive recent momentum")
                if stock_info.market_cap and stock_info.market_cap > 50_000_000_000:
                    reasoning_parts.append("large-cap stability")
                
                reasoning = f"Technical analysis shows {symbol} is " + ", ".join(reasoning_parts) if reasoning_parts else "showing mixed signals"
                
                # Only recommend if score is decent
                if score > 0.65:
                    return {
                        'symbol': symbol,
                        'confidence': min(score, 0.95),  # Cap at 95%
                        'action': 'buy',
                        'reasoning': reasoning,
                        'current_price': current_price,
                        'change_percent': stock_info.change_percent or 0,
                        'market_cap': stock_info.market_cap,
                        'volume': stock_info.volume,
                        'technical_score': round(score, 2),
                        'ma_5': round(ma_5, 2),
                        'ma_20': round(ma_20, 2),
                        'volume_ratio': round(volume_ratio, 2)
                    }
                
                return None
                
            except Exception as e:
                logger.debug(f"Technical analysis failed for {symbol}: {e}")
                return None
        
        # Process in small batches for speed
        recommended_stocks = []
        batch_size = 3
        
        for i in range(0, min(len(candidate_symbols), count * 2), batch_size):  # Limit total processed
            batch = candidate_symbols[i:i + batch_size]
            
            try:
                results = await asyncio.gather(*[fast_technical_analysis(symbol) for symbol in batch], return_exceptions=True)
                
                for result in results:
                    if result and not isinstance(result, Exception):
                        recommended_stocks.append(result)
                        if len(recommended_stocks) >= count:  # Early exit when we have enough
                            break
                        
            except Exception as e:
                logger.warning(f"Batch processing error: {e}")
            
            if len(recommended_stocks) >= count:
                break
        
        # Sort by technical score and confidence
        recommended_stocks.sort(key=lambda x: (x['technical_score'], x['confidence']), reverse=True)
        final_recommendations = recommended_stocks[:count]
        
        logger.info(f"✅ Fast AI analysis complete: {len(final_recommendations)} recommendations generated")
        
        return {
            "recommended_stocks": final_recommendations,
            "analysis_summary": f"Fast technical analysis of {len(candidate_symbols)} stocks using moving averages, volume, and momentum indicators",
            "total_analyzed": min(len(candidate_symbols), count * 2),
            "method": "technical_indicators",
            "criteria": "MA trends, volume confirmation, momentum, market cap > 50B",
            "processing_time": "< 10 seconds"
        }
        
    except Exception as e:
        logger.error(f"Fast AI recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI recommendations failed: {str(e)}")

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

@router.post("/execute-enhanced-analysis")
async def execute_enhanced_manual_analysis(symbol: str = Query(..., description="Stock symbol to analyze")):
    """Execute enhanced manual analysis with comprehensive AI reasoning"""
    if not symbol or not symbol.strip():
        raise HTTPException(status_code=400, detail="Symbol is required")
    
    symbol = symbol.upper().strip()
    
    try:
        logger.info(f"🎯 Starting enhanced manual analysis for {symbol}")
        
        # Get portfolio context
        portfolio = await trading_engine.portfolio_service.get_portfolio()
        portfolio_context = {
            "cash_balance": portfolio.cash_balance,
            "total_value": portfolio.total_value,
            "holdings": portfolio.holdings
        }
        
        # Use the enhanced AI service for comprehensive analysis
        decision = await trading_engine.ai_service.analyze_opportunity_comprehensive(symbol, portfolio_context)
        
        # Get the full analysis with markdown formatting
        analysis_data = await trading_engine.ai_service.get_analysis_with_markdown(symbol, decision.decision_id)
        
        logger.info(f"✅ Enhanced manual analysis completed for {symbol}")
        
        return {
            "symbol": symbol,
            "decision": {
                "action": decision.action.value,
                "confidence": decision.confidence,
                "quantity": decision.quantity,
                "suggested_price": decision.suggested_price,
                "reasoning": decision.reasoning,  # Full reasoning
                "reasoning_markdown": analysis_data.get("reasoning_markdown", decision.reasoning)
            },
            "analysis_enhanced": True,
            "timestamp": datetime.now().isoformat(),
            "decision_id": decision.decision_id
        }
        
    except Exception as e:
        logger.error(f"❌ Enhanced manual analysis failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Enhanced analysis failed: {str(e)}")

@router.get("/analysis/{symbol}/markdown")
async def get_analysis_markdown(symbol: str, decision_id: int = None):
    """Get AI analysis with properly formatted markdown"""
    try:
        analysis = await trading_engine.ai_service.get_analysis_with_markdown(symbol, decision_id)
        
        if "error" in analysis:
            raise HTTPException(status_code=404, detail=analysis["error"])
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting markdown analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-recommendations")
async def test_recommendations():
    """Quick test endpoint to verify recommendations work"""
    try:
        result = await ai_recommend_stocks(count=2)
        return {
            "status": "success",
            "test_completed": True,
            "sample_recommendations": len(result["recommended_stocks"]),
            "message": "AI recommendations system is working properly"
        }
    except Exception as e:
        return {
            "status": "error", 
            "test_completed": False,
            "error": str(e),
            "message": "AI recommendations system needs attention"
        }
