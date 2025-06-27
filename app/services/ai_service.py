from langchain_ibm import WatsonxLLM
from langchain.schema import SystemMessage, HumanMessage
from typing import List, Dict
from models import NewsItem, StockInfo, TradeDecision, TradeAction
from config import settings
import json
import logging

logger = logging.getLogger(__name__)

class AITradingService:
    def __init__(self):
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize IBM Watsonx LLM"""
        try:
            return WatsonxLLM(
                model_id=settings.IBM_BASE_MODEL,
                url=settings.IBM_BASE_URL,
                apikey=settings.IBM_API_KEY,
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
        
        if not self.llm:
            # Fallback decision if LLM is not available
            return self._fallback_decision(stock_info)
        
        try:
            prompt = self._create_analysis_prompt(stock_info, news_items, portfolio_context)
            response = self.llm.invoke(prompt)
            
            # Parse the response to extract trading decision
            decision = self._parse_llm_response(response, stock_info)
            return decision
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return self._fallback_decision(stock_info)
    
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
        """Fallback decision when AI is not available"""
        # Simple rule-based decision
        if stock_info.change_percent and stock_info.change_percent > 2:
            action = TradeAction.BUY
            reasoning = "Stock showing strong positive momentum (>2% gain)"
        elif stock_info.change_percent and stock_info.change_percent < -3:
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
