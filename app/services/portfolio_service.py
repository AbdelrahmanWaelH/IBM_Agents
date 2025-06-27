from typing import Dict, List, Optional
from models import Portfolio, TradeAction
from config import settings
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PortfolioService:
    def __init__(self):
        self.portfolio_file = "portfolio.json"
        self.portfolio_data = self._load_portfolio()
    
    def _load_portfolio(self) -> Dict:
        """Load portfolio from file or create new one"""
        try:
            if os.path.exists(self.portfolio_file):
                with open(self.portfolio_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading portfolio: {e}")
        
        # Create new portfolio with initial budget
        return {
            "cash_balance": settings.INITIAL_BUDGET,
            "holdings": {},  # symbol: {"quantity": int, "avg_price": float}
            "trade_history": []
        }
    
    def _save_portfolio(self):
        """Save portfolio to file"""
        try:
            with open(self.portfolio_file, 'w') as f:
                json.dump(self.portfolio_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving portfolio: {e}")
    
    async def get_portfolio(self, current_prices: Dict[str, float] = None) -> Portfolio:
        """Get current portfolio status"""
        if not current_prices:
            current_prices = {}
        
        total_holdings_value = 0
        holdings_list = []
        
        for symbol, holding in self.portfolio_data["holdings"].items():
            current_price = current_prices.get(symbol, holding["avg_price"])
            value = holding["quantity"] * current_price
            total_holdings_value += value
            
            holdings_list.append({
                "symbol": symbol,
                "quantity": holding["quantity"],
                "avg_price": holding["avg_price"],
                "current_price": current_price,
                "value": value,
                "profit_loss": (current_price - holding["avg_price"]) * holding["quantity"]
            })
        
        total_value = self.portfolio_data["cash_balance"] + total_holdings_value
        initial_value = settings.INITIAL_BUDGET
        total_profit_loss = total_value - initial_value
        profit_loss_percent = (total_profit_loss / initial_value) * 100
        
        return Portfolio(
            cash_balance=self.portfolio_data["cash_balance"],
            total_value=total_value,
            holdings=holdings_list,
            profit_loss=total_profit_loss,
            profit_loss_percent=profit_loss_percent
        )
    
    async def execute_trade(self, symbol: str, action: TradeAction, quantity: int, price: float) -> bool:
        """Execute a trade order"""
        try:
            if action == TradeAction.BUY:
                return self._execute_buy(symbol, quantity, price)
            elif action == TradeAction.SELL:
                return self._execute_sell(symbol, quantity, price)
            return False
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    def _execute_buy(self, symbol: str, quantity: int, price: float) -> bool:
        """Execute buy order"""
        total_cost = quantity * price
        
        if self.portfolio_data["cash_balance"] < total_cost:
            logger.warning(f"Insufficient funds for buying {quantity} shares of {symbol}")
            return False
        
        # Update cash balance
        self.portfolio_data["cash_balance"] -= total_cost
        
        # Update holdings
        if symbol in self.portfolio_data["holdings"]:
            # Calculate new average price
            existing = self.portfolio_data["holdings"][symbol]
            total_quantity = existing["quantity"] + quantity
            total_cost_basis = (existing["quantity"] * existing["avg_price"]) + (quantity * price)
            new_avg_price = total_cost_basis / total_quantity
            
            self.portfolio_data["holdings"][symbol] = {
                "quantity": total_quantity,
                "avg_price": new_avg_price
            }
        else:
            self.portfolio_data["holdings"][symbol] = {
                "quantity": quantity,
                "avg_price": price
            }
        
        # Record trade
        self.portfolio_data["trade_history"].append({
            "symbol": symbol,
            "action": "buy",
            "quantity": quantity,
            "price": price,
            "timestamp": str(datetime.now())
        })
        
        self._save_portfolio()
        return True
    
    def _execute_sell(self, symbol: str, quantity: int, price: float) -> bool:
        """Execute sell order"""
        if symbol not in self.portfolio_data["holdings"]:
            logger.warning(f"No holdings found for {symbol}")
            return False
        
        holding = self.portfolio_data["holdings"][symbol]
        if holding["quantity"] < quantity:
            logger.warning(f"Insufficient shares to sell {quantity} of {symbol}")
            return False
        
        # Update cash balance
        proceeds = quantity * price
        self.portfolio_data["cash_balance"] += proceeds
        
        # Update holdings
        holding["quantity"] -= quantity
        if holding["quantity"] == 0:
            del self.portfolio_data["holdings"][symbol]
        
        # Record trade
        self.portfolio_data["trade_history"].append({
            "symbol": symbol,
            "action": "sell",
            "quantity": quantity,
            "price": price,
            "timestamp": str(datetime.now())
        })
        
        self._save_portfolio()
        return True
    
    async def get_trade_history(self) -> List[Dict]:
        """Get trading history"""
        return self.portfolio_data.get("trade_history", [])
