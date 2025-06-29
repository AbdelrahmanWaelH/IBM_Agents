"""
Standalone WebSocket Server for Real-time Trading Updates
Using the websockets library version 14+ compatible handler
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import Dict, Set
import uuid

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, any] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        
    async def register(self, websocket) -> str:
        """Register a new WebSocket connection"""
        connection_id = f"client_{int(datetime.now().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}"
        self.connections[connection_id] = websocket
        self.subscriptions[connection_id] = set()
        logger.info(f"✅ WebSocket client connected: {connection_id}")
        return connection_id
    
    async def unregister(self, connection_id: str):
        """Unregister a WebSocket connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
        if connection_id in self.subscriptions:
            del self.subscriptions[connection_id]
        logger.info(f"🔌 WebSocket client disconnected: {connection_id}")
    
    async def subscribe(self, connection_id: str, topics: list):
        """Subscribe a connection to topics"""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].update(topics)
            logger.info(f"Client {connection_id} subscribed to: {topics}")
    
    async def send_to_connection(self, connection_id: str, message: dict):
        """Send message to a specific connection"""
        if connection_id in self.connections:
            try:
                await self.connections[connection_id].send(json.dumps(message))
                return True
            except websockets.exceptions.ConnectionClosed:
                await self.unregister(connection_id)
                return False
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                return False
        return False

# Global manager instance
ws_manager = WebSocketManager()

async def handle_client(websocket):
    """Handle a WebSocket client connection - compatible with websockets 14+"""
    connection_id = None
    try:
        # Register the connection
        connection_id = await ws_manager.register(websocket)
        
        # Send welcome message
        await websocket.send(json.dumps({
            "type": "welcome",
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Keep the connection alive and handle incoming messages
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"Received message from {connection_id}: {data}")
                
                if data.get("type") == "subscribe":
                    topics = data.get("topics", [])
                    await ws_manager.subscribe(connection_id, topics)
                    await websocket.send(json.dumps({
                        "type": "subscription_confirmed",
                        "topics": topics,
                        "timestamp": datetime.now().isoformat()
                    }))
                
                elif data.get("type") == "ping":
                    await websocket.send(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }))
            except Exception as e:
                logger.error(f"Error handling message from {connection_id}: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed normally for {connection_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
    finally:
        if connection_id:
            await ws_manager.unregister(connection_id)

async def start_websocket_server():
    """Start the WebSocket server"""
    logger.info("🚀 Starting WebSocket server on localhost:8002")
    
    # Use the proper server creation for websockets 14+
    server = await websockets.serve(handle_client, "localhost", 8002)
    logger.info("✅ WebSocket server running on ws://localhost:8002")
    
    # Keep the server running
    await server.wait_closed()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(start_websocket_server())
