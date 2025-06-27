from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import enum
from config import settings
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/ai_trading_agent")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TradeActionEnum(enum.Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class SentimentEnum(enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    cash_balance = Column(Float, default=1000000.0)
    total_value = Column(Float, default=1000000.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Holding(Base):
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, default=1)  # Simple single portfolio for now
    symbol = Column(String, index=True)
    quantity = Column(Integer)
    avg_price = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, default=1)
    symbol = Column(String, index=True)
    action = Column(Enum(TradeActionEnum))
    quantity = Column(Integer)
    price = Column(Float)
    total_value = Column(Float)
    ai_decision_id = Column(Integer, ForeignKey('ai_decisions.id'), nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

class StockPrice(Base):
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    price = Column(Float)
    market_cap = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    change_percent = Column(Float, nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

class AIDecision(Base):
    __tablename__ = "ai_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(Enum(TradeActionEnum))
    quantity = Column(Integer)
    confidence = Column(Float)
    reasoning = Column(Text)
    suggested_price = Column(Float)
    stock_price = Column(Float)
    stock_change_percent = Column(Float, nullable=True)
    portfolio_context = Column(Text, nullable=True)  # JSON string
    was_executed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    trades = relationship("Trade", backref="ai_decision")

class NewsAnalysis(Base):
    __tablename__ = "news_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=True)
    title = Column(String)
    description = Column(Text, nullable=True)
    url = Column(String)
    source = Column(String)
    sentiment = Column(Enum(SentimentEnum), nullable=True)
    ai_decision_id = Column(Integer, ForeignKey('ai_decisions.id'), nullable=True)
    published_at = Column(DateTime(timezone=True))
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())

class StockAnalysis(Base):
    __tablename__ = "stock_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    current_price = Column(Float)
    market_cap = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    change_percent = Column(Float, nullable=True)
    technical_indicators = Column(Text, nullable=True)  # JSON string
    ai_decision_id = Column(Integer, ForeignKey('ai_decisions.id'))
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_portfolio():
    """Initialize the default portfolio if it doesn't exist"""
    db = SessionLocal()
    try:
        existing_portfolio = db.query(Portfolio).filter(Portfolio.id == 1).first()
        if not existing_portfolio:
            portfolio = Portfolio(
                id=1,
                cash_balance=float(settings.INITIAL_BUDGET),
                total_value=float(settings.INITIAL_BUDGET)
            )
            db.add(portfolio)
            db.commit()
            print(f"Initialized portfolio with ${settings.INITIAL_BUDGET:,.2f}")
        else:
            print("Portfolio already exists")
    except Exception as e:
        print(f"Error initializing portfolio: {e}")
        db.rollback()
    finally:
        db.close()
