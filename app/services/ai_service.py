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
            
            # Store news analysis and log the news being analyzed
            logger.info(f"📰 Analyzing {len(news_items)} news articles for {stock_info.symbol}")
            for idx, news in enumerate(news_items, 1):
                logger.info(f"📄 News {idx}: {news.title[:100]}... from {news.source}")
                
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
                logger.info(f"📊 News sentiment for '{news.title[:50]}...': {sentiment.value if sentiment else 'neutral'}")
            
            if not news_items:
                logger.warning(f"⚠️ No news articles available for {stock_info.symbol} - analysis will be based on stock data only")
            
            # Get AI decision - require AI for all decisions
            if not self.llm:
                logger.error("AI LLM is not available - cannot make trading decisions without AI")
                raise RuntimeError("AI trading service is unavailable")
            
            decision = await self._get_ai_decision(stock_info, news_items, portfolio_context)
            
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
            raise RuntimeError(f"Failed to complete AI analysis for {stock_info.symbol}: {e}")
    
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
            raise RuntimeError(f"AI decision failed: {e}")
    
    def _analyze_news_sentiment(self, news: NewsItem) -> SentimentEnum:
        """Use AI to analyze news sentiment instead of simple heuristics"""
        if not self.llm:
            logger.warning("LLM not available for sentiment analysis, defaulting to neutral")
            return SentimentEnum.NEUTRAL
        
        try:
            sentiment_prompt = f"""
Analyze the sentiment of this financial news article and classify it as positive, negative, or neutral for stock investors.

Title: {news.title}
Description: {news.description}

Consider:
- Impact on stock prices and market sentiment
- Economic implications
- Business performance indicators
- Market trends and forecasts

Respond with ONLY one word: positive, negative, or neutral
"""
            
            response = self.llm.invoke(sentiment_prompt)
            sentiment_text = response.strip().lower()
            
            logger.info(f"🤖 AI sentiment analysis for '{news.title[:50]}...': {sentiment_text}")
            
            if 'positive' in sentiment_text:
                return SentimentEnum.POSITIVE
            elif 'negative' in sentiment_text:
                return SentimentEnum.NEGATIVE
            else:
                return SentimentEnum.NEUTRAL
                
        except Exception as e:
            logger.error(f"Error in AI sentiment analysis: {e}")
            return SentimentEnum.NEUTRAL
    
    def _create_analysis_prompt(self, 
                               stock_info: StockInfo, 
                               news_items: List[NewsItem],
                               portfolio_context: Dict = None) -> str:
        """Create comprehensive prompt for trading analysis"""
        
        # Format news items with more detail
        news_text = ""
        if news_items:
            news_text += f"Found {len(news_items)} relevant news articles:\n"
            for idx, news in enumerate(news_items[:5], 1):  # Limit to top 5 news items
                news_text += f"{idx}. Title: {news.title}\n"
                news_text += f"   Description: {news.description}\n"
                news_text += f"   Source: {news.source}\n"
                news_text += f"   Published: {news.published_at}\n\n"
        else:
            news_text = "No recent news articles found for this stock.\n"
        
        # Format portfolio context
        portfolio_text = ""
        if portfolio_context:
            portfolio_text = f"""
PORTFOLIO CONTEXT:
- Available Cash: ${portfolio_context.get('cash_balance', 0):,.2f}
- Total Portfolio Value: ${portfolio_context.get('total_value', 0):,.2f}
- Number of Holdings: {len(portfolio_context.get('holdings', []))} positions
- Existing position in {stock_info.symbol}: {portfolio_context.get('current_shares', 0)} shares
"""
        
        prompt = f"""
You are an expert financial analyst specializing in AI-driven trading decisions. Analyze the comprehensive information below and provide a data-driven trading recommendation.

STOCK ANALYSIS TARGET:
Symbol: {stock_info.symbol}
Current Price: ${stock_info.current_price:.2f}
Market Capitalization: {f"${stock_info.market_cap:,.0f}" if stock_info.market_cap else 'Not Available'}
Trading Volume: {f"{stock_info.volume:,.0f}" if stock_info.volume else 'Not Available'}
Daily Price Change: {stock_info.change_percent or 0:.2f}%

NEWS SENTIMENT & MARKET IMPACT:
{news_text}

{portfolio_text}

INSTRUCTIONS:
1. Analyze the stock's current technical indicators and price trends
2. Evaluate the sentiment and impact of recent news on the stock
3. Consider market conditions and volatility
4. Assess risk-reward potential based on available data
5. Make a trading recommendation (BUY, SELL, or HOLD)
6. Suggest a reasonable trade size based on current market conditions and risk assessment
7. Provide confidence level (0.0 to 1.0) based on the strength of your analysis
8. Give detailed reasoning for your decision including key factors that influenced it

IMPORTANT: 
- Base your analysis ONLY on the provided data
- Do not use predetermined rules or percentages
- Consider the news sentiment and its relevance to the stock
- Respond ONLY with valid JSON. Do not include any text before or after the JSON.

JSON format (required):
{{
    "action": "BUY",
    "confidence": 0.75,
    "quantity_percentage": 15.5,
    "reasoning": "Detailed explanation including key factors: technical analysis findings, news impact assessment, market sentiment, and risk considerations"
}}

Make informed decisions based on the data provided. Consider both opportunity and risk in your recommendations.
"""
        return prompt
    
    def _parse_llm_response(self, response: str, stock_info: StockInfo) -> TradeDecision:
        """Parse LLM response into TradeDecision object"""
        logger.info(f"Parsing LLM response: {response[:200]}...")
        
        try:
            # Log the raw AI response for debugging
            logger.info(f"🤖 Raw AI Response for {stock_info.symbol}:")
            logger.info(f"Response length: {len(response)} characters")
            logger.info(f"First 200 chars: {response[:200]}")
            
            # Try to extract JSON from response - handle multiple JSON objects
            start_idx = response.find('{')
            
            if start_idx == -1:
                logger.error("No JSON object found in AI response")
                raise ValueError("AI response does not contain valid JSON")
            
            # Find the end of the first complete JSON object
            brace_count = 0
            end_idx = -1
            
            for i in range(start_idx, len(response)):
                if response[i] == '{':
                    brace_count += 1
                elif response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if end_idx == -1:
                logger.error("No complete JSON object found in AI response")
                raise ValueError("AI response contains incomplete JSON")
            
            json_str = response[start_idx:end_idx].strip()
            logger.info(f"📝 Extracted JSON: {json_str}")
            
            # Try to parse the JSON
            try:
                data = json.loads(json_str)
                logger.info(f"✅ Successfully parsed JSON: {data}")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Initial JSON parse failed: {e}")
                
                # Try to fix common JSON issues
                import re
                
                # Remove trailing commas
                fixed_json = re.sub(r',\s*}', '}', json_str)
                fixed_json = re.sub(r',\s*]', ']', fixed_json)
                
                # Fix quotes issues
                fixed_json = re.sub(r'(?<!\\)"([^"]*)"(?=\s*[,}])', r'"\1"', fixed_json)
                
                logger.info(f"🔧 Attempting to parse fixed JSON: {fixed_json}")
                
                try:
                    data = json.loads(fixed_json)
                    logger.info(f"✅ Successfully parsed fixed JSON: {data}")
                except json.JSONDecodeError as e2:
                    logger.error(f"❌ JSON parse failed even after cleanup: {e2}")
                    logger.error(f"Problematic JSON: {fixed_json}")
                    raise ValueError(f"Failed to parse AI response as JSON. Original error: {e}, Fixed error: {e2}")
            
            # Validate and extract data with defaults
            action_str = data.get('action', 'hold').lower().strip()
            if action_str not in ['buy', 'sell', 'hold']:
                logger.warning(f"Invalid action '{action_str}', defaulting to 'hold'")
                action_str = 'hold'
            
            action = TradeAction(action_str)
            confidence = max(0.0, min(1.0, float(data.get('confidence', 0.5))))
            quantity_percentage = max(1.0, min(50.0, float(data.get('quantity_percentage', 5))))
            reasoning = str(data.get('reasoning', 'AI analysis completed'))[:500]  # Limit reasoning length
            
            logger.info(f"🎯 AI Decision for {stock_info.symbol}: {action.value.upper()} (confidence: {confidence:.1%}, quantity: {quantity_percentage}%)")
            logger.info(f"💭 AI Reasoning: {reasoning[:100]}...")
            
            # Calculate actual quantity based on percentage
            # For simplicity, assume $10,000 position size for BUY orders
            if action == TradeAction.BUY:
                position_size = 10000 * (quantity_percentage / 100)
                quantity = max(1, int(position_size / stock_info.current_price))
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
            raise RuntimeError(f"Failed to parse AI response: {e}")
    
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
