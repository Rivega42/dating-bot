"""
VK Authorization Service with VNC
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import base64

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class AuthSession:
    """Manages a single VK authorization session with VNC-like capabilities"""
    
    def __init__(self, session_id: str, account_id: str):
        self.session_id = session_id
        self.account_id = account_id
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.status = "initializing"
        self.created_at = datetime.utcnow()
        self.last_screenshot = None
        self.screenshot_lock = asyncio.Lock()
        
    async def start(self):
        """Start browser for authorization"""
        self.playwright = await async_playwright().start()
        
        # Launch browser in headed mode (visible)
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # Still headless, we'll stream screenshots
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.page = await self.context.new_page()
        self.status = "ready"
        logger.info(f"Auth session {self.session_id} started")
        
    async def navigate_to_vk_login(self):
        """Navigate to VK login page"""
        await self.page.goto("https://vk.com/")
        self.status = "login_page"
        
    async def get_screenshot(self) -> str:
        """Get current page screenshot as base64"""
        async with self.screenshot_lock:
            screenshot = await self.page.screenshot(type="jpeg", quality=80)
            self.last_screenshot = base64.b64encode(screenshot).decode()
            return self.last_screenshot
    
    async def click(self, x: int, y: int):
        """Click at coordinates"""
        await self.page.mouse.click(x, y)
        await asyncio.sleep(0.1)
        
    async def type_text(self, text: str):
        """Type text"""
        await self.page.keyboard.type(text, delay=50)
        
    async def press_key(self, key: str):
        """Press a key (Enter, Tab, etc)"""
        await self.page.keyboard.press(key)
        
    async def check_login_success(self) -> bool:
        """Check if login was successful"""
        try:
            # Check for logged in indicators
            await self.page.wait_for_selector(
                "#top_profile_link, .TopNavBtn__profileLink, [data-task-click='ProfileLink']",
                timeout=5000
            )
            self.status = "logged_in"
            return True
        except:
            return False
    
    async def get_session_data(self) -> dict:
        """Get session cookies and storage for later use"""
        if not self.context:
            return None
        storage_state = await self.context.storage_state()
        return storage_state
    
    async def close(self):
        """Close the session"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.status = "closed"
        logger.info(f"Auth session {self.session_id} closed")


class AuthManager:
    """Manages multiple authorization sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, AuthSession] = {}
        self.lock = asyncio.Lock()
        
    async def create_session(self, account_id: str) -> str:
        """Create new auth session, return session_id"""
        import uuid
        session_id = str(uuid.uuid4())
        
        async with self.lock:
            session = AuthSession(session_id, account_id)
            await session.start()
            await session.navigate_to_vk_login()
            self.sessions[session_id] = session
            
        # Start cleanup task
        asyncio.create_task(self._session_timeout(session_id, timeout=600))  # 10 min timeout
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[AuthSession]:
        """Get existing session"""
        return self.sessions.get(session_id)
    
    async def close_session(self, session_id: str) -> Optional[dict]:
        """Close session and return session data if logged in"""
        async with self.lock:
            session = self.sessions.pop(session_id, None)
            if not session:
                return None
                
            session_data = None
            if session.status == "logged_in":
                session_data = await session.get_session_data()
                
            await session.close()
            return session_data
    
    async def _session_timeout(self, session_id: str, timeout: int):
        """Auto-close session after timeout"""
        await asyncio.sleep(timeout)
        if session_id in self.sessions:
            logger.warning(f"Session {session_id} timed out")
            await self.close_session(session_id)
    
    def get_active_sessions(self) -> list:
        """Get list of active sessions"""
        return [
            {
                "session_id": s.session_id,
                "account_id": s.account_id,
                "status": s.status,
                "created_at": s.created_at.isoformat()
            }
            for s in self.sessions.values()
        ]


# Global auth manager instance
auth_manager = AuthManager()
