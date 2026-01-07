"""
Auth Worker - Handles VK authorization sessions
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import redis.asyncio as redis
from pydantic_settings import BaseSettings

from auth_service import AuthManager, AuthSession

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    screenshot_interval: float = 0.5  # seconds
    
    class Config:
        env_file = ".env"


settings = Settings()


class AuthWorker:
    def __init__(self):
        self.auth_manager = AuthManager()
        self.redis_client = None
        self.running = True
        self.screenshot_tasks: Dict[str, asyncio.Task] = {}
    
    async def start(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        logger.info("Auth worker started")
    
    async def stop(self):
        self.running = False
        for task in self.screenshot_tasks.values():
            task.cancel()
        for session_id in list(self.auth_manager.sessions.keys()):
            await self.auth_manager.close_session(session_id)
        if self.redis_client:
            await self.redis_client.close()
    
    async def process_auth_queue(self):
        """Process auth session creation requests"""
        while self.running:
            try:
                result = await self.redis_client.brpop("auth_queue", timeout=5)
                if not result:
                    continue
                
                _, task_json = result
                task = json.loads(task_json)
                
                if task["type"] == "create_auth_session":
                    session_id = task["session_id"]
                    account_id = task["vk_account_id"]
                    
                    # Create session
                    await self.auth_manager.create_session(account_id)
                    session = await self.auth_manager.get_session(session_id)
                    
                    if session is None:
                        # Session was created with new ID, need to map it
                        # For now, create with specific ID
                        session = AuthSession(session_id, account_id)
                        await session.start()
                        await session.navigate_to_vk_login()
                        self.auth_manager.sessions[session_id] = session
                    
                    # Start screenshot streaming
                    self.screenshot_tasks[session_id] = asyncio.create_task(
                        self._stream_screenshots(session_id)
                    )
                    
                    # Start control listener
                    asyncio.create_task(self._listen_control(session_id))
                    
                    logger.info(f"Auth session {session_id} created for account {account_id}")
                    
            except Exception as e:
                logger.error(f"Auth queue error: {e}")
                await asyncio.sleep(1)
    
    async def _stream_screenshots(self, session_id: str):
        """Stream screenshots to Redis for WebSocket clients"""
        while self.running:
            try:
                session = await self.auth_manager.get_session(session_id)
                if not session or session.status == "closed":
                    break
                
                screenshot = await session.get_screenshot()
                await self.redis_client.publish(f"auth_screen:{session_id}", screenshot)
                
                await asyncio.sleep(settings.screenshot_interval)
                
            except Exception as e:
                logger.error(f"Screenshot error for {session_id}: {e}")
                await asyncio.sleep(1)
    
    async def _listen_control(self, session_id: str):
        """Listen for control commands from API"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"auth_control:{session_id}")
        
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            
            try:
                command = json.loads(message["data"])
                action = command.get("action")
                
                session = await self.auth_manager.get_session(session_id)
                if not session:
                    break
                
                if action == "click":
                    await session.click(command["x"], command["y"])
                
                elif action == "type":
                    await session.type_text(command["text"])
                
                elif action == "key":
                    await session.press_key(command["key"])
                
                elif action == "complete":
                    # Check if logged in and get session data
                    is_logged_in = await session.check_login_success()
                    
                    if is_logged_in:
                        session_data = await session.get_session_data()
                        await self.redis_client.set(
                            f"auth_result:{session_id}",
                            json.dumps({"success": True, "session_data": session_data}),
                            ex=60  # 1 minute TTL
                        )
                    else:
                        await self.redis_client.set(
                            f"auth_result:{session_id}",
                            json.dumps({"success": False, "error": "Not logged in to VK"}),
                            ex=60
                        )
                    
                    # Cleanup
                    await self._cleanup_session(session_id)
                    break
                
                elif action == "cancel":
                    await self._cleanup_session(session_id)
                    break
                    
            except Exception as e:
                logger.error(f"Control command error: {e}")
        
        await pubsub.unsubscribe(f"auth_control:{session_id}")
    
    async def _cleanup_session(self, session_id: str):
        """Cleanup session resources"""
        if session_id in self.screenshot_tasks:
            self.screenshot_tasks[session_id].cancel()
            del self.screenshot_tasks[session_id]
        
        await self.auth_manager.close_session(session_id)
        logger.info(f"Session {session_id} cleaned up")


async def main():
    worker = AuthWorker()
    try:
        await worker.start()
        await worker.process_auth_queue()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
