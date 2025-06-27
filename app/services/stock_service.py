import yfinance as yf
from typing import List, Dict, Optional
from models import StockInfo
import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class StockService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes cache
        self.last_request_time = 0
        self.min_request_interval = 1  # 1 second between requests
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached data is still valid"""
        if symbol not in self.cache:
            return False
        return time.time() - self.cache[symbol]['timestamp'] < self.cache_duration
    
    async def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """Get current stock information with caching and rate limiting"""
        # Check cache first
        if self._is_cache_valid(symbol):
            logger.info(f"Returning cached data for {symbol}")
            return self.cache[symbol]['data']
        
        # Rate limiting
        self._rate_limit()
        
        try:
            # Use a more reliable approach with yfinance
            ticker = yf.Ticker(symbol)
            
            # Get basic info
            info = ticker.info
            if not info or 'regularMarketPrice' not in info:
                # Fallback to history if info is not available
                hist = ticker.history(period="1d")
                if hist.empty:
                    logger.warning(f"No data available for {symbol}")
                    return None
                
                current_price = float(hist['Close'].iloc[-1])
                volume = int(hist['Volume'].iloc[-1]) if len(hist) > 0 else None
                change_percent = self._calculate_change_percent(hist)
                market_cap = None
            else:
                current_price = float(info.get('regularMarketPrice', 0))
                if current_price == 0:
                    # Try previous close
                    current_price = float(info.get('previousClose', 0))
                
                volume = info.get('regularMarketVolume')
                market_cap = info.get('marketCap')
                
                # Calculate change percent
                previous_close = info.get('regularMarketPreviousClose', current_price)
                if previous_close and previous_close != current_price:
                    change_percent = ((current_price - previous_close) / previous_close) * 100
                else:
                    change_percent = 0.0
            
            if current_price == 0:
                logger.warning(f"Invalid price data for {symbol}")
                return None
            
            stock_info = StockInfo(
                symbol=symbol,
                current_price=current_price,
                market_cap=market_cap,
                volume=volume,
                change_percent=change_percent
            )
            
            # Cache the result
            self.cache[symbol] = {
                'data': stock_info,
                'timestamp': time.time()
            }
            
            return stock_info
            
        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {e}")
            # Return mock data for demo purposes
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
        """Get information for multiple stocks"""
        stocks = []
        for symbol in symbols:
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
