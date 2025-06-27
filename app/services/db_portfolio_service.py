from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models import Portfolio as PortfolioModel, TradeAction
from database import get_db, Portfolio, Holding, Trade, StockPrice, SessionLocal, TradeActionEnum
from config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabasePortfolioService:
    def __init__(self):
        self.db = SessionLocal()
    
    async def get_portfolio(self, current_prices: Dict[str, float] = None) -> PortfolioModel:
        """Get current portfolio status from database"""
        if not current_prices:
            current_prices = {}
        
        try:
            # Get portfolio record
            portfolio_record = self.db.query(Portfolio).filter(Portfolio.id == 1).first()
            if not portfolio_record:
                # Initialize portfolio if it doesn't exist
                portfolio_record = Portfolio(
                    id=1,
                    cash_balance=float(settings.INITIAL_BUDGET),
                    total_value=float(settings.INITIAL_BUDGET)
                )
                self.db.add(portfolio_record)
                self.db.commit()
            
            # Get all holdings
            holdings_records = self.db.query(Holding).filter(Holding.portfolio_id == 1).all()
            
            total_holdings_value = 0
            holdings_list = []
            
            for holding in holdings_records:
                if holding.quantity > 0:  # Only include active holdings
                    current_price = current_prices.get(holding.symbol, holding.avg_price)
                    value = holding.quantity * current_price
                    total_holdings_value += value
                    
                    holdings_list.append({
                        "symbol": holding.symbol,
                        "quantity": holding.quantity,
                        "avg_price": holding.avg_price,
                        "current_price": current_price,
                        "value": value,
                        "profit_loss": (current_price - holding.avg_price) * holding.quantity
                    })
            
            total_value = portfolio_record.cash_balance + total_holdings_value
            initial_value = float(settings.INITIAL_BUDGET)
            total_profit_loss = total_value - initial_value
            profit_loss_percent = (total_profit_loss / initial_value) * 100
            
            # Update portfolio total value
            portfolio_record.total_value = total_value
            self.db.commit()
            
            return PortfolioModel(
                cash_balance=portfolio_record.cash_balance,
                total_value=total_value,
                holdings=holdings_list,
                profit_loss=total_profit_loss,
                profit_loss_percent=profit_loss_percent
            )
            
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            self.db.rollback()
            # Return default portfolio
            return PortfolioModel(
                cash_balance=float(settings.INITIAL_BUDGET),
                total_value=float(settings.INITIAL_BUDGET),
                holdings=[],
                profit_loss=0.0,
                profit_loss_percent=0.0
            )
    
    async def execute_trade(self, symbol: str, action: TradeAction, quantity: int, price: float) -> bool:
        """Execute a trade order and update database"""
        try:
            if action == TradeAction.BUY:
                return await self._execute_buy(symbol, quantity, price)
            elif action == TradeAction.SELL:
                return await self._execute_sell(symbol, quantity, price)
            return False
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            self.db.rollback()
            return False
    
    async def _execute_buy(self, symbol: str, quantity: int, price: float) -> bool:
        """Execute buy order"""
        total_cost = quantity * price
        
        # Get portfolio
        portfolio_record = self.db.query(Portfolio).filter(Portfolio.id == 1).first()
        if not portfolio_record or portfolio_record.cash_balance < total_cost:
            logger.warning(f"Insufficient funds for buying {quantity} shares of {symbol}")
            return False
        
        # Update cash balance
        portfolio_record.cash_balance -= total_cost
        
        # Update or create holding
        existing_holding = self.db.query(Holding).filter(
            Holding.portfolio_id == 1, 
            Holding.symbol == symbol
        ).first()
        
        if existing_holding:
            # Calculate new average price
            total_quantity = existing_holding.quantity + quantity
            total_cost_basis = (existing_holding.quantity * existing_holding.avg_price) + (quantity * price)
            new_avg_price = total_cost_basis / total_quantity
            
            existing_holding.quantity = total_quantity
            existing_holding.avg_price = new_avg_price
        else:
            # Create new holding
            new_holding = Holding(
                portfolio_id=1,
                symbol=symbol,
                quantity=quantity,
                avg_price=price
            )
            self.db.add(new_holding)
        
        # Record trade
        trade = Trade(
            portfolio_id=1,
            symbol=symbol,
            action=TradeActionEnum.BUY,
            quantity=quantity,
            price=price,
            total_value=total_cost
        )
        self.db.add(trade)
        
        # Store stock price
        stock_price = StockPrice(
            symbol=symbol,
            price=price
        )
        self.db.add(stock_price)
        
        self.db.commit()
        return True
    
    async def _execute_sell(self, symbol: str, quantity: int, price: float) -> bool:
        """Execute sell order"""
        # Find holding
        holding = self.db.query(Holding).filter(
            Holding.portfolio_id == 1,
            Holding.symbol == symbol
        ).first()
        
        if not holding or holding.quantity < quantity:
            logger.warning(f"Insufficient shares to sell {quantity} of {symbol}")
            return False
        
        # Get portfolio
        portfolio_record = self.db.query(Portfolio).filter(Portfolio.id == 1).first()
        
        # Update cash balance
        proceeds = quantity * price
        portfolio_record.cash_balance += proceeds
        
        # Update holding
        holding.quantity -= quantity
        if holding.quantity == 0:
            self.db.delete(holding)
        
        # Record trade
        trade = Trade(
            portfolio_id=1,
            symbol=symbol,
            action=TradeActionEnum.SELL,
            quantity=quantity,
            price=price,
            total_value=proceeds
        )
        self.db.add(trade)
        
        # Store stock price
        stock_price = StockPrice(
            symbol=symbol,
            price=price
        )
        self.db.add(stock_price)
        
        self.db.commit()
        return True
    
    async def get_trade_history(self) -> List[Dict]:
        """Get trading history from database"""
        try:
            trades = self.db.query(Trade).filter(Trade.portfolio_id == 1).order_by(desc(Trade.executed_at)).all()
            
            return [
                {
                    "symbol": trade.symbol,
                    "action": trade.action.value,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "timestamp": trade.executed_at.isoformat()
                }
                for trade in trades
            ]
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
    
    async def reset_portfolio(self) -> bool:
        """Reset portfolio to initial state"""
        try:
            # Delete all holdings and trades
            self.db.query(Holding).filter(Holding.portfolio_id == 1).delete()
            self.db.query(Trade).filter(Trade.portfolio_id == 1).delete()
            
            # Reset portfolio
            portfolio_record = self.db.query(Portfolio).filter(Portfolio.id == 1).first()
            if portfolio_record:
                portfolio_record.cash_balance = float(settings.INITIAL_BUDGET)
                portfolio_record.total_value = float(settings.INITIAL_BUDGET)
            else:
                portfolio_record = Portfolio(
                    id=1,
                    cash_balance=float(settings.INITIAL_BUDGET),
                    total_value=float(settings.INITIAL_BUDGET)
                )
                self.db.add(portfolio_record)
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error resetting portfolio: {e}")
            self.db.rollback()
            return False
    
    def get_holdings_symbols(self) -> List[str]:
        """Get list of symbols in current holdings"""
        try:
            holdings = self.db.query(Holding).filter(
                Holding.portfolio_id == 1,
                Holding.quantity > 0
            ).all()
            return [holding.symbol for holding in holdings]
        except Exception as e:
            logger.error(f"Error getting holdings symbols: {e}")
            return []
    
    def __del__(self):
        """Close database connection"""
        if hasattr(self, 'db'):
            self.db.close()
