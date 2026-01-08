"""
Dating Bot Platform - Browser Worker
VK Dating селекторы основаны на исследовании DOM (2026-01-08)
"""
import os
import json
import asyncio
import logging
import re
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


# VK Dating селекторы (m.vk.com/dating - мобильная версия без iframe)
class VKSelectors:
    # Кнопки действий (по иконкам внутри)
    BTN_SKIP = 'button:has([class*="vkuiIcon--cancel_outline_28"])'
    BTN_LIKE = 'button:has([class*="vkuiIcon--like_outline_28"]):not([class*="TabbarItem"])'
    BTN_SUPERLIKE = 'button:has([class*="vkuiIcon--fire_alt_outline_28"])'
    BTN_REWIND = 'button:has([class*="vkuiIcon--replay_outline_28"])'
    BTN_BOOST = 'button:has([class*="vkuiIcon--flash_28"])'
    
    # Табы навигации
    TAB_CARDS = '[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--cards_2_outline_28"])'
    TAB_COLLECTIONS = '[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--search_like_outline_28"])'
    TAB_LIKES = '[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--like_outline_28"])'
    TAB_CHATS = '[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--message_outline_28"])'
    TAB_PROFILE = '[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--user_circle_outline_28"])'
    
    # Данные профиля
    PROFILE_NAME = '[class*="vkuiTitle__level2"][class*="accent"]'
    PROFILE_INFO = '[class*="vkuiMiniInfoCell"]'
    PROFILE_TEXT = '[class*="vkuiText"], [class*="vkuiParagraph"]'
    
    # Контейнеры
    PANEL = '[class*="vkuiPanel__in"]'
    CARD_AREA = '[class*="vkuiView__panel"]'


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
                args=[
                    '--no-sandbox', 
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage', 
                    '--disable-gpu', 
                    '--no-first-run', 
                    '--no-zygote', 
                    '--single-process',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # Мобильный user-agent для m.vk.com
            context_options = {
                "viewport": {"width": 414, "height": 896},
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                "locale": "ru-RU",
                "timezone_id": "Europe/Moscow"
            }
            if session_data:
                context_options["storage_state"] = session_data
                
            context = await browser.new_context(**context_options)
            
            # Anti-detection
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            
            page = await context.new_page()
            page.set_default_timeout(settings.browser_timeout)
            
            self.browsers[account_id] = {
                "browser": browser, 
                "context": context, 
                "page": page, 
                "last_active": datetime.utcnow()
            }
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
        return {
            "active_browsers": len(self.browsers), 
            "max_browsers": self.max_browsers, 
            "accounts": list(self.browsers.keys())
        }


class VKDatingBot:
    """Бот для VK Dating (m.vk.com/dating)"""
    
    def __init__(self, page: Page, account_id: str, config: dict):
        self.page = page
        self.account_id = account_id
        self.config = config
        self.running = True
        self.stats = {"likes": 0, "skips": 0, "matches": 0}
        
    async def start(self):
        """Открывает VK Dating"""
        logger.info(f"🎮 Starting bot for account {self.account_id[:8]}...")
        
        # Мобильная версия - без iframe!
        await self.page.goto("https://m.vk.com/dating", wait_until="domcontentloaded")
        
        # Ждём загрузки приложения
        try:
            await self.page.wait_for_selector(VKSelectors.PROFILE_NAME, timeout=30000)
            logger.info(f"✅ VK Dating loaded for account {self.account_id[:8]}")
            return True
        except:
            # Возможно нужна авторизация
            logger.warning(f"⚠️ Dating not loaded, may need auth for {self.account_id[:8]}")
            return False
    
    async def parse_card(self) -> Optional[dict]:
        """Парсит текущую карточку профиля"""
        try:
            # Ждём карточку
            name_el = self.page.locator(VKSelectors.PROFILE_NAME).first
            if not await name_el.is_visible(timeout=5000):
                return None
            
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "account_id": self.account_id
            }
            
            # Имя и возраст
            name_text = await name_el.inner_text()
            data["raw_name"] = name_text
            
            # Парсим "Имя, 25"
            match = re.match(r'^(.+?),\s*(\d+)$', name_text.strip())
            if match:
                data["name"] = match.group(1)
                data["age"] = int(match.group(2))
            else:
                data["name"] = name_text
            
            # Дополнительная информация (город, работа, образование)
            info_items = []
            info_els = self.page.locator(VKSelectors.PROFILE_INFO)
            count = await info_els.count()
            for i in range(min(count, 5)):
                text = await info_els.nth(i).inner_text()
                if text.strip():
                    info_items.append(text.strip())
            data["info"] = info_items
            
            # Текст профиля (bio)
            text_els = self.page.locator(VKSelectors.PROFILE_TEXT)
            texts = []
            count = await text_els.count()
            for i in range(min(count, 10)):
                text = await text_els.nth(i).inner_text()
                if text.strip() and len(text.strip()) > 3:
                    texts.append(text.strip())
            data["bio"] = " ".join(texts)
            
            logger.info(f"👤 Parsed: {data.get('name', 'Unknown')}, {data.get('age', '?')} - {data.get('info', [])[:2]}")
            return data
            
        except Exception as e:
            logger.error(f"Error parsing card: {e}")
            return None
    
    def evaluate_card(self, card_data: dict) -> dict:
        """Оценивает карточку по настроенным критериям"""
        quest = self.config.get("active_quest", "ideal_date")
        filters = self.config.get("quest_filters", {})
        
        score = 0
        reasons = []
        
        age = card_data.get("age", 0)
        bio = (card_data.get("bio") or "").lower()
        info = " ".join(card_data.get("info", [])).lower()
        
        # Фильтр по возрасту
        min_age = filters.get("min_age", 18)
        max_age = filters.get("max_age", 100)
        if min_age <= age <= max_age:
            score += 10
            reasons.append(f"возраст {age} в диапазоне")
        elif age > 0:
            score -= 50
            reasons.append(f"возраст {age} вне диапазона")
        
        # Оценка по квесту
        if quest == "ideal_date":
            target_interests = filters.get("interests", ["путешествия", "музыка", "кино", "спорт"])
            for interest in target_interests:
                if interest.lower() in bio or interest.lower() in info:
                    score += 15
                    reasons.append(f"интерес: {interest}")
                    
        elif quest == "investor":
            keywords = ["инвестор", "бизнес", "стартап", "ceo", "founder", "предприниматель", "директор"]
            for kw in keywords:
                if kw in bio or kw in info:
                    score += 40
                    reasons.append(f"бизнес: {kw}")
                    
        elif quest == "creative":
            keywords = ["художник", "музыкант", "дизайнер", "фотограф", "творческ", "искусств"]
            for kw in keywords:
                if kw in bio or kw in info:
                    score += 30
                    reasons.append(f"творчество: {kw}")
        
        # Негативные фильтры
        negative = filters.get("negative_keywords", [])
        for neg in negative:
            if neg.lower() in bio:
                score -= 100
                reasons.append(f"негатив: {neg}")
        
        decision = {
            "like": score >= filters.get("min_score", 20),
            "superlike": score >= filters.get("superlike_score", 60),
            "score": score,
            "reasons": reasons
        }
        
        return decision
    
    async def click_like(self) -> bool:
        """Нажимает кнопку лайка"""
        try:
            btn = self.page.locator(VKSelectors.BTN_LIKE).first
            await btn.click()
            self.stats["likes"] += 1
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Error clicking like: {e}")
            return False
    
    async def click_skip(self) -> bool:
        """Нажимает кнопку пропуска"""
        try:
            btn = self.page.locator(VKSelectors.BTN_SKIP).first
            await btn.click()
            self.stats["skips"] += 1
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Error clicking skip: {e}")
            return False
    
    async def click_superlike(self) -> bool:
        """Нажимает суперлайк"""
        try:
            btn = self.page.locator(VKSelectors.BTN_SUPERLIKE).first
            if await btn.is_visible():
                await btn.click()
                logger.info(f"💜 Superlike sent!")
                await asyncio.sleep(0.5)
                return True
        except Exception as e:
            logger.error(f"Error clicking superlike: {e}")
        return False
    
    async def activate_boost(self) -> bool:
        """Активирует буст"""
        try:
            btn = self.page.locator(VKSelectors.BTN_BOOST).first
            if await btn.is_visible():
                await btn.click()
                logger.info(f"🚀 Boost activated for {self.account_id[:8]}")
                return True
        except Exception as e:
            logger.error(f"Error activating boost: {e}")
        return False
    
    async def go_to_tab(self, tab: str) -> bool:
        """Переходит на указанный таб"""
        selectors = {
            "cards": VKSelectors.TAB_CARDS,
            "collections": VKSelectors.TAB_COLLECTIONS,
            "likes": VKSelectors.TAB_LIKES,
            "chats": VKSelectors.TAB_CHATS,
            "profile": VKSelectors.TAB_PROFILE
        }
        try:
            if tab in selectors:
                await self.page.locator(selectors[tab]).click()
                await asyncio.sleep(1)
                return True
        except Exception as e:
            logger.error(f"Error navigating to {tab}: {e}")
        return False
    
    async def run_swipe_session(self, max_swipes: int = 50) -> dict:
        """Запускает сессию свайпов"""
        swipes = 0
        
        # Переходим на вкладку анкет
        await self.go_to_tab("cards")
        await asyncio.sleep(2)
        
        while self.running and swipes < max_swipes:
            try:
                # Парсим карточку
                card = await self.parse_card()
                if not card:
                    logger.info("No card visible, waiting...")
                    await asyncio.sleep(3)
                    continue
                
                # Оцениваем
                decision = self.evaluate_card(card)
                logger.info(f"👤 {card.get('name', '?')}, {card.get('age', '?')}: "
                           f"score={decision['score']}, like={decision['like']} "
                           f"({', '.join(decision['reasons'][:3])})")
                
                # Действуем
                if decision.get("superlike") and await self.click_superlike():
                    pass
                elif decision["like"]:
                    await self.click_like()
                else:
                    await self.click_skip()
                
                swipes += 1
                
                # Случайная задержка 1-3 сек
                await asyncio.sleep(1 + (swipes % 3))
                
            except Exception as e:
                logger.error(f"Swipe session error: {e}")
                await asyncio.sleep(5)
        
        logger.info(f"📊 Session done: {swipes} swipes, {self.stats['likes']} likes, {self.stats['skips']} skips")
        return self.stats
    
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
        for bot in self.bots.values():
            bot.stop()
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
                    logger.info(f"⏹️ Bot stopped for {account_id[:8]}")
    
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
        
        logger.info(f"📋 Processing task: {task_type} for {account_id[:8] if account_id else 'N/A'}")
        
        try:
            if task_type == "start_session":
                await self._handle_start_session(task)
                
            elif task_type == "process_cards":
                if account_id in self.bots:
                    max_swipes = task.get("params", {}).get("max_swipes", 50)
                    await self.bots[account_id].run_swipe_session(max_swipes)
                    
            elif task_type == "activate_boost":
                if account_id in self.bots:
                    await self.bots[account_id].activate_boost()
                    
            elif task_type == "stop_session":
                if account_id in self.bots:
                    self.bots[account_id].stop()
                    session_data = await self.browser_pool.release(account_id)
                    if session_data:
                        await self._save_session(account_id, session_data)
                    del self.bots[account_id]
                    
        except Exception as e:
            logger.error(f"Task processing error: {e}")
            await self._update_account_status(account_id, "error", str(e))
    
    async def _handle_start_session(self, task: dict):
        account_id = task["vk_account_id"]
        
        async with async_session() as db:
            result = await db.execute(
                text("""
                    SELECT va.session_data_encrypted, bc.active_quest, bc.quest_filters, bc.boost_times 
                    FROM vk_accounts va 
                    LEFT JOIN bot_configs bc ON va.id = bc.vk_account_id 
                    WHERE va.id = :account_id
                """),
                {"account_id": account_id}
            )
            row = result.fetchone()
            
            if not row:
                logger.error(f"Account {account_id} not found")
                return
            
            session_data = None
            if row.session_data_encrypted:
                try:
                    session_data = json.loads(row.session_data_encrypted.decode())
                except:
                    pass
            
            config = {
                "active_quest": row.active_quest or "ideal_date",
                "quest_filters": json.loads(row.quest_filters) if row.quest_filters else {},
                "boost_times": row.boost_times
            }
            
            page = await self.browser_pool.get_or_create(account_id, session_data)
            bot = VKDatingBot(page, account_id, config)
            
            if await bot.start():
                self.bots[account_id] = bot
                await self._update_account_status(account_id, "active")
                asyncio.create_task(bot.run_swipe_session())
            else:
                await self._update_account_status(account_id, "auth_required")
    
    async def _update_account_status(self, account_id: str, status: str, error: str = None):
        async with async_session() as db:
            if error:
                await db.execute(
                    text("UPDATE vk_accounts SET status = :status, error_message = :error, last_active_at = NOW() WHERE id = :id"),
                    {"id": account_id, "status": status, "error": error}
                )
            else:
                await db.execute(
                    text("UPDATE vk_accounts SET status = :status, error_message = NULL, last_active_at = NOW() WHERE id = :id"),
                    {"id": account_id, "status": status}
                )
            await db.commit()
    
    async def _save_session(self, account_id: str, session_data: dict):
        async with async_session() as db:
            await db.execute(
                text("UPDATE vk_accounts SET session_data_encrypted = :session WHERE id = :id"),
                {"id": account_id, "session": json.dumps(session_data).encode()}
            )
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
        await asyncio.gather(
            processor.process_queue(),
            processor.report_status()
        )
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    finally:
        await processor.stop()


if __name__ == "__main__":
    asyncio.run(main())
