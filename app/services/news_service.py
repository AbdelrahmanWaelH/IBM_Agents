import requests
import yfinance as yf
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from models import NewsItem
from config import settings
import logging
import asyncio
import time
import json

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.base_url = "https://google.serper.dev"
        self.api_key = settings.SERPER_API_KEY
        self.company_cache = {}
        self.cache_duration = 3600  # 1 hour cache
        
        # Financial keywords for relevance filtering
        self.financial_keywords = {
            'high_priority': [
                'earnings', 'revenue', 'profit', 'loss', 'quarterly', 'annual',
                'stock', 'shares', 'trading', 'market cap', 'dividend',
                'analyst', 'upgrade', 'downgrade', 'price target', 'rating',
                'merger', 'acquisition', 'ipo', 'buyback', 'split'
            ],
            'medium_priority': [
                'financial', 'results', 'guidance', 'forecast', 'outlook',
                'investment', 'investor', 'valuation', 'volatility',
                'ceo', 'cfo', 'executive', 'board', 'management'
            ],
            'sector_terms': [
                'technology', 'healthcare', 'finance', 'energy', 'retail',
                'manufacturing', 'automotive', 'pharmaceutical', 'biotech'
            ]
        }
        
    def _get_company_info(self, symbol: str) -> Optional[Dict[str, str]]:
        """Get company information using yfinance"""
        symbol = symbol.upper().strip()
        current_time = time.time()
        
        # Check cache
        if symbol in self.company_cache:
            cached_data = self.company_cache[symbol]
            if current_time - cached_data['timestamp'] < self.cache_duration:
                return cached_data['info']
        
        try:
            logger.info(f"🔍 Fetching company info for {symbol}")
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if info and isinstance(info, dict):
                company_info = {
                    'longName': info.get('longName', ''),
                    'shortName': info.get('shortName', ''),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', '')
                }
                
                # Cache it
                self.company_cache[symbol] = {
                    'info': company_info,
                    'timestamp': current_time
                }
                
                logger.info(f"✅ Company info for {symbol}: {company_info.get('longName', 'N/A')}")
                return company_info
            else:
                logger.warning(f"⚠️ No company info for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting company info for {symbol}: {e}")
            return None
    
    def _generate_search_queries(self, symbol: str, company_info: Optional[Dict[str, str]] = None) -> List[str]:
        """Generate targeted search queries for SERPER"""
        queries = []
        symbol = symbol.upper().strip()
        
        logger.info(f"🎯 Generating SERPER search queries for {symbol}")
        
        if company_info:
            long_name = company_info.get('longName', '').strip()
            short_name = company_info.get('shortName', '').strip()
            
            # Use company names for better relevance
            if long_name:
                queries.extend([
                    f"{long_name} earnings news",
                    f"{long_name} stock news",
                    f"{long_name} financial results"
                ])
            
            if short_name and short_name != long_name:
                queries.append(f"{short_name} stock news")
        
        # Always include symbol-based queries
        queries.extend([
            f"{symbol} stock earnings",
            f"{symbol} financial news",
            f"{symbol} analyst rating"
        ])
        
        # Remove duplicates while preserving order
        unique_queries = []
        seen = set()
        for q in queries:
            if q and q not in seen:
                unique_queries.append(q)
                seen.add(q)
        
        logger.info(f"📊 Generated {len(unique_queries)} search queries: {unique_queries[:3]}...")
        return unique_queries[:4]  # Limit to 4 queries to avoid rate limits

    async def _search_with_serper(self, query: str) -> List[Dict]:
        """Search for news using SERPER API"""
        try:
            url = f"{self.base_url}/news"
            
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            # SERPER payload for news search
            payload = {
                'q': query,
                'num': 10,  # Number of results
                'tbs': 'qdr:w',  # Last week
                'gl': 'us',  # Country
                'hl': 'en'   # Language
            }
            
            logger.info(f"🌐 SERPER search: '{query}'")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            news_results = data.get('news', [])
            
            logger.info(f"📊 SERPER returned {len(news_results)} articles for: '{query}'")
            
            if news_results:
                # Log sample for debugging
                for i, article in enumerate(news_results[:2], 1):
                    title = article.get('title', 'No title')[:60]
                    source = article.get('source', 'Unknown')
                    logger.info(f"   📄 {i}. {title}... ({source})")
            
            return news_results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ SERPER network error for query '{query}': {e}")
            return []
        except Exception as e:
            logger.error(f"❌ SERPER unexpected error for query '{query}': {e}")
            return []
    
    async def get_financial_news(self, query: str = "stock market", limit: int = 10) -> List[NewsItem]:
        """Get financial news using SERPER API for better relevance and stability"""
        if not self.api_key:
            logger.error("❌ SERPER API key not configured")
            raise ValueError("SERPER API key not configured. Please set SERPER_API_KEY in environment.")
        
        try:
            logger.info(f"🚀 Starting SERPER news search for: '{query}'")
            
            # Get company info if it looks like a stock symbol
            company_info = None
            if query.upper().isalpha() and len(query) <= 5:
                company_info = self._get_company_info(query)
            
            # Generate targeted search queries
            search_queries = self._generate_search_queries(query, company_info)
            
            if not search_queries:
                logger.warning("⚠️ No search queries generated, using fallback")
                search_queries = [f"{query} stock news", "financial news"]
            
            # Search with SERPER
            all_articles = []
            successful_searches = 0
            
            for i, search_query in enumerate(search_queries, 1):
                logger.info(f"🔍 SERPER search {i}/{len(search_queries)}: '{search_query}'")
                
                articles = await self._search_with_serper(search_query)
                
                if articles:
                    all_articles.extend(articles)
                    successful_searches += 1
                    logger.info(f"✅ SERPER strategy {i} successful: {len(articles)} articles")
                else:
                    logger.warning(f"⚠️ SERPER strategy {i} failed: no articles")
                
                # Small delay between requests to be respectful
                if i < len(search_queries):
                    await asyncio.sleep(1)
            
            logger.info(f"📊 SERPER search complete: {successful_searches}/{len(search_queries)} strategies successful")
            
            # Remove duplicates by URL
            seen_urls = set()
            unique_articles = []
            for article in all_articles:
                url = article.get('link', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_articles.append(article)
            
            logger.info(f"🔄 After deduplication: {len(unique_articles)} unique articles")
            
            # Sort by date (SERPER provides relative times, we'll prioritize by position)
            # SERPER already returns results in relevance order
            
            # Convert to NewsItem objects
            news_items = []
            for article in unique_articles[:limit]:
                if article.get('title') and article.get('link'):
                    try:
                        # Handle SERPER date format
                        date_str = article.get('date', '')
                        published_at = datetime.now(timezone.utc)  # Default to now with timezone
                        
                        # Try to parse relative dates like "2 hours ago", "1 day ago"
                        if 'hour' in date_str:
                            hours = int(date_str.split()[0]) if date_str.split()[0].isdigit() else 1
                            published_at = datetime.now(timezone.utc) - timedelta(hours=hours)
                        elif 'day' in date_str:
                            days = int(date_str.split()[0]) if date_str.split()[0].isdigit() else 1
                            published_at = datetime.now(timezone.utc) - timedelta(days=days)
                        elif 'week' in date_str:
                            weeks = int(date_str.split()[0]) if date_str.split()[0].isdigit() else 1
                            published_at = datetime.now(timezone.utc) - timedelta(weeks=weeks)
                        
                        news_item = NewsItem(
                            title=article['title'][:200],
                            description=(article.get('snippet', '') or article.get('description', ''))[:500],
                            url=article['link'],
                            published_at=published_at,
                            source=article.get('source', 'Unknown')
                        )
                        news_items.append(news_item)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing SERPER article: {e}")
                        continue
            
            # Final logging
            if news_items:
                logger.info(f"✅ SERPER SUCCESS: {len(news_items)} relevant financial news for '{query}'")
                if company_info:
                    company_name = company_info.get('longName', query)
                    logger.info(f"📈 Financial news found for {query} ({company_name})")
                
                for i, item in enumerate(news_items[:3], 1):
                    logger.info(f"   💰 {i}. {item.title[:80]}... ({item.source})")
            else:
                logger.warning(f"⚠️ No relevant financial news found for {query}")
            
            return news_items
            
        except Exception as e:
            logger.error(f"❌ Critical error fetching SERPER news for '{query}': {e}")
            return []
    
    async def get_stock_news(self, symbol: str, limit: int = 5) -> List[NewsItem]:
        """Get news specific to a stock symbol using SERPER"""
        return await self.get_financial_news(symbol, limit)
    
    async def get_market_news(self, limit: int = 10) -> List[NewsItem]:
        """Get general market news using SERPER"""
        market_queries = [
            "stock market news today",
            "financial markets outlook", 
            "trading news earnings",
            "market analysis today"
        ]
        
        all_news = []
        for query in market_queries[:2]:  # Limit to avoid rate limits
            try:
                news = await self.get_financial_news(query, limit//2)
                all_news.extend(news)
                if len(all_news) >= limit:
                    break
            except Exception as e:
                logger.error(f"Error fetching market news for '{query}': {e}")
                continue
                
        # Remove duplicates and return
        seen_urls = set()
        unique_news = []
        for news_item in all_news:
            if news_item.url not in seen_urls:
                seen_urls.add(news_item.url)
                unique_news.append(news_item)
                
        return unique_news[:limit]
