from langchain_ibm import WatsonxLLM
from langchain.schema import SystemMessage, HumanMessage
from typing import List, Dict
from models import NewsItem, StockInfo, TradeDecision, TradeAction
from config import settings
import json
import logging
from database import SessionLocal, AIDecision, NewsAnalysis, StockAnalysis, SentimentEnum, TradeActionEnum
from datetime import datetime

logger = logging.getLogger(__name__)

class AITradingService:
    def __init__(self):
        self.llm = self._initialize_llm()
        self.db = SessionLocal()
    
    def _initialize_llm(self):
        """Initialize IBM Watsonx LLM"""
        try:
            # Extract just the numeric project ID
            project_id = settings.IBM_PROJECT_ID.split(' - ')[0].strip()
            
            return WatsonxLLM(
                model_id=settings.IBM_BASE_MODEL,
                url=settings.IBM_BASE_URL,
                apikey=settings.IBM_API_KEY,
                project_id=project_id,
                params={
                    "temperature": 0.3,
                    "max_new_tokens": 512,
                    "top_p": 0.9,
                    "top_k": 50
                }
            )
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            return None
    
    async def analyze_and_decide(self, 
                                stock_info: StockInfo, 
                                news_items: List[NewsItem],
                                portfolio_context: Dict = None) -> TradeDecision:
        """Analyze stock and news data to make trading decision"""
        
        # Validate input data
        if not stock_info:
            logger.error("Cannot analyze - no stock information provided")
            raise ValueError("Stock information is required for analysis")
        
        if not stock_info.current_price or stock_info.current_price <= 0:
            logger.error(f"Invalid stock price for {stock_info.symbol}: {stock_info.current_price}")
            raise ValueError(f"Invalid stock price data for {stock_info.symbol}")
        
        try:
            # Store stock analysis in database
            stock_analysis = StockAnalysis(
                symbol=stock_info.symbol,
                current_price=stock_info.current_price,
                market_cap=stock_info.market_cap,
                volume=stock_info.volume,
                change_percent=stock_info.change_percent
            )
            self.db.add(stock_analysis)
            self.db.flush()  # Get the ID
            
            # Store news analysis
            for news in news_items:
                sentiment = self._analyze_news_sentiment(news)
                news_analysis = NewsAnalysis(
                    symbol=stock_info.symbol,
                    title=news.title,
                    description=news.description,
                    url=news.url,
                    source=news.source,
                    sentiment=sentiment,
                    published_at=datetime.fromisoformat(news.published_at.replace('Z', '+00:00')) if isinstance(news.published_at, str) else news.published_at
                )
                self.db.add(news_analysis)
            
            # Get AI decision
            if self.llm:
                decision = await self._get_ai_decision(stock_info, news_items, portfolio_context)
            else:
                decision = self._fallback_decision(stock_info)
            
            # Store AI decision in database
            # Map TradeAction to TradeActionEnum
            action_mapping = {
                TradeAction.BUY: TradeActionEnum.BUY,
                TradeAction.SELL: TradeActionEnum.SELL,
                TradeAction.HOLD: TradeActionEnum.HOLD
            }
            
            ai_decision = AIDecision(
                symbol=stock_info.symbol,
                action=action_mapping.get(decision.action, TradeActionEnum.HOLD),
                quantity=decision.quantity,
                confidence=decision.confidence,
                reasoning=decision.reasoning,
                suggested_price=decision.suggested_price,
                stock_price=stock_info.current_price,
                stock_change_percent=stock_info.change_percent,
                portfolio_context=json.dumps(portfolio_context) if portfolio_context else None
            )
            self.db.add(ai_decision)
            
            # Link stock analysis to AI decision
            stock_analysis.ai_decision_id = ai_decision.id
            
            self.db.commit()
            
            # Update decision with database ID
            decision.decision_id = ai_decision.id
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            self.db.rollback()
            return self._fallback_decision(stock_info)
    
    async def _get_ai_decision(self, 
                              stock_info: StockInfo, 
                              news_items: List[NewsItem],
                              portfolio_context: Dict = None) -> TradeDecision:
        """Get AI decision from IBM Granite"""
        try:
            prompt = self._create_analysis_prompt(stock_info, news_items, portfolio_context)
            response = self.llm.invoke(prompt)
            
            # Parse the response to extract trading decision
            decision = self._parse_llm_response(response, stock_info)
            return decision
            
        except Exception as e:
            logger.error(f"Error in AI decision: {e}")
            return self._fallback_decision(stock_info)
    
    def _analyze_news_sentiment(self, news: NewsItem) -> SentimentEnum:
        """Analyze news sentiment"""
        # Simple keyword-based sentiment analysis
        text = f"{news.title} {news.description}".lower()
        
        positive_words = ['growth', 'profit', 'gain', 'rise', 'up', 'strong', 'positive', 'good', 'bullish', 'buy']
        negative_words = ['loss', 'decline', 'fall', 'down', 'weak', 'negative', 'bad', 'bearish', 'sell', 'crash']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return SentimentEnum.POSITIVE
        elif negative_count > positive_count:
            return SentimentEnum.NEGATIVE
        else:
            return SentimentEnum.NEUTRAL
    
    def _create_analysis_prompt(self, 
                               stock_info: StockInfo, 
                               news_items: List[NewsItem],
                               portfolio_context: Dict = None) -> str:
        """Create comprehensive prompt for trading analysis"""
        
        # Format news items
        news_text = ""
        for news in news_items[:5]:  # Limit to top 5 news items
            news_text += f"- {news.title}: {news.description}\n"
        
        # Format portfolio context
        portfolio_text = ""
        if portfolio_context:
            portfolio_text = f"""
Current Portfolio Status:
- Cash Balance: ${portfolio_context.get('cash_balance', 0):,.2f}
- Total Portfolio Value: ${portfolio_context.get('total_value', 0):,.2f}
- Current Holdings: {len(portfolio_context.get('holdings', []))} positions
"""
        
        prompt = f"""
You are an expert financial analyst and trader. Analyze the following information and make a trading recommendation.

STOCK INFORMATION:
Symbol: {stock_info.symbol}
Current Price: ${stock_info.current_price:.2f}
Market Cap: {stock_info.market_cap or 'N/A'}
Volume: {stock_info.volume or 'N/A'}
Price Change: {stock_info.change_percent or 0:.2f}%

RECENT NEWS:
{news_text}

{portfolio_text}

INSTRUCTIONS:
1. Analyze the stock's current technical indicators
2. Evaluate the sentiment and impact of recent news
3. Consider portfolio diversification and risk management
4. Make a trading recommendation (BUY, SELL, or HOLD)
5. Suggest quantity (as a percentage of available cash for BUY, or percentage of holdings for SELL)
6. Provide confidence level (0.0 to 1.0)
7. Give clear reasoning for your decision

Respond in the following JSON format:
{{
    "action": "BUY|SELL|HOLD",
    "confidence": 0.75,
    "quantity_percentage": 10,
    "reasoning": "Brief explanation of the decision",
    "key_factors": ["factor1", "factor2", "factor3"]
}}

Focus on paper trading simulation - prioritize learning and moderate risk-taking over extreme conservatism.
"""
        return prompt
    
    def _parse_llm_response(self, response: str, stock_info: StockInfo) -> TradeDecision:
        """Parse LLM response into TradeDecision object"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                
                action = TradeAction(data.get('action', 'hold').lower())
                confidence = float(data.get('confidence', 0.5))
                quantity_percentage = float(data.get('quantity_percentage', 5))
                reasoning = data.get('reasoning', 'AI analysis completed')
                
                # Calculate actual quantity based on percentage
                # For simplicity, assume $10,000 position size for BUY orders
                if action == TradeAction.BUY:
                    position_size = 10000 * (quantity_percentage / 100)
                    quantity = int(position_size / stock_info.current_price)
                else:
                    quantity = int(100 * (quantity_percentage / 100))  # Assume 100 shares max holding
                
                return TradeDecision(
                    symbol=stock_info.symbol,
                    action=action,
                    quantity=max(1, quantity),  # Ensure at least 1 share
                    confidence=confidence,
                    reasoning=reasoning,
                    suggested_price=stock_info.current_price
                )
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
        
        # Fallback if parsing fails
        return self._fallback_decision(stock_info)
    
    def _fallback_decision(self, stock_info: StockInfo) -> TradeDecision:
        """Simple fallback decision when AI is not available"""
        # Simple rule-based decision as backup
        change_percent = stock_info.change_percent or 0
        
        if change_percent > 2:
            action = TradeAction.BUY
            reasoning = "Stock showing strong positive momentum (>2% gain)"
        elif change_percent < -3:
            action = TradeAction.SELL
            reasoning = "Stock showing significant decline (>3% loss)"
        else:
            action = TradeAction.HOLD
            reasoning = "Stock price movement within normal range"
        
        return TradeDecision(
            symbol=stock_info.symbol,
            action=action,
            quantity=10,  # Default small position
            confidence=0.6,
            reasoning=reasoning,
            suggested_price=stock_info.current_price
        )
    
    async def get_ai_decisions_history(self, symbol: str = None, limit: int = 50) -> List[Dict]:
        """Get AI decision history"""
        try:
            query = self.db.query(AIDecision)
            if symbol:
                query = query.filter(AIDecision.symbol == symbol)
            
            decisions = query.order_by(AIDecision.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": decision.id,
                    "symbol": decision.symbol,
                    "action": decision.action.value,
                    "quantity": decision.quantity,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                    "suggested_price": decision.suggested_price,
                    "stock_price": decision.stock_price,
                    "stock_change_percent": decision.stock_change_percent,
                    "was_executed": decision.was_executed,
                    "created_at": decision.created_at.isoformat()
                }
                for decision in decisions
            ]
        except Exception as e:
            logger.error(f"Error getting AI decisions: {e}")
            return []
    
    async def get_stock_analysis_history(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Get stock analysis history"""
        try:
            analyses = self.db.query(StockAnalysis).filter(
                StockAnalysis.symbol == symbol
            ).order_by(StockAnalysis.analyzed_at.desc()).limit(limit).all()
            
            return [
                {
                    "symbol": analysis.symbol,
                    "current_price": analysis.current_price,
                    "market_cap": analysis.market_cap,
                    "volume": analysis.volume,
                    "change_percent": analysis.change_percent,
                    "analyzed_at": analysis.analyzed_at.isoformat()
                }
                for analysis in analyses
            ]
        except Exception as e:
            logger.error(f"Error getting stock analysis: {e}")
            return []
    
    async def get_news_analysis(self, symbol: str = None, limit: int = 20) -> List[Dict]:
        """Get news analysis with sentiment"""
        try:
            query = self.db.query(NewsAnalysis)
            if symbol:
                query = query.filter(NewsAnalysis.symbol == symbol)
            
            news = query.order_by(NewsAnalysis.analyzed_at.desc()).limit(limit).all()
            
            return [
                {
                    "symbol": item.symbol,
                    "title": item.title,
                    "description": item.description,
                    "url": item.url,
                    "source": item.source,
                    "sentiment": item.sentiment.value if item.sentiment else None,
                    "published_at": item.published_at.isoformat(),
                    "analyzed_at": item.analyzed_at.isoformat()
                }
                for item in news
            ]
        except Exception as e:
            logger.error(f"Error getting news analysis: {e}")
            return []
    
    async def mark_decision_executed(self, decision_id: int):
        """Mark an AI decision as executed"""
        try:
            decision = self.db.query(AIDecision).filter(AIDecision.id == decision_id).first()
            if decision:
                decision.was_executed = True
                self.db.commit()
        except Exception as e:
            logger.error(f"Error marking decision as executed: {e}")
            self.db.rollback()
    
    def __del__(self):
        """Close database connection"""
        if hasattr(self, 'db'):
            self.db.close()
