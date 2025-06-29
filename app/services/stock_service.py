import yfinance as yf
from typing import List, Dict, Optional
from models import StockInfo
import logging
import time
import asyncio
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StockDataException(Exception):
    """Custom exception for stock data retrieval errors"""
    pass

class StockService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 180  # 3 minutes cache (reduced from 5)
        # Remove aggressive rate limiting for faster responses
        logger.info("StockService initialized with optimized caching")
        
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached data is still valid"""
        if symbol not in self.cache:
            return False
        return time.time() - self.cache[symbol]['timestamp'] < self.cache_duration
    
    def _validate_symbol(self, symbol: str) -> str:
        """Validate and clean symbol format"""
        if not symbol or not isinstance(symbol, str):
            raise StockDataException("Invalid symbol provided")
        
        symbol = symbol.strip().upper()
        if not symbol.isalnum() and '.' not in symbol:
            raise StockDataException(f"Invalid symbol format: {symbol}")
        
        return symbol

    async def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """Get current stock information with robust error handling and NO mock data"""
        try:
            symbol = self._validate_symbol(symbol)
        except StockDataException as e:
            logger.error(f"Symbol validation failed: {e}")
            return None
        
        # Check cache first - much faster!
        if self._is_cache_valid(symbol):
            logger.info(f"⚡ Cache hit for {symbol}")
            return self.cache[symbol]['data']
        
        # Optimized single attempt with faster timeout
        try:
            logger.info(f"⚡ Fast fetch for {symbol}")
            
            # Create ticker and get data in one call
            ticker = yf.Ticker(symbol)
            
            # Get recent data with shorter period for speed
            hist = ticker.history(period="2d", interval="1d")
            
            if hist.empty or len(hist) == 0:
                logger.warning(f"⚠️ No data for {symbol}")
                return None
            
            # Extract data quickly
            current_price = float(hist['Close'].iloc[-1])
            volume = int(hist['Volume'].iloc[-1]) if len(hist['Volume']) > 0 else 0
            
            # Simple change calculation
            change_percent = 0.0
            if len(hist) >= 2:
                previous_close = float(hist['Close'].iloc[-2])
                change_percent = ((current_price - previous_close) / previous_close) * 100
            
            # Skip market cap for speed - can be fetched separately if needed
            market_cap = None
            
            # Validate price
            if current_price <= 0:
                logger.warning(f"⚠️ Invalid price for {symbol}: {current_price}")
                return None
            
            stock_info = StockInfo(
                symbol=symbol,
                current_price=round(current_price, 2),
                market_cap=market_cap,
                volume=volume,
                change_percent=round(change_percent, 2)
            )
            
            # Cache the result for faster future requests
            self.cache[symbol] = {
                'data': stock_info,
                'timestamp': time.time()
            }
            
            logger.info(f"⚡ Fast data fetched for {symbol}: ${current_price:.2f} ({change_percent:+.2f}%)")
            return stock_info
            
        except Exception as e:
            logger.error(f"❌ Fast fetch failed for {symbol}: {e}")
            return None
        logger.error(f"Failed to fetch stock data for {symbol} after {max_retries} attempts")
        return None

    async def get_multiple_stocks(self, symbols: List[str]) -> List[StockInfo]:
        """Get information for multiple stocks with proper rate limiting"""
        if not symbols:
            return []
        
        logger.info(f"Fetching data for {len(symbols)} symbols: {symbols}")
        stocks = []
        
        for i, symbol in enumerate(symbols):
            try:
                # Add delay between requests to respect rate limits
                if i > 0:
                    await asyncio.sleep(2)
                
                stock_info = await self.get_stock_info(symbol)
                if stock_info:
                    stocks.append(stock_info)
                else:
                    logger.warning(f"Skipping {symbol} - no valid data available")
                    
            except Exception as e:
                logger.error(f"Error processing symbol {symbol}: {e}")
                continue
        
        logger.info(f"Successfully fetched data for {len(stocks)}/{len(symbols)} symbols")
        return stocks

    async def get_stocks_batch(self, symbols: list[str]) -> dict[str, StockInfo]:
        """Fast batch fetching of multiple stocks"""
        results = {}
        
        # Check cache first for all symbols
        uncached_symbols = []
        for symbol in symbols:
            if self._is_cache_valid(symbol):
                results[symbol] = self.cache[symbol]['data']
                logger.info(f"⚡ Cache hit for {symbol}")
            else:
                uncached_symbols.append(symbol)
        
        if not uncached_symbols:
            logger.info(f"⚡ All {len(symbols)} symbols served from cache")
            return results
        
        # Fetch uncached symbols concurrently
        logger.info(f"⚡ Fast batch fetch for {len(uncached_symbols)} symbols")
        
        async def fetch_single(symbol):
            try:
                return symbol, await self.get_stock_info(symbol)
            except Exception as e:
                logger.warning(f"Failed to fetch {symbol}: {e}")
                return symbol, None
        
        # Use asyncio.gather for concurrent fetching
        import asyncio
        fetch_tasks = [fetch_single(symbol) for symbol in uncached_symbols]
        fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        # Collect results
        for result in fetch_results:
            if isinstance(result, tuple) and len(result) == 2:
                symbol, stock_info = result
                if stock_info:
                    results[symbol] = stock_info
        
        logger.info(f"⚡ Batch fetch complete: {len(results)}/{len(symbols)} symbols")
        return results

    def clear_cache(self):
        """Clear the entire cache"""
        self.cache.clear()
        logger.info("Stock data cache cleared")

    def get_cache_status(self) -> Dict:
        """Get cache statistics"""
        current_time = time.time()
        valid_entries = sum(1 for entry in self.cache.values() 
                           if current_time - entry['timestamp'] < self.cache_duration)
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'cache_duration_seconds': self.cache_duration
        }
