"""
Dating Bot Platform - Scheduler
"""
import os
import json
import asyncio
import logging
from datetime import datetime

import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    class Config:
        env_file = ".env"

settings = Settings()
DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class TaskScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.redis_client = None
        
    async def start(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        
        self.scheduler.add_job(self.schedule_boosts, CronTrigger(minute="*/5"), id="check_boosts")
        self.scheduler.add_job(self.schedule_swipe_sessions, CronTrigger(minute="*/30"), id="schedule_swipes")
        self.scheduler.add_job(self.schedule_match_checks, CronTrigger(minute="*/10"), id="check_matches")
        self.scheduler.add_job(self.cleanup_stale_sessions, CronTrigger(hour="*/1"), id="cleanup")
        
        self.scheduler.start()
        logger.info("✅ Scheduler started")
        
    async def stop(self):
        self.scheduler.shutdown()
        if self.redis_client:
            await self.redis_client.close()
    
    async def schedule_boosts(self):
        now = datetime.now()
        async with async_session() as db:
            result = await db.execute(text("SELECT bc.vk_account_id, bc.boost_times FROM bot_configs bc JOIN vk_accounts va ON bc.vk_account_id = va.id WHERE bc.is_active = true AND va.status = 'active'"))
            for row in result.fetchall():
                boost_times = row.boost_times or []
                for boost_time in boost_times:
                    try:
                        bt_hour, bt_min = map(int, boost_time.split(":"))
                        diff = abs(now.hour * 60 + now.minute - bt_hour * 60 - bt_min)
                        if diff <= 2:
                            task = {"type": "activate_boost", "vk_account_id": str(row.vk_account_id), "timestamp": now.isoformat()}
                            await self.redis_client.lpush("task_queue", json.dumps(task))
                            logger.info(f"🚀 Scheduled boost for {str(row.vk_account_id)[:8]}...")
                            break
                    except ValueError:
                        continue
    
    async def schedule_swipe_sessions(self):
        async with async_session() as db:
            result = await db.execute(text("SELECT bc.vk_account_id FROM bot_configs bc JOIN vk_accounts va ON bc.vk_account_id = va.id WHERE bc.is_active = true AND va.status = 'active'"))
            for row in result.fetchall():
                task = {"type": "process_cards", "vk_account_id": str(row.vk_account_id), "params": {"max_swipes": 30}, "timestamp": datetime.utcnow().isoformat()}
                await self.redis_client.lpush("task_queue", json.dumps(task))
        logger.info("📋 Scheduled swipe sessions")
    
    async def schedule_match_checks(self):
        async with async_session() as db:
            result = await db.execute(text("SELECT va.id FROM vk_accounts va JOIN bot_configs bc ON va.id = bc.vk_account_id WHERE bc.is_active = true AND va.status = 'active'"))
            for row in result.fetchall():
                task = {"type": "check_matches", "vk_account_id": str(row.id), "timestamp": datetime.utcnow().isoformat()}
                await self.redis_client.lpush("task_queue", json.dumps(task))
        logger.info("💕 Scheduled match checks")
    
    async def cleanup_stale_sessions(self):
        async with async_session() as db:
            await db.execute(text("UPDATE vk_accounts SET status = 'inactive' WHERE status = 'active' AND last_active_at < NOW() - INTERVAL '2 hours'"))
            await db.commit()
        logger.info("🧹 Cleaned up stale sessions")


async def main():
    scheduler = TaskScheduler()
    try:
        await scheduler.start()
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
