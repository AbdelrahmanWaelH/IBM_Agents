from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize database
from database import create_tables
create_tables()

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
from routers import trading, news, portfolio

app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])

@app.get("/")
async def root():
    return {"message": "AI Trading Agent API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
