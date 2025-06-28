from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from services.ai_service import AITradingService
from services.db_portfolio_service import DatabasePortfolioService

router = APIRouter()

# Initialize services
try:
    ai_service = AITradingService()
    portfolio_service = DatabasePortfolioService()
    print("✅ Analytics services initialized")
except Exception as e:
    print(f"⚠️  Analytics services initialization failed: {e}")
    ai_service = None
    portfolio_service = None

@router.get("/ai-decisions", response_model=List[Dict])
async def get_ai_decisions(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    limit: int = Query(50, description="Number of decisions to return"),
    days: Optional[int] = Query(None, description="Filter decisions from last N days")
):
    """Get AI trading decisions with optional filtering"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="Analytics service unavailable")
    
    decisions = await ai_service.get_ai_decisions_history(symbol=symbol, limit=limit)
    
    # Filter by days if specified
    if days:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        filtered_decisions = []
        for d in decisions:
            try:
                created_at_str = d['created_at']
                decision_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if decision_time.tzinfo is None:
                    decision_time = decision_time.replace(tzinfo=timezone.utc)
                
                if decision_time >= cutoff_date:
                    filtered_decisions.append(d)
            except (ValueError, TypeError, KeyError):
                continue
        decisions = filtered_decisions
    
    return decisions

@router.get("/news-analysis", response_model=List[Dict])
async def get_news_analysis(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    limit: int = Query(50, description="Number of news items to return")
):
    """Get news analysis with sentiment"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="Analytics service unavailable")
    
    return await ai_service.get_news_analysis(symbol=symbol, limit=limit)

@router.get("/stock-analysis", response_model=List[Dict])
async def get_stock_analysis(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    limit: int = Query(50, description="Number of analysis records to return")
):
    """Get historical stock analysis data"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="Analytics service unavailable")
    
    return await ai_service.get_stock_analysis_history(symbol=symbol, limit=limit)

@router.get("/portfolio-performance")
async def get_portfolio_performance():
    """Get portfolio performance metrics"""
    if not portfolio_service:
        raise HTTPException(status_code=503, detail="Portfolio service unavailable")
    
    try:
        portfolio = await portfolio_service.get_portfolio()
        trade_history = await portfolio_service.get_trade_history()
        
        # Calculate performance metrics
        total_trades = len(trade_history)
        profitable_trades = len([t for t in trade_history if t.get('action') == 'sell' and t.get('price', 0) > 0])
        
        # Calculate win rate (simplified)
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Get trade distribution by action
        buy_trades = len([t for t in trade_history if t.get('action') == 'buy'])
        sell_trades = len([t for t in trade_history if t.get('action') == 'sell'])
        
        return {
            "portfolio_value": portfolio.total_value,
            "cash_balance": portfolio.cash_balance,
            "total_trades": total_trades,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "win_rate": round(win_rate, 2),
            "holdings_count": len(portfolio.holdings),
            "holdings": [
                {
                    "symbol": h.symbol if hasattr(h, 'symbol') else h.get('symbol', 'UNKNOWN'),
                    "quantity": h.quantity if hasattr(h, 'quantity') else h.get('quantity', 0),
                    "average_price": h.average_price if hasattr(h, 'average_price') else h.get('average_price', 0),
                    "current_value": (h.quantity if hasattr(h, 'quantity') else h.get('quantity', 0)) * (h.average_price if hasattr(h, 'average_price') else h.get('average_price', 0))
                }
                for h in portfolio.holdings
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating portfolio performance: {str(e)}")

@router.get("/sentiment-summary")
async def get_sentiment_summary(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    days: int = Query(7, description="Number of days to analyze")
):
    """Get sentiment analysis summary"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="Analytics service unavailable")
    
    news_data = await ai_service.get_news_analysis(symbol=symbol, limit=100)
    
    # Filter by days - make both datetimes timezone-aware for comparison
    from datetime import timezone
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    recent_news = []
    
    for item in news_data:
        try:
            # Parse the datetime and ensure it's timezone-aware
            analyzed_at_str = item['analyzed_at'].replace('T', ' ').replace('Z', '')
            analyzed_at = datetime.fromisoformat(analyzed_at_str)
            
            # If datetime is naive, assume UTC
            if analyzed_at.tzinfo is None:
                analyzed_at = analyzed_at.replace(tzinfo=timezone.utc)
            
            if analyzed_at >= cutoff_date:
                recent_news.append(item)
        except (ValueError, KeyError) as e:
            logger.warning(f"Error parsing date for news item: {e}")
            continue
    
    # Calculate sentiment distribution
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    for item in recent_news:
        sentiment = item.get('sentiment', 'neutral')
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1
    
    total_news = len(recent_news)
    sentiment_percentages = {
        sentiment: round((count / total_news * 100), 2) if total_news > 0 else 0
        for sentiment, count in sentiment_counts.items()
    }
    
    return {
        "total_news_items": total_news,
        "sentiment_distribution": sentiment_counts,
        "sentiment_percentages": sentiment_percentages,
        "days_analyzed": days,
        "symbol": symbol or "all"
    }

@router.get("/trading-insights")
async def get_trading_insights():
    """Get AI trading insights and patterns"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="Analytics service unavailable")
    
    try:
        decisions = await ai_service.get_ai_decisions_history(limit=100)
        
        # Analyze decision patterns
        action_counts = {"buy": 0, "sell": 0, "hold": 0}
        confidence_total = 0
        executed_count = 0
        
        for decision in decisions:
            action = decision.get('action', 'hold')
            if action in action_counts:
                action_counts[action] += 1
            
            confidence_total += decision.get('confidence', 0)
            if decision.get('was_executed'):
                executed_count += 1
        
        total_decisions = len(decisions)
        avg_confidence = confidence_total / total_decisions if total_decisions > 0 else 0
        execution_rate = (executed_count / total_decisions * 100) if total_decisions > 0 else 0
        
        return {
            "total_decisions": total_decisions,
            "action_distribution": action_counts,
            "average_confidence": round(avg_confidence, 3),
            "execution_rate": round(execution_rate, 2),
            "most_recommended_action": max(action_counts, key=action_counts.get) if action_counts else "hold"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating trading insights: {str(e)}")

@router.post("/mark-executed/{decision_id}")
async def mark_decision_executed(decision_id: int):
    """Mark an AI decision as executed"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="Analytics service unavailable")
    
    try:
        await ai_service.mark_decision_executed(decision_id)
        return {"message": f"Decision {decision_id} marked as executed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking decision as executed: {str(e)}")
