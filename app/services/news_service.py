import requests
import yfinance as yf
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from models import NewsItem
from config import settings
import logging
import asyncio
import time
import re

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.base_url = "https://newsapi.org/v2"
        self.api_key = settings.NEWS_API_KEY
        self.company_cache = {}
        self.cache_duration = 3600  # 1 hour cache
        
    def _clean_company_name(self, company_name: str) -> str:
        """Clean company name for better search results - NewsAPI is very picky"""
        if not company_name:
            return ""
        
        # Remove common suffixes that confuse NewsAPI
        suffixes_to_remove = [
            r'\s+Inc\.?$', r'\s+Corporation$', r'\s+Corp\.?$', r'\s+Company$', r'\s+Co\.?$',
            r'\s+Ltd\.?$', r'\s+Limited$', r'\s+LLC$', r'\s+LP$', r'\s+LLP$',
            r'\s+Group$', r'\s+Holdings?$', r'\s+International$', r'\s+Technologies$',
            r'\s+Systems$', r'\s+Solutions$', r'\s+& Co\.?$', r'\s+& Company$'
        ]
        
        cleaned = company_name
        for suffix in suffixes_to_remove:
            cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE)
        
        # Remove special characters that break NewsAPI queries
        cleaned = re.sub(r'[&.,()"]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        logger.info(f"🧹 Cleaned: '{company_name}' -> '{cleaned}'")
        return cleaned
        
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
    
    def _generate_search_strategies(self, symbol: str, company_info: Optional[Dict[str, str]] = None) -> List[str]:
        """Generate search queries - simplified approach that actually works with NewsAPI"""
        queries = []
        symbol = symbol.upper().strip()
        
        logger.info(f"🎯 Generating search strategies for {symbol}")
        
        if company_info:
            long_name = company_info.get('longName', '').strip()
            short_name = company_info.get('shortName', '').strip()
            
            # Clean names for NewsAPI
            clean_long = self._clean_company_name(long_name)
            clean_short = self._clean_company_name(short_name)
            
            # Strategy 1: Simple company name (most reliable with NewsAPI)
            if clean_long and len(clean_long) > 3:
                queries.append(clean_long)
                logger.info(f"📝 Strategy 1: Company name only -> '{clean_long}'")
            
            # Strategy 2: Company name + stock 
            if clean_long and len(clean_long) > 3:
                queries.append(f"{clean_long} stock")
                logger.info(f"📝 Strategy 2: Company + stock -> '{clean_long} stock'")
            
            # Strategy 3: Short name if different
            if clean_short and clean_short != clean_long and len(clean_short) > 2:
                queries.append(clean_short)
                logger.info(f"📝 Strategy 3: Short name -> '{clean_short}'")
        
        # Strategy 4: Symbol alone (fallback)
        queries.append(symbol)
        logger.info(f"📝 Strategy 4: Symbol only -> '{symbol}'")
        
        # Strategy 5: Symbol + stock
        queries.append(f"{symbol} stock")
        logger.info(f"📝 Strategy 5: Symbol + stock -> '{symbol} stock'")
        
        # Remove duplicates
        unique_queries = []
        seen = set()
        for q in queries:
            if q and q not in seen:
                unique_queries.append(q)
                seen.add(q)
        
        logger.info(f"📊 Final strategies ({len(unique_queries)}): {unique_queries}")
        return unique_queries[:4]  # Limit to 4 to avoid rate limits
    
    async def _try_single_search(self, query: str, attempt: int = 1) -> List[Dict]:
        """Try a single search with NewsAPI - with detailed logging"""
        try:
            url = f"{self.base_url}/everything"
            
            # Simple params - NewsAPI is very sensitive
            params = {
                'q': query,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 50,
                'apiKey': self.api_key,
                'from': (datetime.now() - timedelta(days=5)).isoformat(),
            }
            
            logger.info(f"🌐 ATTEMPT {attempt}: Searching NewsAPI")
            logger.info(f"   Query: '{query}'")
            logger.info(f"   URL: {url}")
            logger.info(f"   Params: {params}")
            
            response = requests.get(url, params=params, timeout=25)
            
            logger.info(f"📡 Response status: {response.status_code}")
            logger.info(f"📡 Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"📊 API Response:")
            logger.info(f"   Status: {data.get('status', 'unknown')}")
            logger.info(f"   Total Results: {data.get('totalResults', 0)}")
            logger.info(f"   Articles returned: {len(data.get('articles', []))}")
            
            articles = data.get('articles', [])
            
            if not articles:
                logger.warning(f"⚠️ No articles for query: '{query}'")
                logger.warning(f"⚠️ Full API response: {data}")
            else:
                logger.info(f"✅ Found {len(articles)} articles for: '{query}'")
                # Log first few article titles for debugging
                for i, article in enumerate(articles[:3], 1):
                    title = article.get('title', 'No title')[:60]
                    source = article.get('source', {}).get('name', 'Unknown')
                    logger.info(f"   📄 {i}. {title}... ({source})")
            
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error for '{query}': {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"   Response status: {e.response.status_code}")
                logger.error(f"   Response text: {e.response.text[:200]}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error for '{query}': {e}")
            return []
    
    async def get_financial_news(self, query: str = "stock market", limit: int = 10) -> List[NewsItem]:
        """Get financial news with robust fallback strategies"""
        if not self.api_key:
            logger.error("❌ NewsAPI key not configured")
            raise ValueError("NewsAPI key not configured. Please set NEWS_API_KEY in environment.")
        
        try:
            logger.info(f"🚀 Starting news search for: '{query}'")
            
            # Get company info if it looks like a stock symbol
            company_info = None
            if query.upper().isalpha() and len(query) <= 5:
                company_info = self._get_company_info(query)
            
            # Generate search strategies
            search_queries = self._generate_search_strategies(query, company_info)
            
            if not search_queries:
                logger.warning("⚠️ No search strategies generated, using fallback")
                search_queries = [query, f"{query} stock"]
            
            # Try each search strategy
            all_articles = []
            successful_searches = 0
            
            for i, search_query in enumerate(search_queries, 1):
                logger.info(f"🔍 Trying search strategy {i}/{len(search_queries)}: '{search_query}'")
                
                articles = await self._try_single_search(search_query, i)
                
                if articles:
                    all_articles.extend(articles)
                    successful_searches += 1
                    logger.info(f"✅ Strategy {i} successful: {len(articles)} articles")
                else:
                    logger.warning(f"⚠️ Strategy {i} failed: no articles")
                
                # Small delay between requests
                if i < len(search_queries):
                    await asyncio.sleep(1)
            
            logger.info(f"📊 Search complete: {successful_searches}/{len(search_queries)} strategies successful")
            
            # Remove duplicates
            seen_urls = set()
            unique_articles = []
            for article in all_articles:
                url = article.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_articles.append(article)
            
            # Sort by date
            unique_articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
            
            logger.info(f"� After deduplication: {len(unique_articles)} unique articles")
            
            # Convert to NewsItem objects
            news_items = []
            for article in unique_articles[:limit]:
                if article.get('title') and article.get('url'):
                    try:
                        published_at = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                        news_item = NewsItem(
                            title=article['title'][:200],
                            description=(article.get('description') or '')[:500],
                            url=article['url'],
                            published_at=published_at,
                            source=article['source']['name']
                        )
                        news_items.append(news_item)
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing article: {e}")
                        continue
            
            # Final logging
            if news_items:
                logger.info(f"✅ SUCCESS: {len(news_items)} news articles processed for '{query}'")
                if company_info:
                    company_name = company_info.get('longName', query)
                    logger.info(f"📈 News found for {query} ({company_name})")
                
                for i, item in enumerate(news_items[:3], 1):
                    logger.info(f"   📄 {i}. {item.title[:80]}... ({item.source})")
            else:
                logger.warning(f"⚠️ No news articles available for {query} - analysis will be based on stock data only")
            
            return news_items
            
        except Exception as e:
            logger.error(f"❌ Critical error fetching news for '{query}': {e}")
            return []  # Return empty list instead of raising exception
    
    async def get_stock_news(self, symbol: str, limit: int = 5) -> List[NewsItem]:
        """Get news specific to a stock symbol"""
        return await self.get_financial_news(symbol, limit)
    
    async def _filter_relevant_news_with_ai(self, articles: List[Dict], symbol: str, company_info: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Use AI to filter news articles for relevance to the specific company/stock"""
        if not articles:
            return []
        
        try:
            # Import here to avoid circular imports
            from services.ai_service import AITradingService
            ai_service = AITradingService()
            
            if not ai_service.llm:
                logger.warning("AI not available for news filtering, returning all articles")
                return articles
            
            company_name = "Unknown Company"
            company_description = ""
            
            if company_info:
                company_name = company_info.get('longName', company_info.get('shortName', symbol))
                company_description = company_info.get('longBusinessSummary', '')[:200]
            
            # Process articles in batches to avoid overwhelming the AI
            relevant_articles = []
            
            for i, article in enumerate(articles[:10]):  # Limit to first 10 articles
                title = article.get('title', '')
                description = article.get('description', '')
                
                if not title:
                    continue
                
                # Create relevance check prompt
                relevance_prompt = f"""
Analyze if this news article is directly relevant to the company {company_name} (symbol: {symbol}).

Company: {company_name}
Symbol: {symbol}
Company Description: {company_description}

News Article:
Title: {title}
Description: {description}

Is this article specifically about {company_name} or directly related to their business, stock performance, earnings, products, or industry developments that would significantly impact their stock price?

Consider relevant:
- Earnings reports, financial results
- Product launches, business developments
- Leadership changes, strategic decisions
- Industry developments affecting the company
- Stock price movements, analyst ratings
- Mergers, acquisitions, partnerships
- Regulatory impacts on the company

Consider NOT relevant:
- General market news not specific to the company
- News about completely different companies
- Generic industry news with no specific company mention
- Unrelated topics (sports, entertainment, politics) unless directly impacting the company

Respond with ONLY: relevant or not_relevant
"""
                
                try:
                    response = ai_service.llm.invoke(relevance_prompt)
                    relevance = response.strip().lower()
                    
                    if 'relevant' in relevance and 'not_relevant' not in relevance:
                        relevant_articles.append(article)
                        logger.info(f"✅ AI marked as relevant: '{title[:60]}...'")
                    else:
                        logger.info(f"❌ AI marked as not relevant: '{title[:60]}...'")
                        
                except Exception as e:
                    logger.warning(f"Error in AI relevance check for article {i+1}: {e}")
                    # If AI fails, include the article (conservative approach)
                    relevant_articles.append(article)
            
            logger.info(f"🤖 AI filtered news: {len(relevant_articles)}/{len(articles)} articles deemed relevant for {symbol}")
            return relevant_articles
            
        except Exception as e:
            logger.error(f"Error in AI news filtering: {e}")
            return articles  # Return all articles if filtering fails
    
    def _enhanced_search_strategies(self, symbol: str, company_info: Optional[Dict[str, str]] = None) -> List[str]:
        """Enhanced search strategies with better company-focused queries"""
        queries = []
        symbol = symbol.upper().strip()
        
        logger.info(f"🎯 Enhanced search strategies for {symbol}")
        
        if company_info:
            long_name = company_info.get('longName', '').strip()
            short_name = company_info.get('shortName', '').strip()
            sector = company_info.get('sector', '').strip()
            
            # Clean names for NewsAPI
            clean_long = self._clean_company_name(long_name)
            clean_short = self._clean_company_name(short_name)
            
            # Strategy 1: Company name + financial terms (highest priority)
            if clean_long and len(clean_long) > 3:
                # More specific financial queries
                queries.extend([
                    f"{clean_long} earnings",
                    f"{clean_long} revenue", 
                    f"{clean_long} stock price",
                    f"{clean_long} quarterly results"
                ])
                logger.info(f"📝 Added earnings/financial queries for: {clean_long}")
            
            # Strategy 2: Company name with stock-specific terms
            if clean_long:
                queries.extend([
                    f"{clean_long} shares",
                    f"{clean_long} market",
                    f"{clean_long} trading"
                ])
                
            # Strategy 3: Sector-specific news (if available)
            if sector and clean_long:
                sector_clean = self._clean_company_name(sector)
                if sector_clean:
                    queries.append(f"{clean_long} {sector_clean}")
                    logger.info(f"📝 Added sector query: {clean_long} {sector_clean}")
            
            # Strategy 4: Short name variations
            if clean_short and clean_short != clean_long and len(clean_short) > 2:
                queries.extend([
                    f"{clean_short} earnings",
                    f"{clean_short} stock"
                ])
        
        # Strategy 5: Symbol-based fallbacks (lower priority)
        queries.extend([
            f"{symbol} earnings report",
            f"{symbol} quarterly",
            f"{symbol} stock news",
            symbol  # Last resort: just the symbol
        ])
        
        # Remove duplicates while preserving order
        unique_queries = []
        seen = set()
        for q in queries:
            if q and q not in seen and len(q.strip()) > 2:
                unique_queries.append(q)
                seen.add(q)
        
        logger.info(f"📊 Enhanced strategies ({len(unique_queries)}): {unique_queries[:6]}")
        return unique_queries[:6]  # Limit to 6 queries
