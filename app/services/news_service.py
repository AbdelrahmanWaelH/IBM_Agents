import requests
import yfinance as yf
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from models import NewsItem
from config import settings
import logging
import asyncio
import time

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.api_key = settings.SERPER_API_KEY
        
    async def get_stock_news(self, symbol: str, limit: int = 5) -> List[NewsItem]:
        """Get news for a stock symbol - simple and reliable"""
        try:
            # Try yfinance first (most reliable for stock news)
            ticker = yf.Ticker(symbol.upper())
            news = ticker.news
            
            news_items = []
            for article in news[:limit]:
                try:
                    published_at = datetime.fromtimestamp(
                        article.get('providerPublishTime', time.time()), 
                        tz=timezone.utc
                    )
                    
                    news_item = NewsItem(
                        title=article.get('title', 'No Title')[:200],
                        description=(article.get('summary') or '')[:500],
                        url=article.get('link', ''),
                        published_at=published_at,
                        source=article.get('publisher', 'Yahoo Finance')
                    )
                    news_items.append(news_item)
                    
                except Exception:
                    continue
            
            if not news_items:
                # Silent handling - don't log warnings for missing news as it's normal
                logger.debug(f"No news articles found for {symbol}")
            else:
                logger.info(f"✅ Found {len(news_items)} articles for {symbol}")
            
            return news_items
            
        except Exception as e:
            logger.debug(f"News fetch failed for {symbol}: {e}")  # Debug level to reduce noise
            return []
    
    async def get_financial_news(self, query: str = "stock market", limit: int = 10) -> List[NewsItem]:
        """Get general financial news"""
        return await self.get_stock_news(query, limit)
    
    async def get_market_news(self, limit: int = 10) -> List[NewsItem]:
        """Get general market news"""
        try:
            # Use a reliable financial news source
            return await self.get_stock_news("SPY", limit)  # S&P 500 ETF news
        except Exception:
            return []