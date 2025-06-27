from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum as SQLEnum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
from config import settings

# Database engine
engine = create_engine(settings.DATABASE_URL if hasattr(settings, 'DATABASE_URL') else 
                      "sqlite:///./ai_trading.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class TradeActionEnum(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    cash_balance = Column(Float, default=1000000.0)
    total_value = Column(Float, default=1000000.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Holding(Base):
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, default=1)  # Single portfolio for now
    symbol = Column(String(10), index=True)
    quantity = Column(Integer)
    avg_price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, default=1)
    symbol = Column(String(10), index=True)
    action = Column(SQLEnum(TradeActionEnum))
    quantity = Column(Integer)
    price = Column(Float)
    total_value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
class StockPrice(Base):
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True)
    price = Column(Float)
    market_cap = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    change_percent = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class AIDecision(Base):
    __tablename__ = "ai_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), index=True)
    action = Column(SQLEnum(TradeActionEnum))
    confidence = Column(Float)
    reasoning = Column(Text)
    suggested_price = Column(Float)
    suggested_quantity = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
