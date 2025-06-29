from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

import json
import asyncio
from datetime import datetime

# Initialize database
try:
    from database import create_tables, init_portfolio
    create_tables()
    init_portfolio()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️  Database initialization failed: {e}")
    print("Continuing with file-based storage...")

app = FastAPI(title="AI Trading Agent", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",  # Alternative localhost
        "http://localhost:3000",  # Alternative dev server
        "http://127.0.0.1:3000",  # Alternative dev server
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Import routers
from routers import trading, news, portfolio, analytics, automated_trading, onboarding, company_search

# Import WebSocket support
from fastapi import WebSocket, WebSocketDisconnect
from services.websocket_manager import manager, trading_ws_manager
from services.company_search_service import company_search_service

app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(automated_trading.router, prefix="/api/automated-trading", tags=["automated-trading"])
app.include_router(company_search.router, prefix="/api/companies", tags=["company-search"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["onboarding"])

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Main WebSocket endpoint for real-time updates"""
    connection_id = None
    try:
        connection_id = await manager.connect(websocket, client_id)
        print(f"✅ WebSocket client connected: {connection_id}")
        
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                # Handle subscription requests
                if message.get("type") == "subscribe":
                    topics = message.get("topics", [])
                    await manager.subscribe(connection_id, topics)
                    await manager.send_personal_message(
                        json.dumps({"type": "subscription_confirmed", "topics": topics}),
                        connection_id
                    )
                
                # Handle unsubscription requests
                elif message.get("type") == "unsubscribe":
                    topics = message.get("topics", [])
                    await manager.unsubscribe(connection_id, topics)
                    await manager.send_personal_message(
                        json.dumps({"type": "unsubscription_confirmed", "topics": topics}),
                        connection_id
                    )
                
                # Handle ping/pong for connection health
                elif message.get("type") == "ping":
                    await manager.send_personal_message(
                        json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                        connection_id
                    )
                
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Invalid JSON format"}),
                    connection_id
                )
                
    except WebSocketDisconnect:
        print(f"🔌 WebSocket client disconnected: {client_id}")
        if connection_id:
            manager.disconnect(connection_id)
    except Exception as e:
        print(f"❌ WebSocket error for client {client_id}: {e}")
        import traceback
        traceback.print_exc()
        if connection_id:
            manager.disconnect(connection_id)
        try:
            await websocket.close(code=1000)
        except:
            pass

# Company search endpoint
@app.get("/api/companies/search")
async def search_companies(q: str, limit: int = 10):
    """Search for companies by name or symbol"""
    try:
        results = await company_search_service.search_companies(q, limit)
        return {"companies": results, "query": q, "total": len(results)}
    except Exception as e:
        return {"error": str(e), "companies": [], "query": q, "total": 0}

@app.get("/api/companies/{symbol}")
async def get_company_details(symbol: str):
    """Get detailed company information"""
    try:
        details = await company_search_service.get_company_details(symbol)
        if details:
            return details
        else:
            return {"error": "Company not found", "symbol": symbol}
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

@app.get("/")
async def root():
    return {"message": "AI Trading Agent API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
