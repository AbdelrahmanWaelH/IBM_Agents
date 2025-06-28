from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from services.ai_service import AIService
from database import get_db, UserPreferences
from sqlalchemy.orm import Session
import json

router = APIRouter()

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    response: str
    is_complete: bool = False
    preferences: Optional[dict] = None

class OnboardingPreferences(BaseModel):
    risk_tolerance: str  # "conservative", "moderate", "aggressive"
    investment_goals: List[str]  # ["growth", "income", "stability", "speculation"]
    time_horizon: str  # "short", "medium", "long"
    sectors_of_interest: List[str]
    budget_range: str  # "small", "medium", "large"
    experience_level: str  # "beginner", "intermediate", "advanced"
    automated_trading_preference: str  # "none", "analysis_only", "full_control"

ONBOARDING_SYSTEM_PROMPT = """
You are an AI financial advisor helping new users set up their investment preferences. Your goal is to understand their:

1. Risk tolerance (conservative, moderate, aggressive)
2. Investment goals (growth, income, stability, speculation)
3. Time horizon (short-term: <1 year, medium-term: 1-5 years, long-term: >5 years)
4. Sectors of interest (technology, healthcare, finance, energy, etc.)
5. Budget range (small: <$10k, medium: $10k-$100k, large: >$100k)
6. Experience level (beginner, intermediate, advanced)
7. Automated trading preference (none, analysis only, full control)

IMPORTANT INSTRUCTIONS:
- Ask questions one at a time to make the conversation natural and engaging
- Be friendly, professional, and educational
- Use simple and concise English without technical jargon
- Only respond as the Assistant, do not simulate user responses
- Do not continue conversations or role-play multiple turns
- Give ONE response to the user's question/statement
- When you have gathered all 7 pieces of information, respond with "ONBOARDING_COMPLETE" at the end
- When given a message from the user that is not within the scope of investing or their preferences, you should ask them politely to stay on topic. You can say "We are here to discuss investments, please remain on topic". 


If this is the first interaction, start by greeting the user and asking about their investment experience level.
"""

@router.post("/chat", response_model=ChatResponse)
async def chat_with_onboarding_agent(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    ai_service = None
    try:
        # Initialize AI service
        ai_service = AIService()
        
        # Build conversation context
        messages = [{"role": "system", "content": ONBOARDING_SYSTEM_PROMPT}]
        
        # Add conversation history
        for msg in request.conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current user message
        messages.append({"role": "user", "content": request.message})
        
        # Get AI response
        response = await ai_service.get_chat_completion(messages)
        
        # Check if onboarding is complete
        is_complete = "ONBOARDING_COMPLETE" in response
        preferences = None
        
        if is_complete:
            # Extract preferences from conversation history
            preferences = extract_preferences_from_conversation(request.conversation_history + [ChatMessage(role="user", content=request.message)])
            response = response.replace("ONBOARDING_COMPLETE", "").strip()
        
        return ChatResponse(
            response=response,
            is_complete=is_complete,
            preferences=preferences
        )
        
    except Exception as e:
        error_msg = f"Error in onboarding chat: {str(e)}"
        print(f"Chat error details: {error_msg}")  # Debug logging
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        # Clean up AI service if needed
        if ai_service and hasattr(ai_service, 'db'):
            try:
                ai_service.db.close()
            except:
                pass

@router.post("/save-preferences")
async def save_user_preferences(
    preferences: OnboardingPreferences,
    db: Session = Depends(get_db)
):
    try:
        # Save or update user preferences in database
        user_prefs = db.query(UserPreferences).filter(UserPreferences.user_id == 1).first()
        
        if user_prefs:
            # Update existing preferences
            user_prefs.risk_tolerance = preferences.risk_tolerance
            user_prefs.investment_goals = json.dumps(preferences.investment_goals)
            user_prefs.time_horizon = preferences.time_horizon
            user_prefs.sectors_of_interest = json.dumps(preferences.sectors_of_interest)
            user_prefs.budget_range = preferences.budget_range
            user_prefs.experience_level = preferences.experience_level
            user_prefs.automated_trading_preference = preferences.automated_trading_preference
        else:
            # Create new preferences
            user_prefs = UserPreferences(
                user_id=1,  # Default user
                risk_tolerance=preferences.risk_tolerance,
                investment_goals=json.dumps(preferences.investment_goals),
                time_horizon=preferences.time_horizon,
                sectors_of_interest=json.dumps(preferences.sectors_of_interest),
                budget_range=preferences.budget_range,
                experience_level=preferences.experience_level,
                automated_trading_preference=preferences.automated_trading_preference
            )
            db.add(user_prefs)
        
        db.commit()
        return {"message": "Preferences saved successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving preferences: {str(e)}")

@router.get("/preferences")
async def get_user_preferences(db: Session = Depends(get_db)):
    try:
        user_prefs = db.query(UserPreferences).filter(UserPreferences.user_id == 1).first()
        
        if not user_prefs:
            return None
            
        return OnboardingPreferences(
            risk_tolerance=user_prefs.risk_tolerance,
            investment_goals=json.loads(user_prefs.investment_goals or "[]"),
            time_horizon=user_prefs.time_horizon,
            sectors_of_interest=json.loads(user_prefs.sectors_of_interest or "[]"),
            budget_range=user_prefs.budget_range,
            experience_level=user_prefs.experience_level,
            automated_trading_preference=user_prefs.automated_trading_preference
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching preferences: {str(e)}")

def extract_preferences_from_conversation(messages: List[ChatMessage]) -> dict:
    """Extract user preferences from conversation history using keyword matching"""
    conversation_text = " ".join([msg.content.lower() for msg in messages if msg.role == "user"])
    
    preferences = {}
    
    # Risk tolerance
    if any(word in conversation_text for word in ["conservative", "safe", "low risk", "careful"]):
        preferences["risk_tolerance"] = "conservative"
    elif any(word in conversation_text for word in ["aggressive", "high risk", "risky", "bold"]):
        preferences["risk_tolerance"] = "aggressive"
    else:
        preferences["risk_tolerance"] = "moderate"
    
    # Investment goals
    goals = []
    if any(word in conversation_text for word in ["growth", "grow", "appreciate", "increase"]):
        goals.append("growth")
    if any(word in conversation_text for word in ["income", "dividend", "yield", "monthly", "quarterly"]):
        goals.append("income")
    if any(word in conversation_text for word in ["stable", "stability", "steady", "consistent"]):
        goals.append("stability")
    if any(word in conversation_text for word in ["speculative", "speculation", "gamble", "risky bets"]):
        goals.append("speculation")
    preferences["investment_goals"] = goals if goals else ["growth"]
    
    # Time horizon
    if any(word in conversation_text for word in ["short", "few months", "this year", "quickly"]):
        preferences["time_horizon"] = "short"
    elif any(word in conversation_text for word in ["long", "years", "decade", "retirement", "long-term"]):
        preferences["time_horizon"] = "long"
    else:
        preferences["time_horizon"] = "medium"
    
    # Experience level
    if any(word in conversation_text for word in ["beginner", "new", "first time", "never", "learning"]):
        preferences["experience_level"] = "beginner"
    elif any(word in conversation_text for word in ["advanced", "experienced", "expert", "professional"]):
        preferences["experience_level"] = "advanced"
    else:
        preferences["experience_level"] = "intermediate"
    
    # Budget range
    if any(word in conversation_text for word in ["small", "little", "few thousand", "under 10"]):
        preferences["budget_range"] = "small"
    elif any(word in conversation_text for word in ["large", "significant", "over 100", "substantial"]):
        preferences["budget_range"] = "large"
    else:
        preferences["budget_range"] = "medium"
    
    # Sectors (basic keyword matching)
    sectors = []
    sector_keywords = {
        "technology": ["tech", "technology", "software", "ai", "artificial intelligence"],
        "healthcare": ["healthcare", "medical", "pharma", "biotech"],
        "finance": ["finance", "banking", "fintech", "financial"],
        "energy": ["energy", "oil", "renewable", "solar", "wind"],
        "consumer": ["consumer", "retail", "shopping", "brands"],
        "real_estate": ["real estate", "property", "reit"]
    }
    
    for sector, keywords in sector_keywords.items():
        if any(keyword in conversation_text for keyword in keywords):
            sectors.append(sector)
    
    preferences["sectors_of_interest"] = sectors if sectors else ["technology"]
    
    # Automated trading preference
    if any(word in conversation_text for word in ["no automation", "manual", "myself", "no auto"]):
        preferences["automated_trading_preference"] = "none"
    elif any(word in conversation_text for word in ["full control", "automatic", "auto trading", "let ai"]):
        preferences["automated_trading_preference"] = "full_control"
    else:
        preferences["automated_trading_preference"] = "analysis_only"
    
    return preferences