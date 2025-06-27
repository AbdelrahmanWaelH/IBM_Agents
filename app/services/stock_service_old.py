import yfinance as yf
from typing import List, Dict, Optional
from models import StockInfo
import logging
import time
import asyncio
import os
import requests

logger = logging.getLogger(__name__)

class StockService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes cache
        self.last_request_time = {}  # Track per-symbol request times
        self.min_request_interval = 2  # 2 seconds between requests per symbol
        self.global_last_request = 0
        self.global_min_interval = 0.5  # 500ms between any requests
        # Persistent session for yfinance
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AI-Trader/1.0; +https://ibm.com)'
        })
        # Optionally set Yahoo cookie/crumb if provided
        yf_cookie = os.getenv('YF_COOKIE')
        yf_crumb = os.getenv('YF_CRUMB')
        if yf_cookie:
            self.session.cookies.set('B', yf_cookie)
        if yf_crumb:
            self.session.cookies.set('crumb', yf_crumb)

    def _rate_limit_global(self):
        """Global rate limiting across all requests"""
        current_time = time.time()
        time_since_last = current_time - self.global_last_request
        if time_since_last < self.global_min_interval:
            sleep_time = self.global_min_interval - time_since_last
            time.sleep(sleep_time)
        self.global_last_request = time.time()
    
    def _rate_limit_symbol(self, symbol: str):
        """Per-symbol rate limiting"""
        current_time = time.time()
        if symbol in self.last_request_time:
            time_since_last = current_time - self.last_request_time[symbol]
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                time.sleep(sleep_time)
        self.last_request_time[symbol] = time.time()
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached data is still valid"""
        if symbol not in self.cache:
            return False
        return time.time() - self.cache[symbol]['timestamp'] < self.cache_duration
    
    async def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """Get current stock information with aggressive caching and rate limiting"""
        # Check cache first
        if self._is_cache_valid(symbol):
            logger.info(f"Returning cached data for {symbol}")
            return self.cache[symbol]['data']
        
        # Apply rate limiting
        self._rate_limit_global()
        self._rate_limit_symbol(symbol)
        
        max_retries = 4
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching fresh data for {symbol} (attempt {attempt+1})")
                ticker = yf.Ticker(symbol, session=self.session)
                hist = ticker.history(period="2d", interval="1d")
                if hist.empty:
                    logger.warning(f"No historical data available for {symbol}")
                    return self._get_mock_stock_data(symbol)
                current_price = float(hist['Close'].iloc[-1])
                volume = int(hist['Volume'].iloc[-1]) if not hist['Volume'].empty else None
                if len(hist) >= 2:
                    previous_close = float(hist['Close'].iloc[-2])
                    change_percent = ((current_price - previous_close) / previous_close) * 100
                else:
                    change_percent = 0.0
                market_cap = None
                try:
                    info = ticker.info
                    if info and isinstance(info, dict):
                        market_cap = info.get('marketCap')
                except Exception as e:
                    logger.warning(f"Could not fetch detailed info for {symbol}: {e}")
                stock_info = StockInfo(
                    symbol=symbol,
                    current_price=current_price,
                    market_cap=market_cap,
                    volume=volume,
                    change_percent=change_percent
                )
                self.cache[symbol] = {
                    'data': stock_info,
                    'timestamp': time.time()
                }
                logger.info(f"Successfully fetched data for {symbol}: ${current_price:.2f}")
                return stock_info
            except Exception as e:
                logger.error(f"Error fetching stock info for {symbol} (attempt {attempt+1}): {e}")
                # If 429 or rate limit, exponential backoff
                if '429' in str(e) or 'Too Many Requests' in str(e):
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited by Yahoo. Backing off for {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    break
        # If all attempts fail, return mock data
        return self._get_mock_stock_data(symbol)
    
    def _get_mock_stock_data(self, symbol: str) -> StockInfo:
        """Return mock stock data for demo purposes"""
        mock_prices = {
            'AAPL': 150.25,
            'GOOGL': 2800.50,
            'MSFT': 350.75,
            'TSLA': 800.25,
            'NVDA': 450.60,
            'AMZN': 3200.25
        }
        
        base_price = mock_prices.get(symbol, 100.0)
        # Add some random variation
        import random
        price_variation = random.uniform(-0.05, 0.05)  # ±5%
        current_price = base_price * (1 + price_variation)
        
        return StockInfo(
            symbol=symbol,
            current_price=current_price,
            market_cap=1000000000,  # 1B mock market cap
            volume=1000000,  # 1M mock volume
            change_percent=price_variation * 100
        )
    
    async def get_multiple_stocks(self, symbols: List[str]) -> List[StockInfo]:
        """Get information for multiple stocks with staggered requests"""
        stocks = []
        for i, symbol in enumerate(symbols):
            if i > 0:
                # Add extra delay between multiple requests
                await asyncio.sleep(1)
            
            stock_info = await self.get_stock_info(symbol)
            if stock_info:
                stocks.append(stock_info)
        return stocks
    
    def _calculate_change_percent(self, hist) -> Optional[float]:
        """Calculate percentage change from previous close"""
        if len(hist) < 2:
            return None
        
        current = hist['Close'].iloc[-1]
        previous = hist['Close'].iloc[-2]
        return float(((current - previous) / previous) * 100)
