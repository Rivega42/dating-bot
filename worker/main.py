"""
Dating Bot Platform - Browser Worker
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import redis.asyncio as redis
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    max_browsers: int = 8
    browser_timeout: int = 30000
    worker_id: str = "worker-1"
    anthropic_api_key: Optional[str] = None
    class Config:
        env_file = ".env"

settings = Settings()
DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class BrowserPool:
    def __init__(self, max_browsers: int = 8):
        self.max_browsers = max_browsers
        self.browsers: Dict[str, Dict[str, Any]] = {}
        self.playwright = None
        self.lock = asyncio.Lock()
        
    async def start(self):
        self.playwright = await async_playwright().start()
        logger.info(f"🚀 Browser pool started (max: {self.max_browsers})")
        
    async def stop(self):
        for account_id in list(self.browsers.keys()):
            await self.release(account_id)
        if self.playwright:
            await self.playwright.stop()
        
    async def get_or_create(self, account_id: str, session_data: Optional[dict] = None) -> Page:
        async with self.lock:
            if account_id in self.browsers:
                self.browsers[account_id]["last_active"] = datetime.utcnow()
                return self.browsers[account_id]["page"]
            
            if len(self.browsers) >= self.max_browsers:
                await self._evict_least_active()
            
            browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--no-first-run', '--no-zygote', '--single-process']
            )
            
            context_options = {"viewport": {"width": 1280, "height": 720}, "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            if session_data:
                context_options["storage_state"] = session_data
                
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            page.set_default_timeout(settings.browser_timeout)
            
            self.browsers[account_id] = {"browser": browser, "context": context, "page": page, "last_active": datetime.utcnow()}
            logger.info(f"🌐 Browser created for account {account_id[:8]}... ({len(self.browsers)}/{self.max_browsers})")
            return page
    
    async def release(self, account_id: str, save_session: bool = True) -> Optional[dict]:
        async with self.lock:
            if account_id not in self.browsers:
                return None
            entry = self.browsers[account_id]
            session_data = None
            if save_session:
                try:
                    session_data = await entry["context"].storage_state()
                except:
                    pass
            try:
                await entry["browser"].close()
            except:
                pass
            del self.browsers[account_id]
            return session_data
    
    async def _evict_least_active(self):
        if not self.browsers:
            return
        oldest = min(self.browsers.items(), key=lambda x: x[1]["last_active"])
        await self.release(oldest[0])
    
    def get_status(self) -> dict:
        return {"active_browsers": len(self.browsers), "max_browsers": self.max_browsers, "accounts": list(self.browsers.keys())}


class VKDatingBot:
    def __init__(self, page: Page, account_id: str, config: dict):
        self.page = page
        self.account_id = account_id
        self.config = config
        self.frame = None
        self.running = True
        
    async def start(self, app_id: str):
        logger.info(f"🎮 Starting bot for account {self.account_id[:8]}...")
        await self.page.goto(f"https://vk.com/app{app_id}")
        await self.page.wait_for_selector("iframe", timeout=30000)
        self.frame = self.page.frame_locator("iframe").first
        logger.info(f"✅ Mini app loaded for account {self.account_id[:8]}...")
        return True
    
    async def parse_card(self) -> Optional[dict]:
        try:
            card = self.frame.locator(".card-container, .profile-card, [class*='card']").first
            if not await card.is_visible():
                return None
            data = {"timestamp": datetime.utcnow().isoformat()}
            name_el = card.locator(".name, .profile-name, [class*='name']").first
            if await name_el.is_visible():
                data["name"] = await name_el.inner_text()
            bio_el = card.locator(".bio, .description, [class*='bio']").first
            if await bio_el.is_visible():
                data["bio"] = await bio_el.inner_text()
            return data
        except Exception as e:
            logger.error(f"Error parsing card: {e}")
            return None
    
    def evaluate_card(self, card_data: dict) -> dict:
        quest = self.config.get("active_quest", "ideal_date")
        filters = self.config.get("quest_filters", {})
        score = 0
        reasons = []
        bio = (card_data.get("bio") or "").lower()
        
        if quest == "ideal_date":
            target_interests = filters.get("interests", ["путешествия", "музыка", "кино"])
            for interest in target_interests:
                if interest.lower() in bio:
                    score += 20
                    reasons.append(f"интерес: {interest}")
        elif quest == "investor":
            keywords = ["инвестор", "бизнес", "стартап", "ceo", "founder"]
            for kw in keywords:
                if kw in bio:
                    score += 40
                    reasons.append(f"ключевое слово: {kw}")
                    break
        
        return {"like": score >= 30, "score": score, "reasons": reasons}
    
    async def swipe(self, like: bool):
        try:
            if like:
                btn = self.frame.locator(".btn-like, .like-button, [class*='like']").first
            else:
                btn = self.frame.locator(".btn-skip, .skip-button, [class*='skip']").first
            await btn.click()
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error swiping: {e}")
    
    async def activate_boost(self) -> bool:
        try:
            boost_btn = self.frame.locator(".boost-btn:not(.active), .boost-button:not(.used)").first
            if await boost_btn.is_visible():
                await boost_btn.click()
                logger.info(f"🚀 Boost activated for {self.account_id[:8]}...")
                return True
        except Exception as e:
            logger.error(f"Error activating boost: {e}")
        return False
    
    async def run_swipe_session(self, max_swipes: int = 50):
        swipes = 0
        while self.running and swipes < max_swipes:
            try:
                await self.frame.locator(".card-container, .profile-card").first.wait_for(timeout=10000)
                card = await self.parse_card()
                if not card:
                    await asyncio.sleep(2)
                    continue
                decision = self.evaluate_card(card)
                logger.info(f"👤 {card.get('name', 'Unknown')}: score={decision['score']}, like={decision['like']}")
                await self.swipe(like=decision["like"])
                swipes += 1
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Swipe session error: {e}")
                await asyncio.sleep(5)
        logger.info(f"📊 Swipe session completed: {swipes} swipes")
        return swipes
    
    def stop(self):
        self.running = False


class TaskProcessor:
    def __init__(self):
        self.browser_pool = BrowserPool(settings.max_browsers)
        self.redis_client = None
        self.bots: Dict[str, VKDatingBot] = {}
        self.running = True
        
    async def start(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await self.browser_pool.start()
        pubsub = self.redis_client.pubsub()
        await pubsub.psubscribe("control:*")
        asyncio.create_task(self._listen_control(pubsub))
        logger.info(f"✅ Task processor started (worker: {settings.worker_id})")
        
    async def stop(self):
        self.running = False
        await self.browser_pool.stop()
        if self.redis_client:
            await self.redis_client.close()
    
    async def _listen_control(self, pubsub):
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                command = message["data"]
                account_id = channel.split(":")[-1]
                if command == "stop" and account_id in self.bots:
                    self.bots[account_id].stop()
                    await self.browser_pool.release(account_id)
                    del self.bots[account_id]
                    logger.info(f"⏹️ Bot stopped for {account_id[:8]}...")
    
    async def process_queue(self):
        while self.running:
            try:
                result = await self.redis_client.brpop("task_queue", timeout=5)
                if not result:
                    continue
                _, task_json = result
                task = json.loads(task_json)
                await self._process_task(task)
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)
    
    async def _process_task(self, task: dict):
        task_type = task.get("type")
        account_id = task.get("vk_account_id")
        logger.info(f"📋 Processing task: {task_type} for {account_id[:8] if account_id else 'N/A'}...")
        
        try:
            if task_type == "start_session":
                await self._handle_start_session(task)
            elif task_type == "process_cards":
                if account_id in self.bots:
                    await self.bots[account_id].run_swipe_session(task.get("params", {}).get("max_swipes", 50))
            elif task_type == "activate_boost":
                if account_id in self.bots:
                    await self.bots[account_id].activate_boost()
        except Exception as e:
            logger.error(f"Task processing error: {e}")
            await self._update_account_status(account_id, "error", str(e))
    
    async def _handle_start_session(self, task: dict):
        account_id = task["vk_account_id"]
        async with async_session() as db:
            result = await db.execute(
                text("SELECT va.session_data_encrypted, va.vk_app_id, bc.active_quest, bc.quest_filters, bc.boost_times FROM vk_accounts va JOIN bot_configs bc ON va.id = bc.vk_account_id WHERE va.id = :account_id"),
                {"account_id": account_id}
            )
            row = result.fetchone()
            if not row:
                return
            
            session_data = json.loads(row.session_data_encrypted.decode()) if row.session_data_encrypted else None
            config = {"active_quest": row.active_quest, "quest_filters": json.loads(row.quest_filters) if row.quest_filters else {}, "boost_times": row.boost_times}
            
            page = await self.browser_pool.get_or_create(account_id, session_data)
            bot = VKDatingBot(page, account_id, config)
            await bot.start(row.vk_app_id)
            self.bots[account_id] = bot
            await self._update_account_status(account_id, "active")
            asyncio.create_task(bot.run_swipe_session())
    
    async def _update_account_status(self, account_id: str, status: str, error: str = None):
        async with async_session() as db:
            if error:
                await db.execute(text("UPDATE vk_accounts SET status = :status, error_message = :error, last_active_at = NOW() WHERE id = :id"), {"id": account_id, "status": status, "error": error})
            else:
                await db.execute(text("UPDATE vk_accounts SET status = :status, error_message = NULL, last_active_at = NOW() WHERE id = :id"), {"id": account_id, "status": status})
            await db.commit()
    
    async def report_status(self):
        while self.running:
            status = self.browser_pool.get_status()
            await self.redis_client.hset("worker_load", settings.worker_id, len(self.bots))
            logger.info(f"📊 Status: {status['active_browsers']}/{status['max_browsers']} browsers, {len(self.bots)} bots")
            await asyncio.sleep(60)


async def main():
    processor = TaskProcessor()
    try:
        await processor.start()
        await asyncio.gather(processor.process_queue(), processor.report_status())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    finally:
        await processor.stop()


if __name__ == "__main__":
    asyncio.run(main())
