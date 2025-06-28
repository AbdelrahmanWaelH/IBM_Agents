from langchain_ibm import WatsonxLLM
from langchain.schema import SystemMessage, HumanMessage
from typing import List, Dict, Optional
from models import NewsItem, StockInfo, TradeDecision, TradeAction
from config import settings
import json
import logging
import yfinance as yf
import time
import re
from database import SessionLocal, AIDecision, NewsAnalysis, StockAnalysis, SentimentEnum, TradeActionEnum
from datetime import datetime

logger = logging.getLogger(__name__)

class AITradingService:
    def __init__(self):
        self.llm = self._initialize_llm()
        self.db = SessionLocal()
        self.company_cache = {}
        self.cache_duration = 3600  # Cache company info for 1 hour
        
    def _get_company_info(self, symbol: str) -> Optional[Dict[str, str]]:
        """Dynamically get company information using yfinance"""
        symbol = symbol.upper().strip()
        current_time = time.time()
        
        # Check cache first
        if symbol in self.company_cache:
            cached_data = self.company_cache[symbol]
            if current_time - cached_data['timestamp'] < self.cache_duration:
                return cached_data['info']
        
        try:
            logger.info(f"Fetching company info for AI analysis: {symbol}")
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if info and isinstance(info, dict):
                company_info = {
                    'longName': info.get('longName', ''),
                    'shortName': info.get('shortName', ''),
                    'longBusinessSummary': info.get('longBusinessSummary', ''),
                    'sector': info.get('sector', ''),
                    'industry': info.get('industry', '')
                }
                
                # Cache the result
                self.company_cache[symbol] = {
                    'info': company_info,
                    'timestamp': current_time
                }
                
                logger.info(f"✅ Retrieved company info for AI: {symbol} -> {company_info.get('longName', 'N/A')}")
                return company_info
            else:
                logger.warning(f"No company info available for AI analysis: {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching company info for AI analysis: {symbol}: {e}")
            return None
    
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
        """Create comprehensive prompt for trading analysis with dynamic company info"""
        
        # Get dynamic company information
        company_info = self._get_company_info(stock_info.symbol)
        
        # Determine company name and context
        if company_info and company_info.get('longName'):
            company_name = company_info['longName']
            company_context = f"""
COMPANY INFORMATION:
Full Name: {company_info.get('longName', 'N/A')}
Short Name: {company_info.get('shortName', 'N/A')}
Sector: {company_info.get('sector', 'N/A')}
Industry: {company_info.get('industry', 'N/A')}
Business Summary: {company_info.get('longBusinessSummary', 'N/A')[:300]}...
"""
        else:
            company_name = stock_info.symbol
            company_context = f"Limited company information available for {stock_info.symbol}."
        
        # Format news items with more detail
        news_text = ""
        if news_items:
            news_text += f"**RECENT NEWS ANALYSIS** - Found {len(news_items)} relevant articles:\n"
            for idx, news in enumerate(news_items[:5], 1):  # Limit to top 5 news items
                news_text += f"{idx}. **{news.title}**\n"
                news_text += f"   Summary: {news.description}\n"
                news_text += f"   Source: {news.source} | Published: {news.published_at}\n"
                news_text += f"   Analysis Impact: Consider how this news affects investor sentiment and stock performance\n\n"
        else:
            news_text = "**NO RECENT NEWS AVAILABLE** - Analysis based on stock data only. This limits prediction accuracy.\n"
        
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

{company_context}

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
1. Analyze {company_name}'s current technical indicators and price trends
2. **CRITICAL**: Thoroughly evaluate the sentiment and impact of recent news on {company_name} - this is essential for trading decisions
3. Consider market conditions and volatility affecting {company_name}
4. Assess risk-reward potential based on available data and company fundamentals
5. Make a trading recommendation (BUY, SELL, or HOLD)
6. Suggest a reasonable trade size based on current market conditions and risk assessment
7. Provide confidence level (0.0 to 1.0) based on the strength of your analysis
8. Give detailed reasoning for your decision including key factors that influenced it

IMPORTANT: 
- Base your analysis ONLY on the provided data
- **NEWS ANALYSIS IS CRITICAL**: Pay special attention to news sentiment and its direct impact on stock performance
- Do not use predetermined rules or percentages
- Consider the news sentiment and its relevance to the stock price movement
- Factor in company fundamentals, sector trends, and market conditions
- If no news is available, note this limitation in your reasoning
- Respond ONLY with valid JSON. Do not include any text before or after the JSON.

JSON format (required):
{{
    "action": "BUY",
    "confidence": 0.75,
    "quantity_percentage": 15.5,
    "reasoning": "Detailed explanation including key factors: technical analysis findings, news impact assessment, market sentiment, company fundamentals, and risk considerations"
}}

Make informed decisions based on the data provided. Consider both opportunity and risk in your recommendations.
"""
        return prompt
    
    def _parse_llm_response(self, response: str, stock_info: StockInfo) -> TradeDecision:
        """Parse LLM response into TradeDecision object with robust error handling"""
        logger.info(f"Parsing LLM response: {response[:200]}...")
        
        try:
            # Log the raw AI response for debugging
            logger.info(f"🤖 Raw AI Response for {stock_info.symbol}:")
            logger.info(f"Response length: {len(response)} characters")
            logger.info(f"First 200 chars: {response[:200]}")
            
            # Clean the response first to handle control characters
            cleaned_response = self._clean_json_response(response)
            
            # Try to extract JSON from cleaned response
            start_idx = cleaned_response.find('{')
            
            if start_idx == -1:
                logger.error("No JSON object found in AI response")
                raise ValueError("AI response does not contain valid JSON")
            
            # Find the end of the first complete JSON object
            brace_count = 0
            end_idx = -1
            
            for i in range(start_idx, len(cleaned_response)):
                if cleaned_response[i] == '{':
                    brace_count += 1
                elif cleaned_response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if end_idx == -1:
                logger.error("No complete JSON object found in AI response")
                raise ValueError("AI response contains incomplete JSON")
            
            json_str = cleaned_response[start_idx:end_idx].strip()
            logger.info(f"📝 Extracted JSON: {json_str[:200]}...")
            
            # Try to parse the JSON
            try:
                data = json.loads(json_str)
                logger.info(f"✅ Successfully parsed JSON")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Initial JSON parse failed: {e}")
                logger.warning(f"Problematic character at position {e.pos}: '{json_str[max(0, e.pos-5):e.pos+5]}'")
                
                # Try more aggressive cleanup for JSON issues
                fixed_json = self._fix_json_string(json_str)
                
                logger.info(f"🔧 Attempting to parse fixed JSON...")
                
                try:
                    data = json.loads(fixed_json)
                    logger.info(f"✅ Successfully parsed fixed JSON")
                except json.JSONDecodeError as e2:
                    logger.error(f"❌ JSON parse failed even after cleanup: {e2}")
                    logger.error(f"Problematic JSON first 500 chars: {fixed_json[:500]}")
                    
                    # Additional debugging - show character codes around error
                    if e2.pos < len(fixed_json):
                        error_context = fixed_json[max(0, e2.pos-10):e2.pos+10]
                        logger.error(f"Character codes around error: {char_codes}")
                    
                    # Fallback: try to extract values manually using regex
                    logger.warning("🚨 Attempting manual value extraction as fallback")
                    data = self._extract_values_manually(cleaned_response)
            
            # Validate and extract data with defaults
            action_str = data.get('action', 'hold').lower().strip()
            if action_str not in ['buy', 'sell', 'hold']:
                logger.warning(f"Invalid action '{action_str}', defaulting to 'hold'")
                action_str = 'hold'
            
            action = TradeAction(action_str)
            confidence = max(0.0, min(1.0, float(data.get('confidence', 0.5))))
            quantity_percentage = max(1.0, min(50.0, float(data.get('quantity_percentage', 5))))
            reasoning = str(data.get('reasoning', 'AI analysis completed'))[:1000]  # Limit length
            
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
    
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response by removing control characters and fixing common issues"""
        try:
            # AGGRESSIVE CONTROL CHARACTER REMOVAL
            # Remove ALL control characters (0-31) except space (32), newline (10), tab (9), and carriage return (13)
            cleaned = ''.join(char for char in response if ord(char) >= 32 or char in '\n\t\r')
            
            # Additional control character cleanup - remove common problematic Unicode characters
            # Remove zero-width characters, non-breaking spaces, etc.
            cleaned = re.sub(r'[\u0000-\u001F\u007F-\u009F\u00AD\u200B-\u200F\u2028-\u202F\u205F-\u206F\uFEFF]', '', cleaned)
            
            # Remove common prefixes/suffixes that might interfere
            cleaned = cleaned.strip()
            
            # Remove any markdown code block markers
            cleaned = re.sub(r'```json\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            
            # Remove any extra text before the first {
            first_brace = cleaned.find('{')
            if first_brace > 0:
                cleaned = cleaned[first_brace:]
            
            # Remove any extra text after the last }
            last_brace = cleaned.rfind('}')
            if last_brace != -1:
                cleaned = cleaned[:last_brace + 1]
            
            # Clean up any remaining whitespace issues
            cleaned = re.sub(r'\s+', ' ', cleaned)  # Replace multiple whitespace with single space
            cleaned = re.sub(r'\s*,\s*', ',', cleaned)  # Clean comma spacing
            cleaned = re.sub(r'\s*:\s*', ':', cleaned)  # Clean colon spacing
            cleaned = re.sub(r'\s*{\s*', '{', cleaned)  # Clean brace spacing
            cleaned = re.sub(r'\s*}\s*', '}', cleaned)  # Clean brace spacing
            
            logger.info(f"🧹 Aggressively cleaned JSON response (length: {len(cleaned)})")
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning JSON response: {e}")
            return response
    
    def _fix_json_string(self, json_str: str) -> str:
        """Attempt to fix common JSON issues including type corrections"""
        try:
            # Fix escaped quotes that might be causing issues
            fixed = json_str.replace('\\"', '"')
            
            # Fix trailing commas
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            # CRITICAL FIX: Convert string numbers to actual numbers
            # Fix confidence values that are strings
            fixed = re.sub(r'"confidence":\s*"([0-9.]+)"', r'"confidence": \1', fixed)
            
            # Fix quantity_percentage values that are strings
            fixed = re.sub(r'"quantity_percentage":\s*"([0-9.]+)"', r'"quantity_percentage": \1', fixed)
            
            # Fix other numeric values that might be strings
            fixed = re.sub(r'"(\w+)":\s*"([0-9.]+)"', r'"\1": \2', fixed)
            
            # Fix action values to ensure they're proper strings
            fixed = re.sub(r'"action":\s*([A-Z]+)', r'"action": "\1"', fixed)
            
            # Ensure proper string quoting for non-numeric values
            # This regex is more careful to avoid breaking already-quoted strings
            fixed = re.sub(r':\s*([^",{\[}\]\s\d][^,}]*?)(?=\s*[,}])', r': "\1"', fixed)
            
            logger.info(f"🔧 Fixed JSON string with type corrections")
            return fixed
            
        except Exception as e:
            logger.error(f"Error fixing JSON string: {e}")
            return json_str
    
    def _extract_values_manually(self, response: str) -> Dict:
        """Manual extraction of values from AI response as fallback"""
        try:
            logger.warning("🚨 Using manual value extraction - AI response was not valid JSON")
            
            data = {
                'action': 'hold',
                'confidence': 0.5,
                'quantity_percentage': 5.0,
                'reasoning': 'AI analysis completed with manual parsing fallback'
            }
            
            # Try to extract action (look for common patterns)
            action_patterns = [
                r'"action":\s*"([^"]*)"',
                r'"action":\s*([A-Z]+)',
                r'action.*?([A-Z]{3,4})',  # BUY, SELL, HOLD
            ]
            
            for pattern in action_patterns:
                action_match = re.search(pattern, response, re.IGNORECASE)
                if action_match:
                    action = action_match.group(1).lower().strip()
                    if action in ['buy', 'sell', 'hold']:
                        data['action'] = action
                        break
            
            # Try to extract confidence (handle both string and numeric formats)
            confidence_patterns = [
                r'"confidence":\s*"([0-9.]+)"',
                r'"confidence":\s*([0-9.]+)',
                r'confidence.*?([0-9.]+)',
            ]
            
            for pattern in confidence_patterns:
                confidence_match = re.search(pattern, response, re.IGNORECASE)
                if confidence_match:
                    try:
                        confidence = float(confidence_match.group(1))
                        data['confidence'] = max(0.0, min(1.0, confidence))
                        break
                    except ValueError:
                        continue
            
            # Try to extract quantity_percentage (handle both string and numeric formats)
            quantity_patterns = [
                r'"quantity_percentage":\s*"([0-9.]+)"',
                r'"quantity_percentage":\s*([0-9.]+)',
                r'quantity_percentage.*?([0-9.]+)',
            ]
            
            for pattern in quantity_patterns:
                quantity_match = re.search(pattern, response, re.IGNORECASE)
                if quantity_match:
                    try:
                        quantity = float(quantity_match.group(1))
                        data['quantity_percentage'] = max(1.0, min(50.0, quantity))
                        break
                    except ValueError:
                        continue
            
            # Try to extract reasoning (handle multiline strings)
            reasoning_patterns = [
                r'"reasoning":\s*"([^"]*)"',
                r'"reasoning":\s*"([^"]*?)(?=")',  # Non-greedy until next quote
                r'"reasoning":\s*"(.*?)"',  # Greedy version
            ]
            
            for pattern in reasoning_patterns:
                reasoning_match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if reasoning_match:
                    reasoning = reasoning_match.group(1)
                    if reasoning and len(reasoning.strip()) > 10:  # Only use if meaningful
                        data['reasoning'] = reasoning[:1000]  # Limit length
                        break
            
            logger.info(f"🔍 Manually extracted values: action={data['action']}, confidence={data['confidence']}, quantity={data['quantity_percentage']}%")
            return data
            
        except Exception as e:
            logger.error(f"Error in manual value extraction: {e}")
            return {
                'action': 'hold',
                'confidence': 0.5,
                'quantity_percentage': 5.0,
                'reasoning': 'Default values due to parsing error'
            }
    
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
    
    async def get_chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """Get chat completion for onboarding conversation with fallback support"""
        try:
            # Check if LLM is available
            if not self.llm:
                logger.warning("LLM not available, using fallback chat system")
                return self._get_fallback_chat_response(messages)
            
            # Convert messages to a more structured prompt to prevent conversation continuation
            prompt_parts = []
            
            # Add system message
            for msg in messages:
                if msg["role"] == "system":
                    prompt_parts.append(f"INSTRUCTIONS: {msg['content']}")
                    break
            
            # Add conversation history in a structured way
            conversation_history = []
            current_user_message = ""
            
            for msg in messages:
                if msg["role"] == "user":
                    current_user_message = msg['content']
                    conversation_history.append(f"User said: {msg['content']}")
                elif msg["role"] == "assistant":
                    conversation_history.append(f"You responded: {msg['content']}")
            
            if conversation_history:
                prompt_parts.append("CONVERSATION SO FAR:")
                prompt_parts.extend(conversation_history)
            
            prompt_parts.append(f"USER'S CURRENT MESSAGE: {current_user_message}")
            prompt_parts.append("YOUR RESPONSE (respond only as the assistant, do not continue the conversation):")
            
            final_prompt = "\n\n".join(prompt_parts)
            
            # Try to get response from LLM with timeout
            try:
                logger.info("Attempting LLM chat completion...")
                response = self.llm.invoke(final_prompt)
                
                if not response or not response.strip():
                    logger.warning("LLM returned empty response, using fallback")
                    return self._get_fallback_chat_response(messages)
                
                # Clean up the response to prevent conversation continuation
                cleaned_response = self._clean_chat_response(response.strip())
                
                logger.info(f"LLM chat completion successful: {cleaned_response[:100]}...")
                return cleaned_response
                
            except Exception as llm_error:
                logger.error(f"LLM invocation failed: {llm_error}")
                logger.warning("Falling back to rule-based chat system")
                return self._get_fallback_chat_response(messages)
            
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            return self._get_fallback_chat_response(messages)
    
    def _get_fallback_chat_response(self, messages: List[Dict[str, str]]) -> str:
        """Fallback chat system when LLM is not available"""
        try:
            # Get the last user message
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            last_message = user_messages[-1]["content"].lower() if user_messages else ""
            
            # Count total questions asked
            total_questions = len(user_messages)
            
            # Rule-based responses for onboarding
            if total_questions == 0 or "hi" in last_message or "hello" in last_message:
                return ("Hello! I'm your AI investment advisor. I'm here to help you set up your investment "
                       "preferences so we can provide personalized recommendations. Let's start by getting to "
                       "know your investment experience. Are you new to investing, or do you have some experience "
                       "with stocks and trading?")
            
            elif total_questions == 1:
                if any(word in last_message for word in ["new", "beginner", "first time", "never"]):
                    return ("Great! It's exciting to start your investment journey. Since you're new to investing, "
                           "let's take it step by step. First, let's talk about risk tolerance. How do you feel "
                           "about market fluctuations? Would you prefer: 1) Conservative approach with lower risk "
                           "and steady returns, 2) Moderate approach with balanced risk and growth potential, or "
                           "3) Aggressive approach with higher risk for potentially higher returns?")
                else:
                    return ("Excellent! Having some investment experience will help us tailor better recommendations. "
                           "Now let's discuss your risk tolerance. Given your experience, how comfortable are you "
                           "with market volatility? Would you describe yourself as: 1) Conservative (prefer stability), "
                           "2) Moderate (balanced approach), or 3) Aggressive (comfortable with higher risk)?")
            
            elif total_questions == 2:
                return ("Thank you for sharing your risk tolerance! Now let's talk about your investment goals. "
                       "What are you primarily looking to achieve with your investments? You can choose multiple: "
                       "1) Growth (capital appreciation over time), 2) Income (regular dividends), "
                       "3) Stability (preserve capital), or 4) Speculation (high-risk, high-reward opportunities)?")
            
            elif total_questions == 3:
                return ("Perfect! Understanding your goals helps me recommend the right strategies. Now, what's your "
                       "investment time horizon? Are you investing for: 1) Short-term goals (less than 1 year), "
                       "2) Medium-term goals (1-5 years), or 3) Long-term goals (more than 5 years)?")
            
            elif total_questions == 4:
                return ("Excellent! Time horizon is crucial for investment strategy. Now let's discuss sectors. "
                       "Are there any particular industries or sectors you're interested in? For example: "
                       "Technology, Healthcare, Finance, Energy, Consumer goods, Real estate, or would you "
                       "prefer a diversified approach across multiple sectors?")
            
            elif total_questions == 5:
                return ("Great choices! Now let's talk about your budget. What's your approximate investment "
                       "budget range? 1) Small (under $10,000), 2) Medium ($10,000 - $100,000), or "
                       "3) Large (over $100,000)? This helps me suggest appropriate position sizes.")
            
            elif total_questions == 6:
                return ("Perfect! Finally, let's discuss automation. Would you like our AI to: "
                       "1) Provide analysis only (you make all trading decisions), "
                       "2) Provide analysis and execute trades with your approval, or "
                       "3) Handle trading automatically based on AI recommendations?")
            
            elif total_questions >= 7:
                return ("Thank you for providing all that information! Based on our conversation, I've gathered "
                       "your investment preferences. I'll now create your personalized investment profile to "
                       "provide you with tailored recommendations. You can always update these preferences later. "
                       "ONBOARDING_COMPLETE")
            
            else:
                return ("I understand. Could you tell me more about your investment preferences? "
                       "This will help me provide better recommendations for you.")
                
        except Exception as e:
            logger.error(f"Error in fallback chat: {e}")
            return ("Thank you for your input! Let's continue with your investment preferences setup. "
                   "What aspects of investing are most important to you?")

    def _clean_chat_response(self, response: str) -> str:
        """Clean the chat response to prevent conversation continuation"""
        # Split by common conversation markers and take only the first part
        stop_patterns = [
            "\n\nUser:",
            "\nUser:",
            "\n\nAssistant:",
            "\nAssistant:",
            "User said:",
            "User:"
        ]
        
        cleaned = response
        for pattern in stop_patterns:
            if pattern in cleaned:
                cleaned = cleaned.split(pattern)[0]
        
        # Remove any trailing colons or conversation markers
        cleaned = cleaned.rstrip(": \n")
        
        return cleaned.strip()

    def __del__(self):
        """Close database connection"""
        if hasattr(self, 'db'):
            self.db.close()

# Alias for consistency with onboarding router
AIService = AITradingService
