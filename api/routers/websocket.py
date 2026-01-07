"""
WebSocket Router for Auth Sessions
"""
import json
import asyncio
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
    
    async def send_screenshot(self, session_id: str, screenshot_base64: str):
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_json({
                "type": "screenshot",
                "data": screenshot_base64
            })
    
    async def send_status(self, session_id: str, status: str):
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_json({
                "type": "status",
                "status": status
            })


manager = ConnectionManager()


@router.websocket("/ws/auth/{session_id}")
async def auth_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for auth session.
    Streams screenshots and receives user input.
    """
    await manager.connect(session_id, websocket)
    
    try:
        from database import redis_client
        
        # Subscribe to screenshots
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"auth_screen:{session_id}")
        
        async def receive_messages():
            while True:
                try:
                    data = await websocket.receive_json()
                    action = data.get("action")
                    
                    if action == "click":
                        await redis_client.publish(f"auth_control:{session_id}", json.dumps({
                            "action": "click",
                            "x": data["x"],
                            "y": data["y"]
                        }))
                    elif action == "type":
                        await redis_client.publish(f"auth_control:{session_id}", json.dumps({
                            "action": "type",
                            "text": data["text"]
                        }))
                    elif action == "key":
                        await redis_client.publish(f"auth_control:{session_id}", json.dumps({
                            "action": "key",
                            "key": data["key"]
                        }))
                except WebSocketDisconnect:
                    break
        
        async def send_screenshots():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_json({
                        "type": "screenshot",
                        "data": message["data"]
                    })
        
        await asyncio.gather(
            receive_messages(),
            send_screenshots()
        )
        
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(session_id)
        await pubsub.unsubscribe(f"auth_screen:{session_id}")
