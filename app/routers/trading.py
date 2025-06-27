from fastapi import APIRouter, HTTPException
from typing import List
from models import StockInfo, TradeDecision, TradeOrder
from services.stock_service import StockService
from services.news_service import NewsService
from services.ai_service import AITradingService
from services.db_portfolio_service import DatabasePortfolioService

router = APIRouter()

stock_service = StockService()
news_service = NewsService()
ai_service = AITradingService()
portfolio_service = DatabasePortfolioService()

@router.get("/stocks/{symbol}", response_model=StockInfo)
async def get_stock_info(symbol: str):
    """Get current stock information"""
    stock_info = await stock_service.get_stock_info(symbol.upper())
    if not stock_info:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock_info

@router.get("/stocks", response_model=List[StockInfo])
async def get_multiple_stocks(symbols: str):
    """Get information for multiple stocks (comma-separated symbols)"""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    stocks = await stock_service.get_multiple_stocks(symbol_list)
    return stocks

@router.post("/analyze/{symbol}", response_model=TradeDecision)
async def analyze_stock(symbol: str):
    """Analyze a stock and get AI trading recommendation"""
    # Get stock information
    stock_info = await stock_service.get_stock_info(symbol.upper())
    if not stock_info:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Get related news
    news_items = await news_service.get_stock_news(symbol)
    
    # Get portfolio context
    portfolio = await portfolio_service.get_portfolio()
    portfolio_context = {
        "cash_balance": portfolio.cash_balance,
        "total_value": portfolio.total_value,
        "holdings": portfolio.holdings
    }
    
    # Get AI decision
    decision = await ai_service.analyze_and_decide(stock_info, news_items, portfolio_context)
    return decision

@router.post("/execute", response_model=dict)
async def execute_trade(order: TradeOrder):
    """Execute a trade order"""
    # Get current stock price
    stock_info = await stock_service.get_stock_info(order.symbol.upper())
    if not stock_info:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Use provided price or current market price
    execution_price = order.price if order.price else stock_info.current_price
    
    # Execute the trade
    success = await portfolio_service.execute_trade(
        order.symbol.upper(),
        order.action,
        order.quantity,
        execution_price
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Trade execution failed")
    
    return {
        "message": "Trade executed successfully",
        "symbol": order.symbol.upper(),
        "action": order.action,
        "quantity": order.quantity,
        "price": execution_price
    }
