from fastapi import APIRouter
from typing import List, Dict
from models import Portfolio
from services.db_portfolio_service import DatabasePortfolioService
from services.stock_service import StockService

router = APIRouter()
portfolio_service = DatabasePortfolioService()
stock_service = StockService()

@router.get("/", response_model=Portfolio)
async def get_portfolio():
    """Get current portfolio status"""
    # Get current prices for all holdings
    portfolio_data = portfolio_service.portfolio_data
    symbols = list(portfolio_data["holdings"].keys())
    
    current_prices = {}
    if symbols:
        stocks = await stock_service.get_multiple_stocks(symbols)
        current_prices = {stock.symbol: stock.current_price for stock in stocks}
    
    portfolio = await portfolio_service.get_portfolio(current_prices)
    return portfolio

@router.get("/history", response_model=List[Dict])
async def get_trade_history():
    """Get trading history"""
    history = await portfolio_service.get_trade_history()
    return history

@router.post("/reset")
async def reset_portfolio():
    """Reset portfolio to initial state"""
    success = await portfolio_service.reset_portfolio()
    
    if success:
        return {"message": "Portfolio reset successfully"}
    else:
        return {"message": "Failed to reset portfolio"}
