"""
Company Search Service for Dynamic Symbol Lookup
Allows users to search for companies by name and get their stock symbols
"""

import asyncio
import logging
import yfinance as yf
import requests
import time
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from database import SessionLocal
from sqlalchemy import Column, Integer, String, DateTime, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import json
import re

logger = logging.getLogger(__name__)

# Create a simple cache table for company data
Base = declarative_base()

class CompanyCache(Base):
    __tablename__ = "company_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    company_name = Column(String, index=True)
    short_name = Column(String, index=True)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    market_cap = Column(String, nullable=True)
    description = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    country = Column(String, nullable=True)
    website = Column(String, nullable=True)
    cached_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CompanySearchService:
    def __init__(self):
        self.db = SessionLocal()
        self.cache_duration = 86400  # 24 hours cache
        self._ensure_cache_table()
        
        # Popular symbols for quick searching
        self.popular_symbols = {
            # Tech Giants
            'AAPL': 'Apple Inc.',
            'MSFT': 'Microsoft Corporation',
            'GOOGL': 'Alphabet Inc.',
            'AMZN': 'Amazon.com Inc.',
            'META': 'Meta Platforms Inc.',
            'NVDA': 'NVIDIA Corporation',
            'TSLA': 'Tesla Inc.',
            'NFLX': 'Netflix Inc.',
            'AMD': 'Advanced Micro Devices Inc.',
            'ORCL': 'Oracle Corporation',
            'ADBE': 'Adobe Inc.',
            'CRM': 'Salesforce Inc.',
            'INTC': 'Intel Corporation',
            'IBM': 'International Business Machines Corporation',
            
            # Financial
            'JPM': 'JPMorgan Chase & Co.',
            'BAC': 'Bank of America Corporation',
            'WFC': 'Wells Fargo & Company',
            'GS': 'The Goldman Sachs Group Inc.',
            'MS': 'Morgan Stanley',
            'C': 'Citigroup Inc.',
            'V': 'Visa Inc.',
            'MA': 'Mastercard Incorporated',
            'AXP': 'American Express Company',
            'BRK.B': 'Berkshire Hathaway Inc.',
            
            # Healthcare
            'UNH': 'UnitedHealth Group Incorporated',
            'JNJ': 'Johnson & Johnson',
            'PFE': 'Pfizer Inc.',
            'ABBV': 'AbbVie Inc.',
            'TMO': 'Thermo Fisher Scientific Inc.',
            'ABT': 'Abbott Laboratories',
            'MRK': 'Merck & Co. Inc.',
            'LLY': 'Eli Lilly and Company',
            'BMY': 'Bristol-Myers Squibb Company',
            'GILD': 'Gilead Sciences Inc.',
            
            # Consumer
            'WMT': 'Walmart Inc.',
            'HD': 'The Home Depot Inc.',
            'PG': 'The Procter & Gamble Company',
            'KO': 'The Coca-Cola Company',
            'PEP': 'PepsiCo Inc.',
            'NKE': 'NIKE Inc.',
            'MCD': "McDonald's Corporation",
            'COST': 'Costco Wholesale Corporation',
            'DIS': 'The Walt Disney Company',
            'SBUX': 'Starbucks Corporation',
            
            # Energy
            'XOM': 'Exxon Mobil Corporation',
            'CVX': 'Chevron Corporation',
            'COP': 'ConocoPhillips',
            'SLB': 'Schlumberger Limited',
            'EOG': 'EOG Resources Inc.',
            'PXD': 'Pioneer Natural Resources Company',
            'MPC': 'Marathon Petroleum Corporation',
            'VLO': 'Valero Energy Corporation',
            
            # Industrial
            'BA': 'The Boeing Company',
            'CAT': 'Caterpillar Inc.',
            'GE': 'General Electric Company',
            'MMM': '3M Company',
            'HON': 'Honeywell International Inc.',
            'UPS': 'United Parcel Service Inc.',
            'FDX': 'FedEx Corporation',
            'RTX': 'Raytheon Technologies Corporation'
        }
    
    def _ensure_cache_table(self):
        """Ensure the company cache table exists"""
        try:
            from database import engine
            CompanyCache.metadata.create_all(bind=engine)
            logger.info("Company cache table ready")
        except Exception as e:
            logger.warning(f"Could not create company cache table: {e}")
    
    async def search_companies(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Search for companies by name or symbol using Yahoo Finance
        Returns list of matches with symbol, name, and other details
        """
        query = query.strip()
        results = []
        
        try:
            # Use Yahoo Finance search API for both names and symbols
            results = await self._search_by_company_name(query, limit)
            
            # Cache results
            for result in results:
                await self._cache_company_info(result)
                
        except Exception as e:
            logger.error(f"Error in company search: {e}")
        
        return results[:limit]
    
    def get_popular_companies(self) -> List[Dict[str, str]]:
        """Get list of popular companies for quick selection"""
        popular = []
        for symbol, name in list(self.popular_symbols.items())[:20]:  # Return top 20
            popular.append({
                'symbol': symbol,
                'company_name': name,
                'short_name': name.split(' Inc.')[0].split(' Corporation')[0],
                'source': 'popular',
                'sector': self._guess_sector(symbol)
            })
        return popular
    
    async def _live_company_search(self, query: str, limit: int) -> List[Dict[str, str]]:
        """Perform live search using Yahoo Finance only"""
        return await self._search_by_company_name(query, limit)
    
    async def _search_by_company_name(self, company_name: str, limit: int) -> List[Dict[str, str]]:
        """Search for company by name using Yahoo Finance search API only"""
        matches = []
        
        try:
            import requests
            from urllib.parse import quote
            
            # Use Yahoo Finance search API
            search_url = f"https://query1.finance.yahoo.com/v1/finance/search"
            params = {
                'q': company_name,
                'quotesCount': limit,
                'newsCount': 0,
                'enableFuzzyQuery': True,
                'quotesQueryId': 'tss_match_phrase_query',
                'multiQuoteQueryId': 'multi_quote_single_token_query'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Make the request with timeout
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                quotes = data.get('quotes', [])
                
                for quote in quotes[:limit]:
                    symbol = quote.get('symbol', '')
                    if symbol and quote.get('isYahooFinance', False):
                        company_info = {
                            'symbol': symbol,
                            'company_name': quote.get('longname', quote.get('shortname', '')),
                            'short_name': quote.get('shortname', ''),
                            'sector': quote.get('sector', ''),
                            'industry': quote.get('industry', ''),
                            'exchange': quote.get('exchange', ''),
                            'source': 'yahoo_search',
                            'quote_type': quote.get('quoteType', ''),
                            'market_cap': '',
                        }
                        
                        # Only include equity securities
                        if quote.get('quoteType') in ['EQUITY', 'ETF']:
                            matches.append(company_info)
            
        except Exception as e:
            logger.error(f"Error searching by company name via Yahoo Finance: {e}")
        
        return matches
    
    async def _get_company_info_live(self, symbol: str) -> Optional[Dict[str, str]]:
        """Get company information for a symbol using yfinance"""
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            if info and info.get('longName'):
                company_info = {
                    'symbol': symbol.upper(),
                    'company_name': info.get('longName', ''),
                    'short_name': info.get('shortName', info.get('longName', '')),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', ''),
                    'market_cap': self._format_market_cap(info.get('marketCap')),
                    'exchange': info.get('exchange', ''),
                    'currency': info.get('currency', ''),
                    'country': info.get('country', ''),
                    'website': info.get('website', ''),
                    'description': info.get('longBusinessSummary', '')[:500] if info.get('longBusinessSummary') else '',
                    'source': 'live'
                }
                
                return company_info
            
        except Exception as e:
            logger.debug(f"Could not get info for {symbol}: {e}")
        
        return None
    
    async def _cache_company_info(self, company_info: Dict[str, str]):
        """Cache company information in database"""
        try:
            existing = self.db.query(CompanyCache).filter(
                CompanyCache.symbol == company_info['symbol']
            ).first()
            
            if existing:
                # Update existing record
                for key, value in company_info.items():
                    if key != 'source' and hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = func.now()
            else:
                # Create new record
                cache_record = CompanyCache(**{
                    k: v for k, v in company_info.items() 
                    if k != 'source' and hasattr(CompanyCache, k)
                })
                self.db.add(cache_record)
            
            self.db.commit()
            logger.debug(f"Cached company info for {company_info['symbol']}")
            
        except Exception as e:
            logger.error(f"Error caching company info: {e}")
            self.db.rollback()
    
    def _format_market_cap(self, market_cap) -> str:
        """Format market cap into readable string"""
        if not market_cap or market_cap == 0:
            return "N/A"
        
        try:
            mc = float(market_cap)
            if mc >= 1e12:
                return f"${mc/1e12:.1f}T"
            elif mc >= 1e9:
                return f"${mc/1e9:.1f}B"
            elif mc >= 1e6:
                return f"${mc/1e6:.1f}M"
            else:
                return f"${mc:,.0f}"
        except:
            return "N/A"
    
    def _guess_sector(self, symbol: str) -> str:
        """Guess sector based on symbol for popular stocks"""
        tech_symbols = {'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX', 'AMD', 'ORCL', 'ADBE', 'CRM', 'INTC', 'IBM'}
        financial_symbols = {'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA', 'AXP', 'BRK.B'}
        healthcare_symbols = {'UNH', 'JNJ', 'PFE', 'ABBV', 'TMO', 'ABT', 'MRK', 'LLY', 'BMY', 'GILD'}
        consumer_symbols = {'WMT', 'HD', 'PG', 'KO', 'PEP', 'NKE', 'MCD', 'COST', 'DIS', 'SBUX'}
        energy_symbols = {'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC', 'VLO'}
        industrial_symbols = {'BA', 'CAT', 'GE', 'MMM', 'HON', 'UPS', 'FDX', 'RTX'}
        
        if symbol in tech_symbols:
            return "Technology"
        elif symbol in financial_symbols:
            return "Financial Services"
        elif symbol in healthcare_symbols:
            return "Healthcare"
        elif symbol in consumer_symbols:
            return "Consumer Cyclical"
        elif symbol in energy_symbols:
            return "Energy"
        elif symbol in industrial_symbols:
            return "Industrials"
        else:
            return "Other"
    
    async def get_company_details(self, symbol: str) -> Optional[Dict[str, str]]:
        """Get detailed company information for a specific symbol"""
        symbol = symbol.upper().strip()
        
        # Check cache first
        cached = self.db.query(CompanyCache).filter(
            CompanyCache.symbol == symbol
        ).first()
        
        if cached:
            # Check if cache is still valid
            cache_age = (func.now() - cached.updated_at).total_seconds()
            if cache_age < self.cache_duration:
                return {
                    'symbol': cached.symbol,
                    'company_name': cached.company_name,
                    'short_name': cached.short_name,
                    'sector': cached.sector,
                    'industry': cached.industry,
                    'market_cap': cached.market_cap,
                    'exchange': cached.exchange,
                    'currency': cached.currency,
                    'country': cached.country,
                    'website': cached.website,
                    'description': cached.description,
                    'source': 'cache'
                }
        
        # Get live data
        company_info = await self._get_company_info_live(symbol)
        if company_info:
            await self._cache_company_info(company_info)
            return company_info
        
        return None
    
    def get_popular_companies(self) -> List[Dict[str, str]]:
        """Get list of popular companies for quick selection"""
        popular_list = []
        
        for symbol, name in list(self.popular_symbols.items())[:20]:  # Get top 20
            popular_list.append({
                'symbol': symbol,
                'company_name': name,
                'short_name': name.split(' Inc.')[0].split(' Corporation')[0],
                'sector': self._guess_sector(symbol),
                'source': 'popular'
            })
        
        return popular_list
    
    async def refresh_cache(self):
        """Refresh the company cache with latest data"""
        try:
            logger.info("Starting company cache refresh")
            
            # Get popular symbols and refresh their data
            symbols_to_refresh = list(self.popular_symbols.keys())[:50]  # Refresh top 50
            
            refreshed_count = 0
            for symbol in symbols_to_refresh:
                try:
                    company_info = await self._get_company_info_live(symbol)
                    if company_info:
                        await self._cache_company_info(company_info)
                        refreshed_count += 1
                        await asyncio.sleep(0.5)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Failed to refresh {symbol}: {e}")
            
            logger.info(f"Company cache refresh completed: {refreshed_count}/{len(symbols_to_refresh)} symbols updated")
            
        except Exception as e:
            logger.error(f"Error refreshing company cache: {e}")
            raise
    
    def search_symbols_by_name(self, company_name: str, limit: int = 5) -> List[str]:
        """Quick search for symbols by company name (synchronous)"""
        company_name = company_name.upper()
        matches = []
        
        for symbol, name in self.popular_symbols.items():
            if company_name in name.upper():
                matches.append(symbol)
                if len(matches) >= limit:
                    break
        
        return matches
    
    async def get_symbol_from_name(self, company_name: str) -> Optional[str]:
        """Get stock symbol from company name using Yahoo Finance search"""
        try:
            import requests
            from urllib.parse import quote
            
            # Use Yahoo Finance search API
            search_url = f"https://query1.finance.yahoo.com/v1/finance/search"
            params = {
                'q': company_name,
                'quotesCount': 10,
                'newsCount': 0,
                'enableFuzzyQuery': True,
                'quotesQueryId': 'tss_match_phrase_query',
                'multiQuoteQueryId': 'multi_quote_single_token_query'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                quotes = data.get('quotes', [])
                
                # Look for exact or close matches
                for quote in quotes:
                    if quote.get('isYahooFinance', False) and quote.get('quoteType') in ['EQUITY', 'ETF']:
                        symbol = quote.get('symbol', '')
                        long_name = quote.get('longname', '').lower()
                        short_name = quote.get('shortname', '').lower()
                        
                        # Check for exact or very close match
                        company_lower = company_name.lower()
                        if (company_lower in long_name or 
                            company_lower in short_name or
                            long_name.startswith(company_lower) or
                            short_name.startswith(company_lower)):
                            
                            # Verify the symbol actually works
                            if await self._verify_symbol(symbol):
                                return symbol
                
                # If no exact match, return the first valid result
                for quote in quotes:
                    if quote.get('isYahooFinance', False) and quote.get('quoteType') in ['EQUITY', 'ETF']:
                        symbol = quote.get('symbol', '')
                        if await self._verify_symbol(symbol):
                            return symbol
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting symbol from name '{company_name}': {e}")
            return None
    
    async def verify_symbol(self, symbol: str) -> bool:
        """Verify that a symbol is valid by checking if we can get its info"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return bool(info and info.get('symbol') and info.get('regularMarketPrice') is not None)
        except Exception:
            return False

    async def _verify_symbol(self, symbol: str) -> bool:
        """Verify that a symbol is valid by checking if we can get its info"""
        return await self.verify_symbol(symbol)
    
    def __del__(self):
        """Close database connection"""
        if hasattr(self, 'db'):
            self.db.close()

# Global instance
company_search_service = CompanySearchService()
