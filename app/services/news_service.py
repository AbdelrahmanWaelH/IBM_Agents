import requests
from typing import List
from datetime import datetime, timedelta
from models import NewsItem
from config import settings
import logging

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.base_url = "https://newsapi.org/v2"
        self.api_key = settings.NEWS_API_KEY
    
    async def get_financial_news(self, query: str = "stock market", limit: int = 10) -> List[NewsItem]:
        """Get financial news from NewsAPI"""
        if not self.api_key:
            # Fallback to mock data if no API key
            return self._get_mock_news()
        
        try:
            url = f"{self.base_url}/everything"
            params = {
                'q': query,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': limit,
                'apiKey': self.api_key,
                'from': (datetime.now() - timedelta(days=1)).isoformat()
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get('articles', [])
            
            news_items = []
            for article in articles:
                news_items.append(NewsItem(
                    title=article['title'],
                    description=article['description'] or '',
                    url=article['url'],
                    published_at=datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')),
                    source=article['source']['name']
                ))
            
            return news_items
        
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return self._get_mock_news()
    
    async def get_stock_news(self, symbol: str, limit: int = 5) -> List[NewsItem]:
        """Get news specific to a stock symbol"""
        return await self.get_financial_news(f"{symbol} stock", limit)
    
    def _get_mock_news(self) -> List[NewsItem]:
        """Mock news data for testing"""
        return [
            NewsItem(
                title="Market Shows Strong Performance in Tech Sector",
                description="Technology stocks continue to lead market gains as investors show confidence in AI and cloud computing sectors.",
                url="https://example.com/news/1",
                published_at=datetime.now() - timedelta(hours=2),
                source="Financial Times",
                sentiment="positive"
            ),
            NewsItem(
                title="Federal Reserve Maintains Interest Rates",
                description="The Federal Reserve decided to keep interest rates unchanged, citing stable economic conditions.",
                url="https://example.com/news/2",
                published_at=datetime.now() - timedelta(hours=4),
                source="Reuters",
                sentiment="neutral"
            ),
            NewsItem(
                title="Energy Sector Faces Volatility",
                description="Oil prices fluctuate as geopolitical tensions create uncertainty in energy markets.",
                url="https://example.com/news/3",
                published_at=datetime.now() - timedelta(hours=6),
                source="Bloomberg",
                sentiment="negative"
            )
        ]
