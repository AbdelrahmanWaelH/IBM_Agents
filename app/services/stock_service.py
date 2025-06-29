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
        self.cache_duration = 300  # 5 minutes cache
        self.last_request_time = {}  # Track per-symbol request times
        self.min_request_interval = 3  # 3 seconds between requests per symbol
        self.global_last_request = 0
        self.global_min_interval = 1.0  # 1 second between any requests
        
        logger.info("StockService initialized with enhanced rate limiting and no mock data")
        
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
        
        # Check cache first
        if self._is_cache_valid(symbol):
            logger.info(f"Returning cached data for {symbol}")
            return self.cache[symbol]['data']
        
        # Apply rate limiting
        self._rate_limit_global()
        self._rate_limit_symbol(symbol)
        
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching real data for {symbol} (attempt {attempt+1}/{max_retries})")
                
                # Create ticker without custom session (let yfinance handle it)
                ticker = yf.Ticker(symbol)
                
                # Get historical data first (more reliable)
                hist = ticker.history(period="5d", interval="1d")
                
                if hist.empty:
                    logger.warning(f"No historical data available for {symbol} - possibly delisted or invalid")
                    if attempt == max_retries - 1:
                        return None  # Return None instead of raising exception
                    continue
                
                # Get current price from most recent data
                current_price = float(hist['Close'].iloc[-1])
                volume = int(hist['Volume'].iloc[-1]) if not hist['Volume'].empty else 0
                
                # Calculate change percent
                change_percent = 0.0
                if len(hist) >= 2:
                    previous_close = float(hist['Close'].iloc[-2])
                    change_percent = ((current_price - previous_close) / previous_close) * 100
                
                # Try to get additional market data
                market_cap = None
                try:
                    # Use a more targeted approach for info
                    info = ticker.info
                    if info and isinstance(info, dict):
                        market_cap = info.get('marketCap')
                        # Validate the data makes sense
                        if market_cap and market_cap <= 0:
                            market_cap = None
                except Exception as info_error:
                    logger.warning(f"Could not fetch market cap for {symbol}: {info_error}")
                
                # Validate price data
                if current_price <= 0:
                    logger.warning(f"Invalid price data for {symbol}: {current_price}")
                    return None
                
                stock_info = StockInfo(
                    symbol=symbol,
                    current_price=round(current_price, 2),
                    market_cap=market_cap,
                    volume=volume,
                    change_percent=round(change_percent, 2)
                )
                
                # Cache the successful result
                self.cache[symbol] = {
                    'data': stock_info,
                    'timestamp': time.time()
                }
                
                logger.info(f"Successfully fetched real data for {symbol}: ${current_price:.2f} ({change_percent:+.2f}%)")
                return stock_info
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error fetching stock info for {symbol} (attempt {attempt+1}): {error_msg}")
                
                # Check if it's a rate limiting error
                if '429' in error_msg or 'Too Many Requests' in error_msg:
                    wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limited by Yahoo Finance. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                elif 'Invalid symbol' in error_msg or 'not found' in error_msg.lower() or 'delisted' in error_msg.lower():
                    logger.info(f"Symbol {symbol} not found or delisted")
                    return None
                else:
                    # For other errors, wait briefly before retry
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
        
        # If all attempts failed, return None (no mock data)
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
