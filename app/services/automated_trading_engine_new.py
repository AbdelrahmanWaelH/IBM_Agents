import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random
from enum import Enum
from services.stock_service import StockService
from services.news_service import NewsService
from services.ai_service import AITradingService
from services.db_portfolio_service import DatabasePortfolioService
from models import TradeAction

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    ANALYSIS_ONLY = "analysis_only"  # AI analysis only, no automatic trades
    FULL_CONTROL = "full_control"    # AI makes and executes trades automatically

class AutomatedTradingEngine:
    def __init__(self):
        self.stock_service = StockService()
        self.news_service = NewsService()
        self.ai_service = AITradingService()
        self.portfolio_service = DatabasePortfolioService()
        self.is_running = False
        
        # Trading configuration
        self.trading_symbols = self._load_trading_symbols()
        self.analysis_interval = 300  # 5 minutes  
        self.max_daily_trades = 10
        self.daily_trade_count = 0
        self.last_trade_reset = datetime.now().date()
        self.rate_limit_delay = 8  # 8 seconds between API calls
        
        # Trading mode - default to analysis only for safety
        self.trading_mode = TradingMode.ANALYSIS_ONLY
        self.min_confidence_threshold = 0.75  # Only execute trades with high confidence
        
        logger.info(f"AutomatedTradingEngine initialized in {self.trading_mode.value} mode")
        
    def _load_trading_symbols(self) -> List[str]:
        """Load trading symbols from configuration"""
        import os
        
        # Try to load from environment variable first
        env_symbols = os.getenv('TRADING_SYMBOLS')
        if env_symbols:
            return [s.strip().upper() for s in env_symbols.split(',')]
        
        # Default symbols - focus on well-known, liquid stocks
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", 
            "NVDA", "META", "JPM", "V", "JNJ"
        ]
        
    async def start_trading(self):
        """Start the automated trading engine"""
        if self.is_running:
            logger.warning("Trading engine is already running")
            return
            
        self.is_running = True
        logger.info(f"🚀 Starting automated trading engine in {self.trading_mode.value} mode")
        
        try:
            while self.is_running:
                await self._trading_cycle()
                
                # Wait for next cycle
                logger.info(f"⏱️  Waiting {self.analysis_interval} seconds until next analysis cycle")
                await asyncio.sleep(self.analysis_interval)
                
        except Exception as e:
            logger.error(f"Critical error in trading engine: {e}")
        finally:
            self.is_running = False
            logger.info("🛑 Automated trading engine stopped")
            
    async def stop_trading(self):
        """Stop the automated trading engine"""
        self.is_running = False
        logger.info("🛑 Stopping automated trading engine...")
        
    async def _trading_cycle(self):
        """Execute one complete trading cycle"""
        try:
            # Reset daily count if it's a new day
            current_date = datetime.now().date()
            if current_date != self.last_trade_reset:
                self.daily_trade_count = 0
                self.last_trade_reset = current_date
                logger.info(f"📅 New trading day - reset daily trade count")
            
            # Check daily trade limit (only for full control mode)
            if self.trading_mode == TradingMode.FULL_CONTROL and self.daily_trade_count >= self.max_daily_trades:
                logger.info(f"📈 Daily trade limit reached ({self.max_daily_trades}). Analysis continues but no trades will be executed.")
                # Continue with analysis but don't execute trades
            
            # Select symbols to analyze (fewer for better rate limiting)
            symbols_to_analyze = random.sample(self.trading_symbols, min(2, len(self.trading_symbols)))
            
            logger.info(f"🔍 Analyzing {len(symbols_to_analyze)} symbols: {', '.join(symbols_to_analyze)}")
            
            # Get portfolio context
            portfolio = await self.portfolio_service.get_portfolio()
            portfolio_context = {
                "cash_balance": portfolio.cash_balance,
                "total_value": portfolio.total_value,
                "holdings": portfolio.holdings
            }
            
            # Analyze current holdings first
            await self._analyze_current_holdings(portfolio_context)
            
            # Analyze new symbols
            successful_analyses = 0
            for i, symbol in enumerate(symbols_to_analyze):
                try:
                    success = await self._analyze_and_decide_symbol(symbol, portfolio_context)
                    if success:
                        successful_analyses += 1
                    
                    # Rate limiting between API calls
                    if i < len(symbols_to_analyze) - 1:
                        await asyncio.sleep(self.rate_limit_delay)
                        
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {e}")
                    await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"📊 Trading cycle completed. Mode: {self.trading_mode.value}, Successful analyses: {successful_analyses}/{len(symbols_to_analyze)}, Daily trades: {self.daily_trade_count}/{self.max_daily_trades}")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    async def _analyze_current_holdings(self, portfolio_context: dict):
        """Analyze current portfolio holdings with news sentiment"""
        try:
            holdings = portfolio_context.get("holdings", [])
            if not holdings:
                logger.info("📝 No current holdings to analyze")
                return
            
            logger.info(f"📊 Analyzing {len(holdings)} current holdings")
            
            for holding in holdings:
                try:
                    symbol = holding.symbol
                    logger.info(f"🔍 Analyzing current holding: {symbol} ({holding.quantity} shares)")
                    
                    # Get fresh stock data
                    stock_info = await self.stock_service.get_stock_info(symbol)
                    if not stock_info:
                        logger.warning(f"⚠️ Could not get current market data for holding {symbol}")
                        continue
                    
                    # Get news for sentiment analysis
                    news_items = []
                    try:
                        news_items = await self.news_service.get_stock_news(symbol)
                        logger.info(f"📰 Found {len(news_items)} news items for {symbol}")
                    except Exception as e:
                        logger.warning(f"Could not fetch news for {symbol}: {e}")
                    
                    # Get AI analysis
                    decision = await self.ai_service.analyze_and_decide(
                        stock_info, 
                        news_items, 
                        portfolio_context
                    )
                    
                    # Calculate current P&L for this holding
                    current_value = holding.quantity * stock_info.current_price
                    cost_basis = holding.quantity * holding.avg_price
                    profit_loss = current_value - cost_basis
                    profit_loss_percent = (profit_loss / cost_basis) * 100 if cost_basis > 0 else 0
                    
                    logger.info(f"💰 {symbol} P&L: ${profit_loss:+.2f} ({profit_loss_percent:+.1f}%) | AI Recommendation: {decision.action.value} (confidence: {decision.confidence:.1%})")
                    
                    # In full control mode, execute sell decisions for holdings
                    if (self.trading_mode == TradingMode.FULL_CONTROL and 
                        decision.action == TradeAction.SELL and 
                        decision.confidence >= self.min_confidence_threshold and
                        self.daily_trade_count < self.max_daily_trades):
                        
                        try:
                            # Limit sell quantity to current holdings
                            sell_quantity = min(decision.quantity, holding.quantity)
                            await self._execute_trade_decision(decision, stock_info, sell_quantity)
                            self.daily_trade_count += 1
                            logger.info(f"✅ Executed SELL for holding {symbol}: {sell_quantity} shares")
                        except Exception as e:
                            logger.error(f"❌ Failed to execute sell for {symbol}: {e}")
                    
                    # Add delay between holdings analysis
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error analyzing holding {holding.symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error analyzing current holdings: {e}")
    
    async def _analyze_and_decide_symbol(self, symbol: str, portfolio_context: dict) -> bool:
        """Analyze a specific symbol and potentially execute trades"""
        try:
            # Get stock information with robust error handling
            stock_info = None
            for attempt in range(3):
                try:
                    stock_info = await self.stock_service.get_stock_info(symbol)
                    if stock_info:
                        break
                    logger.warning(f"Attempt {attempt + 1}: No stock data returned for {symbol}")
                    if attempt < 2:
                        await asyncio.sleep(5)
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                    if attempt < 2:
                        await asyncio.sleep(10)
            
            if not stock_info:
                logger.error(f"❌ Could not get stock info for {symbol} after 3 attempts")
                return False
            
            # Validate stock data
            if not stock_info.current_price or stock_info.current_price <= 0:
                logger.error(f"❌ Invalid price data for {symbol}: {stock_info.current_price}")
                return False
            
            # Get news for analysis
            news_items = []
            try:
                news_items = await self.news_service.get_stock_news(symbol)
                logger.info(f"📰 Found {len(news_items)} news items for {symbol}")
            except Exception as e:
                logger.warning(f"Could not fetch news for {symbol}: {e}")
            
            # Get AI decision
            try:
                decision = await self.ai_service.analyze_and_decide(
                    stock_info, 
                    news_items, 
                    portfolio_context
                )
            except Exception as e:
                logger.error(f"❌ AI analysis failed for {symbol}: {e}")
                return False
            
            if not decision:
                logger.warning(f"⚠️ No trading decision generated for {symbol}")
                return False
            
            logger.info(f"🤖 AI Analysis for {symbol}: {decision.action.value} {decision.quantity} shares at ${decision.suggested_price:.2f} (confidence: {decision.confidence:.1%})")
            logger.info(f"📋 Reasoning: {decision.reasoning[:150]}...")
            
            # Execute trade based on mode and decision
            if (self.trading_mode == TradingMode.FULL_CONTROL and 
                decision.action != TradeAction.HOLD and 
                decision.confidence >= self.min_confidence_threshold and
                self.daily_trade_count < self.max_daily_trades):
                
                try:
                    await self._execute_trade_decision(decision, stock_info)
                    self.daily_trade_count += 1
                    logger.info(f"✅ Trade executed for {symbol}: {decision.action.value} {decision.quantity} shares")
                except Exception as e:
                    logger.error(f"❌ Trade execution failed for {symbol}: {e}")
            else:
                reason = []
                if self.trading_mode == TradingMode.ANALYSIS_ONLY:
                    reason.append("analysis-only mode")
                if decision.action == TradeAction.HOLD:
                    reason.append("hold recommendation")
                if decision.confidence < self.min_confidence_threshold:
                    reason.append(f"low confidence ({decision.confidence:.1%})")
                if self.daily_trade_count >= self.max_daily_trades:
                    reason.append("daily limit reached")
                
                logger.info(f"⏭️ No trade executed for {symbol}: {', '.join(reason)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return False
    
    async def _execute_trade_decision(self, decision, stock_info, override_quantity: Optional[int] = None):
        """Execute a trade decision with validation"""
        
        quantity = override_quantity or decision.quantity
        
        # Validate trade parameters
        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}")
        
        if decision.suggested_price <= 0:
            raise ValueError(f"Invalid price: {decision.suggested_price}")
        
        # Check portfolio constraints
        portfolio = await self.portfolio_service.get_portfolio()
        
        if decision.action == TradeAction.BUY:
            required_cash = quantity * decision.suggested_price
            if required_cash > portfolio.cash_balance * 0.9:
                raise ValueError(f"Insufficient cash (need ${required_cash:.2f}, have ${portfolio.cash_balance:.2f})")
        
        elif decision.action == TradeAction.SELL:
            holding = next((h for h in portfolio.holdings if h.symbol == decision.symbol), None)
            if not holding or holding.quantity < quantity:
                available = holding.quantity if holding else 0
                raise ValueError(f"Insufficient shares (need {quantity}, have {available})")
        
        # Execute the trade
        await self.portfolio_service.execute_trade(
            symbol=decision.symbol,
            action=decision.action,
            quantity=quantity,
            price=decision.suggested_price,
            decision_id=getattr(decision, 'decision_id', None)
        )
        
        logger.info(f"💼 Trade executed: {decision.action.value} {quantity} {decision.symbol} @ ${decision.suggested_price:.2f}")

    def get_engine_status(self) -> dict:
        """Get current status of the trading engine"""
        return {
            "is_running": self.is_running,
            "trading_mode": self.trading_mode.value,
            "daily_trade_count": self.daily_trade_count,
            "max_daily_trades": self.max_daily_trades,
            "monitored_symbols": self.trading_symbols,
            "analysis_interval_seconds": self.analysis_interval,
            "min_confidence_threshold": self.min_confidence_threshold,
            "last_trade_reset": self.last_trade_reset.isoformat() if self.last_trade_reset else None
        }
    
    def set_trading_mode(self, mode: TradingMode):
        """Set the trading mode"""
        if self.is_running:
            raise ValueError("Cannot change trading mode while engine is running")
        
        old_mode = self.trading_mode
        self.trading_mode = mode
        logger.info(f"Trading mode changed from {old_mode.value} to {mode.value}")
    
    def update_trading_symbols(self, symbols: List[str]):
        """Update the list of trading symbols"""
        if self.is_running:
            raise ValueError("Cannot update symbols while engine is running")
        
        clean_symbols = [s.strip().upper() for s in symbols if s.strip()]
        if not clean_symbols:
            raise ValueError("Symbol list cannot be empty")
        
        self.trading_symbols = clean_symbols
        logger.info(f"Updated trading symbols: {', '.join(self.trading_symbols)}")
    
    def update_analysis_interval(self, interval_seconds: int):
        """Update the analysis interval"""
        if self.is_running:
            raise ValueError("Cannot update interval while engine is running")
        
        if interval_seconds < 120 or interval_seconds > 3600:
            raise ValueError("Analysis interval must be between 120 and 3600 seconds")
        
        self.analysis_interval = interval_seconds
        logger.info(f"Updated analysis interval to {interval_seconds} seconds")
    
    def update_max_daily_trades(self, max_trades: int):
        """Update maximum daily trades"""
        if self.is_running:
            raise ValueError("Cannot update max trades while engine is running")
        
        if max_trades < 1 or max_trades > 50:
            raise ValueError("Max daily trades must be between 1 and 50")
        
        self.max_daily_trades = max_trades
        logger.info(f"Updated max daily trades to {max_trades}")
    
    def update_confidence_threshold(self, threshold: float):
        """Update minimum confidence threshold for trade execution"""
        if self.is_running:
            raise ValueError("Cannot update confidence threshold while engine is running")
        
        if threshold < 0.5 or threshold > 1.0:
            raise ValueError("Confidence threshold must be between 0.5 and 1.0")
        
        self.min_confidence_threshold = threshold
        logger.info(f"Updated confidence threshold to {threshold:.1%}")

# Global trading engine instance
trading_engine = AutomatedTradingEngine()
