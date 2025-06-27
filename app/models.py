from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class StockInfo(BaseModel):
    symbol: str
    current_price: float
    market_cap: Optional[float] = None
    volume: Optional[int] = None
    change_percent: Optional[float] = None

class NewsItem(BaseModel):
    title: str
    description: str
    url: str
    published_at: datetime
    source: str
    sentiment: Optional[str] = None

class TradeDecision(BaseModel):
    symbol: str
    action: TradeAction
    quantity: int
    confidence: float
    reasoning: str
    suggested_price: float

class Portfolio(BaseModel):
    cash_balance: float
    total_value: float
    holdings: List[dict]
    profit_loss: float
    profit_loss_percent: float

class TradeOrder(BaseModel):
    symbol: str
    action: TradeAction
    quantity: int
    price: Optional[float] = None
