"""
SOLID WebSocket Server for Real-time Trading Updates
Minimal, robust implementation for websockets 14+
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global connections storage
connections = {}

async def register_client(websocket):
    """Register a new client connection"""
    client_id = f"client_{int(datetime.now().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}"
    connections[client_id] = {
        'websocket': websocket,
        'subscriptions': set(),
        'connected_at': datetime.now()
    }
    logger.info(f"✅ Client registered: {client_id}")
    return client_id

async def unregister_client(client_id):
    """Unregister a client connection"""
    if client_id in connections:
        del connections[client_id]
        logger.info(f"🔌 Client unregistered: {client_id}")

async def handle_client(websocket):
    """Handle WebSocket client - SOLID implementation"""
    client_id = None
    try:
        # Register the client
        client_id = await register_client(websocket)
        logger.info(f"� New connection from {websocket.remote_address}")
        
        # Keep connection alive - wait for messages
        await websocket.wait_closed()
        
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed normally for {client_id}")
    except Exception as e:
        logger.error(f"Error handling client {client_id}: {e}")
    finally:
        if client_id:
            await unregister_client(client_id)

async def start_server():
    """Start the WebSocket server"""
    logger.info("🚀 Starting WebSocket server on localhost:8002")
    
    # Start server with minimal configuration
    async with websockets.serve(
        handle_client,
        "localhost", 
        8002,
        ping_interval=20,
        ping_timeout=10
    ):
        logger.info("✅ WebSocket server is running on ws://localhost:8002")
        # Keep server running
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error sending message to {connection_id}: {e}")

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
