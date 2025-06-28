import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import random
from enum import Enum
from services.stock_service import StockService
from services.news_service import NewsService
from services.ai_service import AITradingService
from services.db_portfolio_service import DatabasePortfolioService
from services.websocket_manager import trading_ws_manager
from services.company_search_service import company_search_service
from models import TradeAction
import concurrent.futures
import time

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
            
            # Enhanced symbol selection - use more symbols but with intelligent filtering
            all_symbols = self.trading_symbols.copy()
            
            # Get portfolio context
            portfolio = await self.portfolio_service.get_portfolio()
            portfolio_context = {
                "cash_balance": portfolio.cash_balance,
                "total_value": portfolio.total_value,
                "holdings": portfolio.holdings
            }
            
            # Analyze current holdings first with concurrency
            logger.info("🔍 Analyzing current holdings with enhanced concurrency")
            await self._analyze_current_holdings_enhanced(portfolio_context)
            
            # Select symbols for new analysis (more intelligent selection)
            symbols_to_analyze = self._select_symbols_for_analysis(all_symbols, portfolio_context)
            logger.info(f"🎯 Selected {len(symbols_to_analyze)} symbols for analysis: {', '.join(symbols_to_analyze)}")
            
            # Use concurrent analysis for better performance
            if symbols_to_analyze:
                logger.info(f"🚀 Starting concurrent analysis of {len(symbols_to_analyze)} symbols")
                
                # Limit concurrent analyses to avoid overwhelming APIs
                max_concurrent = 3
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def analyze_with_rate_limit(symbol):
                    async with semaphore:
                        try:
                            success = await self._analyze_and_decide_symbol(symbol, portfolio_context)
                            await asyncio.sleep(2)  # Rate limiting between analyses
                            return success
                        except Exception as e:
                            logger.error(f"Error analyzing {symbol}: {e}")
                            return False
                
                # Execute analyses concurrently
                tasks = [analyze_with_rate_limit(symbol) for symbol in symbols_to_analyze]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successful analyses
                successful_analyses = sum(1 for result in results if result is True)
                
                logger.info(f"📊 Enhanced trading cycle completed. Mode: {self.trading_mode.value}, "
                          f"Successful analyses: {successful_analyses}/{len(symbols_to_analyze)}, "
                          f"Daily trades: {self.daily_trade_count}/{self.max_daily_trades}")
            else:
                logger.info("📊 No new symbols to analyze this cycle")
            
            # Notify about cycle completion via WebSocket
            await trading_ws_manager.notify_engine_status({
                "cycle_completed": True,
                "symbols_analyzed": len(symbols_to_analyze),
                "daily_trades": self.daily_trade_count,
                "max_daily_trades": self.max_daily_trades,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in enhanced trading cycle: {e}")
    
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
        """Analyze a specific symbol and potentially execute trades with enhanced reliability"""
        try:
            logger.info(f"🎯 Enhanced analysis starting for {symbol}")
            
            # Get stock information with enhanced error handling and retries
            stock_info = await self._get_stock_info_with_retries(symbol, max_retries=3)
            if not stock_info:
                logger.error(f"❌ Could not get stock info for {symbol} after retries")
                return False
            
            # Validate stock data quality
            if not self._validate_stock_data(stock_info):
                logger.error(f"❌ Invalid stock data for {symbol}")
                return False
            
            # Get news with timeout protection
            news_items = await self._get_news_with_timeout(symbol, timeout=10)
            logger.info(f"📰 Found {len(news_items)} news items for {symbol}")
            
            # Get AI decision using enhanced service
            try:
                decision = await self.ai_service.analyze_opportunity_comprehensive(symbol, portfolio_context)
                logger.info(f"🤖 AI Decision for {symbol}: {decision.action.value.upper()} "
                          f"(confidence: {decision.confidence:.1%}, quantity: {decision.quantity})")
                
                # Show more of the reasoning (not truncated)
                reasoning_preview = decision.reasoning[:500] + "..." if len(decision.reasoning) > 500 else decision.reasoning
                logger.info(f"💭 AI Reasoning preview: {reasoning_preview}")
                
            except Exception as e:
                logger.error(f"❌ AI analysis failed for {symbol}: {e}")
                return False
            
            if not decision:
                logger.warning(f"⚠️ No trading decision generated for {symbol}")
                return False
            
            # Enhanced trade execution logic
            trade_executed = False
            if (self.trading_mode == TradingMode.FULL_CONTROL and 
                decision.action != TradeAction.HOLD and 
                decision.confidence >= self.min_confidence_threshold and
                self.daily_trade_count < self.max_daily_trades):
                
                try:
                    # Execute trade with enhanced validation and feedback
                    await self._execute_trade_decision_enhanced(decision, stock_info)
                    self.daily_trade_count += 1
                    trade_executed = True
                    logger.info(f"✅ TRADE EXECUTED for {symbol}: {decision.action.value} {decision.quantity} shares at ${decision.suggested_price:.2f}")
                    
                    # Notify via WebSocket
                    await trading_ws_manager.notify_trade_execution({
                        "symbol": symbol,
                        "action": decision.action.value,
                        "quantity": decision.quantity,
                        "price": decision.suggested_price,
                        "confidence": decision.confidence,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"❌ Trade execution failed for {symbol}: {e}")
                    # Still mark as successful analysis even if trade failed
            else:
                # Log detailed reasons why trade wasn't executed
                reasons = []
                if self.trading_mode == TradingMode.ANALYSIS_ONLY:
                    reasons.append("analysis-only mode")
                if decision.action == TradeAction.HOLD:
                    reasons.append("hold recommendation")
                if decision.confidence < self.min_confidence_threshold:
                    reasons.append(f"low confidence ({decision.confidence:.1%} < {self.min_confidence_threshold:.1%})")
                if self.daily_trade_count >= self.max_daily_trades:
                    reasons.append("daily limit reached")
                
                logger.info(f"⏭️ No trade executed for {symbol}: {', '.join(reasons)}")
            
            # Mark decision as executed in database if trade was successful
            if trade_executed and decision.decision_id:
                await self.ai_service.mark_decision_executed(decision.decision_id)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Enhanced analysis error for {symbol}: {e}")
            return False
    
    async def _get_stock_info_with_retries(self, symbol: str, max_retries: int = 3):
        """Get stock information with retry logic and better error handling"""
        for attempt in range(max_retries):
            try:
                stock_info = await self.stock_service.get_stock_info(symbol)
                if stock_info and self._validate_stock_data(stock_info):
                    return stock_info
                
                logger.warning(f"Attempt {attempt + 1}: Invalid stock data for {symbol}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(10 * (attempt + 1))
        
        return None
    
    def _validate_stock_data(self, stock_info) -> bool:
        """Validate stock data quality"""
        if not stock_info:
            return False
        
        if not stock_info.current_price or stock_info.current_price <= 0:
            return False
        
        # Additional validations
        if stock_info.current_price > 100000:  # Unrealistic price
            return False
        
        return True
    
    async def _get_news_with_timeout(self, symbol: str, timeout: int = 10):
        """Get news with timeout protection"""
        try:
            return await asyncio.wait_for(
                self.news_service.get_stock_news(symbol), 
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"News fetch timeout for {symbol}")
            return []
        except Exception as e:
            logger.warning(f"Could not fetch news for {symbol}: {e}")
            return []
    
    async def _execute_trade_decision_enhanced(self, decision, stock_info, override_quantity: Optional[int] = None):
        """Enhanced trade execution with better validation and error handling"""
        
        quantity = override_quantity or decision.quantity
        
        # Enhanced validation
        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}")
        
        if decision.suggested_price <= 0:
            raise ValueError(f"Invalid price: {decision.suggested_price}")
        
        # Check portfolio constraints with detailed logging
        portfolio = await self.portfolio_service.get_portfolio()
        logger.info(f"💰 Portfolio state: Cash=${portfolio.cash_balance:.2f}, Total=${portfolio.total_value:.2f}")
        
        if decision.action == TradeAction.BUY:
            required_cash = quantity * decision.suggested_price
            available_cash = portfolio.cash_balance * 0.95  # Use 95% to leave buffer
            
            if required_cash > available_cash:
                # Try to adjust quantity to fit available cash
                adjusted_quantity = int(available_cash / decision.suggested_price)
                if adjusted_quantity > 0:
                    logger.warning(f"⚠️ Adjusting quantity from {quantity} to {adjusted_quantity} due to cash constraints")
                    quantity = adjusted_quantity
                else:
                    raise ValueError(f"Insufficient cash (need ${required_cash:.2f}, have ${available_cash:.2f})")
        
        elif decision.action == TradeAction.SELL:
            holding = next((h for h in portfolio.holdings if h.symbol == decision.symbol), None)
            if not holding or holding.quantity < quantity:
                available = holding.quantity if holding else 0
                if available > 0:
                    logger.warning(f"⚠️ Adjusting sell quantity from {quantity} to {available}")
                    quantity = available
                else:
                    raise ValueError(f"Insufficient shares (need {quantity}, have {available})")
        
        # Execute the trade with enhanced logging
        logger.info(f"🔄 Executing trade: {decision.action.value} {quantity} {decision.symbol} @ ${decision.suggested_price:.2f}")
        
        success = await self.portfolio_service.execute_trade(
            symbol=decision.symbol,
            action=decision.action,
            quantity=quantity,
            price=decision.suggested_price,
            decision_id=getattr(decision, 'decision_id', None)
        )
        
        if not success:
            raise ValueError("Trade execution failed in portfolio service")
        
        logger.info(f"💼 Trade executed successfully: {decision.action.value} {quantity} {decision.symbol} @ ${decision.suggested_price:.2f}")
        return True
    
    async def _execute_trade_decision(self, decision, stock_info, override_quantity: Optional[int] = None):
        """Execute a trade decision with validation - legacy method for compatibility"""
        return await self._execute_trade_decision_enhanced(decision, stock_info, override_quantity)

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
    
    def _select_symbols_for_analysis(self, all_symbols: List[str], portfolio_context: dict) -> List[str]:
        """Intelligently select symbols for analysis based on various factors"""
        try:
            # Start with a base selection
            base_count = min(4, len(all_symbols))  # Analyze more symbols
            
            # Prioritize symbols not currently in portfolio
            holdings_symbols = {holding.symbol for holding in portfolio_context.get('holdings', [])}
            non_holdings = [s for s in all_symbols if s not in holdings_symbols]
            
            # Mix of random selection and priority symbols
            priority_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']
            available_priority = [s for s in priority_symbols if s in all_symbols and s not in holdings_symbols]
            
            selected = []
            
            # Add 1-2 priority symbols if available
            if available_priority:
                selected.extend(random.sample(available_priority, min(2, len(available_priority))))
            
            # Fill remaining with random non-holdings
            remaining_needed = base_count - len(selected)
            if remaining_needed > 0 and non_holdings:
                available_non_priority = [s for s in non_holdings if s not in selected]
                if available_non_priority:
                    selected.extend(random.sample(available_non_priority, min(remaining_needed, len(available_non_priority))))
            
            # If still need more, add some random symbols
            if len(selected) < base_count:
                remaining = [s for s in all_symbols if s not in selected]
                if remaining:
                    selected.extend(random.sample(remaining, min(base_count - len(selected), len(remaining))))
            
            return selected[:base_count]
            
        except Exception as e:
            logger.error(f"Error selecting symbols: {e}")
            return random.sample(all_symbols, min(2, len(all_symbols)))
    
    async def _analyze_current_holdings_enhanced(self, portfolio_context: dict):
        """Analyze current portfolio holdings with enhanced concurrency and WebSocket updates"""
        try:
            holdings = portfolio_context.get('holdings', [])
            if not holdings:
                logger.info("📝 No current holdings to analyze")
                return
            
            logger.info(f"🔍 Analyzing {len(holdings)} current holdings with enhanced methods")
            
            # Use the AI service's concurrent analysis method
            holding_symbols = [holding.symbol for holding in holdings]
            
            # Analyze holdings concurrently but with smaller batch size
            if holding_symbols:
                decisions = await self.ai_service.analyze_multiple_opportunities_concurrent(
                    holding_symbols, portfolio_context, max_concurrent=2
                )
                
                # Process decisions for holdings
                for symbol, decision in decisions.items():
                    if decision and decision.action == TradeAction.SELL:
                        holding = next((h for h in holdings if h.symbol == symbol), None)
                        if holding:
                            logger.info(f"🔍 Holdings analysis for {symbol}: {decision.action.value} "
                                      f"(confidence: {decision.confidence:.1%})")
                            
                            # In full control mode, execute sell decisions for holdings
                            if (self.trading_mode == TradingMode.FULL_CONTROL and 
                                decision.confidence >= self.min_confidence_threshold and
                                self.daily_trade_count < self.max_daily_trades):
                                
                                try:
                                    # Limit sell quantity to current holdings
                                    sell_quantity = min(decision.quantity, holding.quantity)
                                    await self._execute_trade_decision_enhanced(decision, None, sell_quantity)
                                    self.daily_trade_count += 1
                                    logger.info(f"✅ Executed SELL for holding {symbol}: {sell_quantity} shares")
                                except Exception as e:
                                    logger.error(f"❌ Failed to execute sell for {symbol}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced holdings analysis: {e}")

# Create a global instance of the trading engine
trading_engine = AutomatedTradingEngine()
