"""
Database and Redis utilities for routers
"""
import redis.asyncio as redis
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    
    class Config:
        env_file = ".env"


settings = Settings()
DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Global Redis client
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def get_db():
    async with async_session() as session:
        yield session
