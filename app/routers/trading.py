from fastapi import APIRouter, HTTPException
from typing import List
from models import StockInfo, TradeDecision, TradeOrder
from services.stock_service import StockService
from services.news_service import NewsService
from services.ai_service import AITradingService

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
news_service = NewsService()
ai_service = AITradingService()

@router.get("/stocks/{symbol}", response_model=StockInfo)
async def get_stock_info(symbol: str):
    """Get current stock information"""
    try:
        stock_info = await stock_service.get_stock_info(symbol.upper())
        if not stock_info:
            raise HTTPException(
                status_code=404, 
                detail=f"No market data available for symbol {symbol.upper()}. Please verify the symbol is correct and markets are open."
            )
        return stock_info
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching stock data for {symbol.upper()}: {str(e)}"
        )

@router.get("/stocks", response_model=List[StockInfo])
async def get_multiple_stocks(symbols: str):
    """Get information for multiple stocks (comma-separated symbols)"""
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            raise HTTPException(status_code=400, detail="No valid symbols provided")
        
        stocks = await stock_service.get_multiple_stocks(symbol_list)
        
        if not stocks:
            raise HTTPException(
                status_code=404, 
                detail="No market data available for any of the requested symbols"
            )
        
        return stocks
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching stock data: {str(e)}"
        )

@router.post("/analyze/{symbol}", response_model=TradeDecision)
async def analyze_stock(symbol: str):
    """Analyze a stock and get AI trading recommendation"""
    try:
        # Get stock information
        stock_info = await stock_service.get_stock_info(symbol.upper())
        if not stock_info:
            raise HTTPException(
                status_code=404, 
                detail=f"No market data available for symbol {symbol.upper()}. Please verify the symbol is correct and markets are open."
            )
        
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
        
        if not decision:
            raise HTTPException(
                status_code=500, 
                detail="AI analysis failed to generate a trading decision"
            )
        
        return decision
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error analyzing stock {symbol.upper()}: {str(e)}"
        )

@router.post("/validate", response_model=dict)
async def validate_trade(order: TradeOrder):
    """Validate a trade order before execution"""
    try:
        # Basic validation
        if not order.symbol or not order.symbol.strip():
            return {"valid": False, "error": "Symbol is required"}
        
        if order.quantity <= 0:
            return {"valid": False, "error": "Quantity must be positive"}
        
        # Get current stock price and portfolio
        stock_info = await stock_service.get_stock_info(order.symbol.upper())
        if not stock_info:
            return {"valid": False, "error": f"No market data available for symbol {order.symbol.upper()}"}
        
        portfolio = await portfolio_service.get_portfolio({order.symbol.upper(): stock_info.current_price})
        execution_price = order.price if order.price and order.price > 0 else stock_info.current_price
        
        if order.action.lower() == 'buy':
            total_cost = order.quantity * execution_price
            if portfolio.cash_balance < total_cost:
                return {
                    "valid": False, 
                    "error": f"Insufficient funds. Need ${total_cost:,.2f}, have ${portfolio.cash_balance:,.2f}",
                    "available_cash": portfolio.cash_balance,
                    "required_cash": total_cost,
                    "max_affordable_shares": int(portfolio.cash_balance / execution_price)
                }
        
        elif order.action.lower() == 'sell':
            # Find current holding
            current_holding = None
            for holding in portfolio.holdings:
                if holding['symbol'] == order.symbol.upper():
                    current_holding = holding
                    break
            
            if not current_holding or current_holding['quantity'] < order.quantity:
                available_shares = current_holding['quantity'] if current_holding else 0
                return {
                    "valid": False,
                    "error": f"Insufficient shares. Need {order.quantity}, have {available_shares}",
                    "available_shares": available_shares,
                    "requested_shares": order.quantity
                }
        
        return {
            "valid": True,
            "estimated_cost": order.quantity * execution_price,
            "execution_price": execution_price,
            "current_price": stock_info.current_price
        }
        
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {str(e)}"}

@router.post("/execute", response_model=dict)
async def execute_trade(order: TradeOrder):
    """Execute a trade order"""
    try:
        # Validate order
        if not order.symbol or not order.symbol.strip():
            raise HTTPException(status_code=400, detail="Symbol is required")
        
        if order.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        
        # Get current stock price for validation
        stock_info = await stock_service.get_stock_info(order.symbol.upper())
        if not stock_info:
            raise HTTPException(
                status_code=404, 
                detail=f"No market data available for symbol {order.symbol.upper()}"
            )
        
        # Use provided price or current market price
        execution_price = order.price if order.price and order.price > 0 else stock_info.current_price
        
        # Execute the trade
        success = await portfolio_service.execute_trade(
            order.symbol.upper(),
            order.action,
            order.quantity,
            execution_price
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Trade execution failed - insufficient funds or shares")
        
        # If the order has a decision_id, mark it as executed
        if hasattr(order, 'decision_id') and order.decision_id:
            try:
                await ai_service.mark_decision_executed(order.decision_id)
            except Exception as e:
                print(f"Warning: Could not mark decision as executed: {e}")
        
        return {
            "message": "Trade executed successfully",
            "symbol": order.symbol.upper(),
            "action": order.action,
            "quantity": order.quantity,
            "price": execution_price
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error executing trade: {str(e)}"
        )
