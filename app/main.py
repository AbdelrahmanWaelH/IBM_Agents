from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize database
try:
    from database import create_tables, init_portfolio
    create_tables()
    init_portfolio()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️  Database initialization failed: {e}")
    print("Continuing with file-based storage...")

app = FastAPI(title="AI Trading Agent", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from routers import trading, news, portfolio, analytics, automated_trading, onboarding

app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(automated_trading.router, prefix="/api/automated-trading", tags=["automated-trading"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["onboarding"])

@app.get("/")
async def root():
    return {"message": "AI Trading Agent API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
