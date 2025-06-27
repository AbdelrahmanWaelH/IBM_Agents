from fastapi import APIRouter
from typing import List, Dict
from models import Portfolio
from services.stock_service import StockService

# Try to import database service, fall back to file-based service
try:
    from services.db_portfolio_service import DatabasePortfolioService
    portfolio_service = DatabasePortfolioService()
    print("✅ Using PostgreSQL database for portfolio storage")
except Exception as e:
    print(f"⚠️  Database service unavailable: {e}")
    from services.portfolio_service import PortfolioService
    portfolio_service = PortfolioService()
    print("✅ Using file-based storage for portfolio")

router = APIRouter()
stock_service = StockService()

@router.get("/", response_model=Portfolio)
async def get_portfolio():
    """Get current portfolio status"""
    # Get current prices for all holdings
    try:
        # Try database service method first
        if hasattr(portfolio_service, 'get_holdings_symbols'):
            symbols = portfolio_service.get_holdings_symbols()
        else:
            # Fallback for file-based service
            symbols = list(portfolio_service.portfolio_data.get("holdings", {}).keys())
    except:
        symbols = []
    
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
    try:
        if hasattr(portfolio_service, 'reset_portfolio'):
            # Database service
            success = await portfolio_service.reset_portfolio()
            if success:
                return {"message": "Portfolio reset successfully"}
            else:
                return {"message": "Failed to reset portfolio"}
        else:
            # File-based service
            import os
            if os.path.exists(portfolio_service.portfolio_file):
                os.remove(portfolio_service.portfolio_file)
            portfolio_service.portfolio_data = portfolio_service._load_portfolio()
            return {"message": "Portfolio reset successfully"}
    except Exception as e:
        return {"message": f"Error resetting portfolio: {e}"}
