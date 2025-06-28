"""
WebSocket Manager for Real-time Trading Updates
Provides real-time updates for portfolio, trades, and AI decisions
"""

import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_topics: Dict[str, Set[str]] = {}  # connection_id -> topics
        
    async def connect(self, websocket: WebSocket, connection_id: str = None) -> str:
        """Connect a new WebSocket client"""
        if connection_id is None:
            connection_id = str(uuid.uuid4())
        
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_topics[connection_id] = set()
        
        logger.info(f"WebSocket client connected: {connection_id}")
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Disconnect a WebSocket client"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_topics:
            del self.connection_topics[connection_id]
        
        logger.info(f"WebSocket client disconnected: {connection_id}")
    
    async def subscribe(self, connection_id: str, topics: List[str]):
        """Subscribe a connection to specific topics"""
        if connection_id in self.connection_topics:
            self.connection_topics[connection_id].update(topics)
            logger.info(f"Client {connection_id} subscribed to: {topics}")
    
    async def unsubscribe(self, connection_id: str, topics: List[str]):
        """Unsubscribe a connection from specific topics"""
        if connection_id in self.connection_topics:
            self.connection_topics[connection_id] -= set(topics)
            logger.info(f"Client {connection_id} unsubscribed from: {topics}")
    
    async def send_personal_message(self, message: str, connection_id: str):
        """Send a message to a specific connection"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast_to_topic(self, topic: str, message: Dict):
        """Broadcast a message to all connections subscribed to a topic"""
        message_data = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "data": message
        }
        
        message_text = json.dumps(message_data)
        disconnected_clients = []
        
        for connection_id, topics in self.connection_topics.items():
            if topic in topics:
                try:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_text(message_text)
                except Exception as e:
                    logger.error(f"Error broadcasting to {connection_id}: {e}")
                    disconnected_clients.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected_clients:
            self.disconnect(connection_id)
    
    async def broadcast_to_all(self, message: Dict):
        """Broadcast a message to all active connections"""
        message_data = {
            "topic": "broadcast",
            "timestamp": datetime.now().isoformat(),
            "data": message
        }
        
        message_text = json.dumps(message_data)
        disconnected_clients = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
                disconnected_clients.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected_clients:
            self.disconnect(connection_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def get_topic_subscribers(self, topic: str) -> int:
        """Get the number of subscribers for a topic"""
        count = 0
        for topics in self.connection_topics.values():
            if topic in topics:
                count += 1
        return count

# Global connection manager
manager = ConnectionManager()

class TradingWebSocketManager:
    """High-level WebSocket manager for trading-specific events"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
    
    async def notify_ai_decision(self, decision_data: Dict):
        """Notify clients about new AI trading decisions"""
        await self.manager.broadcast_to_topic("ai_decisions", {
            "type": "new_decision",
            "decision": decision_data
        })
    
    async def notify_trade_execution(self, trade_data: Dict):
        """Notify clients about trade executions"""
        await self.manager.broadcast_to_topic("trades", {
            "type": "trade_executed",
            "trade": trade_data
        })
    
    async def notify_portfolio_update(self, portfolio_data: Dict):
        """Notify clients about portfolio updates"""
        await self.manager.broadcast_to_topic("portfolio", {
            "type": "portfolio_updated",
            "portfolio": portfolio_data
        })
    
    async def notify_engine_status(self, status_data: Dict):
        """Notify clients about trading engine status changes"""
        await self.manager.broadcast_to_topic("engine_status", {
            "type": "status_change",
            "status": status_data
        })
    
    async def notify_market_data(self, symbol: str, market_data: Dict):
        """Notify clients about market data updates"""
        await self.manager.broadcast_to_topic("market_data", {
            "type": "price_update",
            "symbol": symbol,
            "data": market_data
        })
    
    async def notify_news_analysis(self, news_data: Dict):
        """Notify clients about new news analysis"""
        await self.manager.broadcast_to_topic("news", {
            "type": "news_analyzed",
            "news": news_data
        })
    
    async def notify_error(self, error_data: Dict):
        """Notify clients about errors"""
        await self.manager.broadcast_to_topic("errors", {
            "type": "error",
            "error": error_data
        })
    
    async def send_analytics_update(self, analytics_data: Dict):
        """Send analytics updates to subscribed clients"""
        await self.manager.broadcast_to_topic("analytics", {
            "type": "analytics_update",
            "data": analytics_data
        })

# Global trading WebSocket manager
trading_ws_manager = TradingWebSocketManager(manager)
