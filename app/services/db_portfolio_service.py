from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Portfolio as PortfolioModel, TradeAction
from database import get_db, Portfolio, Holding, Trade, TradeActionEnum
from config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabasePortfolioService:
    def __init__(self):
        self.db_generator = get_db()
    
    def _get_db(self) -> Session:
        return next(self.db_generator)
    
    def _ensure_portfolio_exists(self, db: Session) -> Portfolio:
        """Ensure a portfolio exists in the database"""
        portfolio = db.query(Portfolio).filter(Portfolio.id == 1).first()
        if not portfolio:
            portfolio = Portfolio(
                id=1,
                cash_balance=settings.INITIAL_BUDGET,
                total_value=settings.INITIAL_BUDGET
            )
            db.add(portfolio)
            db.commit()
            db.refresh(portfolio)
        return portfolio
    
    async def get_portfolio(self, current_prices: Dict[str, float] = None) -> PortfolioModel:
        """Get current portfolio status from database"""
        if not current_prices:
            current_prices = {}
        
        db = self._get_db()
        try:
            portfolio = self._ensure_portfolio_exists(db)
            holdings = db.query(Holding).filter(Holding.portfolio_id == 1).all()
            
            total_holdings_value = 0
            holdings_list = []
            
            for holding in holdings:
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
            
            total_value = portfolio.cash_balance + total_holdings_value
            initial_value = settings.INITIAL_BUDGET
            total_profit_loss = total_value - initial_value
            profit_loss_percent = (total_profit_loss / initial_value) * 100
            
            # Update portfolio total value
            portfolio.total_value = total_value
            portfolio.updated_at = datetime.utcnow()
            db.commit()
            
            return PortfolioModel(
                cash_balance=portfolio.cash_balance,
                total_value=total_value,
                holdings=holdings_list,
                profit_loss=total_profit_loss,
                profit_loss_percent=profit_loss_percent
            )
        finally:
            db.close()
    
    async def execute_trade(self, symbol: str, action: TradeAction, quantity: int, price: float) -> bool:
        """Execute a trade order and update database"""
        db = self._get_db()
        try:
            portfolio = self._ensure_portfolio_exists(db)
            
            if action == TradeAction.BUY:
                return self._execute_buy(db, portfolio, symbol, quantity, price)
            elif action == TradeAction.SELL:
                return self._execute_sell(db, portfolio, symbol, quantity, price)
            return False
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def _execute_buy(self, db: Session, portfolio: Portfolio, symbol: str, quantity: int, price: float) -> bool:
        """Execute buy order"""
        total_cost = quantity * price
        
        if portfolio.cash_balance < total_cost:
            logger.warning(f"Insufficient funds for buying {quantity} shares of {symbol}")
            return False
        
        # Update cash balance
        portfolio.cash_balance -= total_cost
        portfolio.updated_at = datetime.utcnow()
        
        # Update or create holding
        holding = db.query(Holding).filter(
            Holding.portfolio_id == 1,
            Holding.symbol == symbol
        ).first()
        
        if holding:
            # Calculate new average price
            total_quantity = holding.quantity + quantity
            total_cost_basis = (holding.quantity * holding.avg_price) + (quantity * price)
            new_avg_price = total_cost_basis / total_quantity
            
            holding.quantity = total_quantity
            holding.avg_price = new_avg_price
            holding.updated_at = datetime.utcnow()
        else:
            holding = Holding(
                portfolio_id=1,
                symbol=symbol,
                quantity=quantity,
                avg_price=price
            )
            db.add(holding)
        
        # Record trade
        trade = Trade(
            portfolio_id=1,
            symbol=symbol,
            action=TradeActionEnum.BUY,
            quantity=quantity,
            price=price,
            total_value=total_cost
        )
        db.add(trade)
        
        db.commit()
        return True
    
    def _execute_sell(self, db: Session, portfolio: Portfolio, symbol: str, quantity: int, price: float) -> bool:
        """Execute sell order"""
        holding = db.query(Holding).filter(
            Holding.portfolio_id == 1,
            Holding.symbol == symbol
        ).first()
        
        if not holding:
            logger.warning(f"No holdings found for {symbol}")
            return False
        
        if holding.quantity < quantity:
            logger.warning(f"Insufficient shares to sell {quantity} of {symbol}")
            return False
        
        # Update cash balance
        proceeds = quantity * price
        portfolio.cash_balance += proceeds
        portfolio.updated_at = datetime.utcnow()
        
        # Update holding
        holding.quantity -= quantity
        holding.updated_at = datetime.utcnow()
        
        if holding.quantity == 0:
            db.delete(holding)
        
        # Record trade
        trade = Trade(
            portfolio_id=1,
            symbol=symbol,
            action=TradeActionEnum.SELL,
            quantity=quantity,
            price=price,
            total_value=proceeds
        )
        db.add(trade)
        
        db.commit()
        return True
    
    async def get_trade_history(self) -> List[Dict]:
        """Get trading history from database"""
        db = self._get_db()
        try:
            trades = db.query(Trade).filter(Trade.portfolio_id == 1).order_by(Trade.timestamp.desc()).all()
            
            return [
                {
                    "symbol": trade.symbol,
                    "action": trade.action.value,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "total_value": trade.total_value,
                    "timestamp": trade.timestamp.isoformat()
                }
                for trade in trades
            ]
        finally:
            db.close()
    
    async def reset_portfolio(self) -> bool:
        """Reset portfolio to initial state"""
        db = self._get_db()
        try:
            # Delete all trades and holdings
            db.query(Trade).filter(Trade.portfolio_id == 1).delete()
            db.query(Holding).filter(Holding.portfolio_id == 1).delete()
            
            # Reset portfolio
            portfolio = db.query(Portfolio).filter(Portfolio.id == 1).first()
            if portfolio:
                portfolio.cash_balance = settings.INITIAL_BUDGET
                portfolio.total_value = settings.INITIAL_BUDGET
                portfolio.updated_at = datetime.utcnow()
            else:
                portfolio = Portfolio(
                    id=1,
                    cash_balance=settings.INITIAL_BUDGET,
                    total_value=settings.INITIAL_BUDGET
                )
                db.add(portfolio)
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error resetting portfolio: {e}")
            db.rollback()
            return False
        finally:
            db.close()
