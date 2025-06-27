from fastapi import APIRouter
from typing import List
from models import NewsItem
from services.news_service import NewsService

router = APIRouter()
news_service = NewsService()

@router.get("/", response_model=List[NewsItem])
async def get_financial_news(limit: int = 10):
    """Get latest financial news"""
    news_items = await news_service.get_financial_news(limit=limit)
    return news_items

@router.get("/stock/{symbol}", response_model=List[NewsItem])
async def get_stock_news(symbol: str, limit: int = 5):
    """Get news for specific stock symbol"""
    news_items = await news_service.get_stock_news(symbol.upper(), limit=limit)
    return news_items

@router.get("/search", response_model=List[NewsItem])
async def search_news(query: str, limit: int = 10):
    """Search news by query"""
    news_items = await news_service.get_financial_news(query=query, limit=limit)
    return news_items
