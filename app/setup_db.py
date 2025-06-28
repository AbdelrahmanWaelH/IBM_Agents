#!/usr/bin/env python3

"""
Database setup script for AI Trading Agent
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import create_tables, SessionLocal, Portfolio
from config import settings

def setup_database():
    """Initialize database and create default data"""
    print("🗄️  Setting up database...")
    
    # Create all tables
    create_tables()
    print("✅ Database tables created")
    
    # Create default portfolio if it doesn't exist
    db = SessionLocal()
    try:
        portfolio = db.query(Portfolio).filter(Portfolio.id == 1).first()
        if not portfolio:
            portfolio = Portfolio(
                id=1,
                cash_balance=settings.INITIAL_BUDGET,
                total_value=settings.INITIAL_BUDGET
            )
            db.add(portfolio)
            db.commit()
            print(f"✅ Default portfolio created with ${settings.INITIAL_BUDGET:,.2f}")
        else:
            print(f"✅ Portfolio already exists with ${portfolio.cash_balance:,.2f}")
    finally:
        db.close()
    
    print("🚀 Database setup complete!")

if __name__ == "__main__":
    setup_database()
