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
            logger.error("NewsAPI key not configured")
            raise ValueError("NewsAPI key not configured. Please set NEWS_API_KEY in environment.")
        
        try:
            url = f"{self.base_url}/everything"
            
            # More flexible query for stock symbols
            if query.upper() in ['AMZN', 'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'META']:
                # For major stocks, use company names too
                company_names = {
                    'AMZN': 'Amazon',
                    'AAPL': 'Apple',
                    'GOOGL': 'Google OR Alphabet',
                    'MSFT': 'Microsoft',
                    'TSLA': 'Tesla',
                    'NVDA': 'Nvidia',
                    'META': 'Meta OR Facebook'
                }
                search_query = f"({query} OR {company_names.get(query.upper(), query)}) AND (stock OR earnings OR financial OR market)"
            else:
                search_query = f"{query} AND (stock OR trading OR finance OR market)"
            
            params = {
                'q': search_query,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': limit,
                'apiKey': self.api_key,
                'from': (datetime.now() - timedelta(days=2)).isoformat(),  # Extended to 2 days
                'domains': 'cnbc.com,bloomberg.com,reuters.com,marketwatch.com,yahoo.com,forbes.com,finance.yahoo.com,investing.com'
            }
            
            logger.info(f"Searching news with query: {search_query}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get('articles', [])
            
            logger.info(f"📰 NewsAPI returned {len(articles)} articles for query: {search_query}")
            
            if not articles:
                logger.warning(f"⚠️ No news articles found for query: {search_query}")
                # Try a fallback with a simpler query
                fallback_params = params.copy()
                fallback_params['q'] = query  # Just the symbol/query without additional filters
                logger.info(f"🔄 Trying fallback query: {query}")
                
                fallback_response = requests.get(url, params=fallback_params, timeout=10)
                fallback_response.raise_for_status()
                fallback_data = fallback_response.json()
                articles = fallback_data.get('articles', [])
                
                if articles:
                    logger.info(f"✅ Fallback found {len(articles)} articles")
                else:
                    logger.error(f"❌ No articles found even with fallback for: {query}")
                    return []
                
                logger.info(f"Fallback query returned {len(articles)} articles")
                
                if not articles:
                    return []
            
            news_items = []
            logger.info(f"📝 Processing {len(articles)} articles from NewsAPI...")
            
            for idx, article in enumerate(articles, 1):
                if article.get('title') and article.get('url'):
                    try:
                        published_at = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                        news_item = NewsItem(
                            title=article['title'][:200],  # Limit title length
                            description=(article.get('description') or '')[:500],  # Limit description
                            url=article['url'],
                            published_at=published_at,
                            source=article['source']['name']
                        )
                        news_items.append(news_item)
                        
                        logger.info(f"📄 Article {idx}: '{news_item.title[:50]}...' from {news_item.source}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing article {idx}: {e}")
                        continue
                else:
                    logger.warning(f"⚠️ Skipping article {idx}: missing title or URL")
            
            logger.info(f"✅ Successfully processed {len(news_items)} news articles for: {query}")
            return news_items
        
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            raise ValueError(f"Failed to fetch news from NewsAPI: {e}")
    
    async def get_stock_news(self, symbol: str, limit: int = 5) -> List[NewsItem]:
        """Get news specific to a stock symbol"""
        return await self.get_financial_news(f"{symbol} stock", limit)
