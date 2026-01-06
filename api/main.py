"""
Dating Bot Platform - API
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pydantic_settings import BaseSettings
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from jose import JWTError, jwt
from passlib.context import CryptContext
import uuid


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    environment: str = "production"
    
    class Config:
        env_file = ".env"

settings = Settings()
DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session

redis_pool = None

async def get_redis():
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.from_url(settings.redis_url, decode_responses=True)
    return redis_pool

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
        client_id: str = payload.get("sub")
        if client_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = await db.execute(
        text("SELECT * FROM clients WHERE id = :id AND is_active = true"),
        {"id": client_id}
    )
    user = result.fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class ClientCreate(BaseModel):
    email: EmailStr
    password: str

class ClientLogin(BaseModel):
    email: EmailStr
    password: str

class ClientResponse(BaseModel):
    id: str
    email: str
    subscription_tier: str
    subscription_until: Optional[datetime]
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class VKAccountCreate(BaseModel):
    vk_app_id: str
    session_data: dict

class BotConfigCreate(BaseModel):
    active_quest: str
    quest_filters: dict = {}
    boost_times: list[str] = ["19:00", "21:00", "23:00"]
    swipe_interval_minutes: int = 30
    dialogue_style: str = "balanced"

class BotConfigUpdate(BaseModel):
    active_quest: Optional[str] = None
    quest_filters: Optional[dict] = None
    boost_times: Optional[list[str]] = None
    is_active: Optional[bool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Dating Bot API...")
    yield
    global redis_pool
    if redis_pool:
        await redis_pool.close()
    print("👋 Shutting down...")

app = FastAPI(title="Dating Bot Platform API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        redis_client = await get_redis()
        await redis_client.ping()
        return {"status": "healthy", "database": "connected", "redis": "connected", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/auth/register", response_model=TokenResponse)
async def register(client: ClientCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT id FROM clients WHERE email = :email"), {"email": client.email})
    if result.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    client_id = str(uuid.uuid4())
    password_hash = get_password_hash(client.password)
    
    await db.execute(
        text("INSERT INTO clients (id, email, password_hash) VALUES (:id, :email, :password_hash)"),
        {"id": client_id, "email": client.email, "password_hash": password_hash}
    )
    await db.commit()
    
    access_token = create_access_token({"sub": client_id})
    return TokenResponse(access_token=access_token)


@app.post("/auth/login", response_model=TokenResponse)
async def login(client: ClientLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT id, password_hash FROM clients WHERE email = :email AND is_active = true"),
        {"email": client.email}
    )
    row = result.fetchone()
    
    if not row or not verify_password(client.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": str(row.id)})
    return TokenResponse(access_token=access_token)


@app.get("/auth/me", response_model=ClientResponse)
async def get_me(current_user = Depends(get_current_user)):
    return ClientResponse(
        id=str(current_user.id),
        email=current_user.email,
        subscription_tier=current_user.subscription_tier,
        subscription_until=current_user.subscription_until,
        created_at=current_user.created_at
    )


@app.post("/vk-accounts")
async def create_vk_account(account: VKAccountCreate, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account_id = str(uuid.uuid4())
    session_encrypted = json.dumps(account.session_data).encode()
    
    await db.execute(
        text("INSERT INTO vk_accounts (id, client_id, vk_app_id, session_data_encrypted, status) VALUES (:id, :client_id, :vk_app_id, :session_data, 'inactive')"),
        {"id": account_id, "client_id": str(current_user.id), "vk_app_id": account.vk_app_id, "session_data": session_encrypted}
    )
    await db.commit()
    return {"id": account_id, "status": "created"}


@app.get("/vk-accounts")
async def list_vk_accounts(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT id, vk_app_id, status, last_active_at, error_message, created_at FROM vk_accounts WHERE client_id = :client_id"),
        {"client_id": str(current_user.id)}
    )
    return [{"id": str(row.id), "vk_app_id": row.vk_app_id, "status": row.status, "last_active_at": row.last_active_at, "error_message": row.error_message, "created_at": row.created_at} for row in result.fetchall()]


@app.post("/vk-accounts/{account_id}/start")
async def start_bot(account_id: str, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT va.id FROM vk_accounts va JOIN bot_configs bc ON va.id = bc.vk_account_id WHERE va.id = :account_id AND va.client_id = :client_id"),
        {"account_id": account_id, "client_id": str(current_user.id)}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Account or config not found")
    
    redis_client = await get_redis()
    task = {"type": "start_session", "client_id": str(current_user.id), "vk_account_id": account_id, "timestamp": datetime.utcnow().isoformat()}
    await redis_client.lpush("task_queue", json.dumps(task))
    
    await db.execute(text("UPDATE vk_accounts SET status = 'starting' WHERE id = :id"), {"id": account_id})
    await db.execute(text("UPDATE bot_configs SET is_active = true WHERE vk_account_id = :id"), {"id": account_id})
    await db.commit()
    
    return {"status": "starting", "message": "Bot is being started"}


@app.post("/vk-accounts/{account_id}/stop")
async def stop_bot(account_id: str, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT id FROM vk_accounts WHERE id = :id AND client_id = :client_id"), {"id": account_id, "client_id": str(current_user.id)})
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Account not found")
    
    redis_client = await get_redis()
    await redis_client.publish(f"control:{account_id}", "stop")
    
    await db.execute(text("UPDATE vk_accounts SET status = 'inactive' WHERE id = :id"), {"id": account_id})
    await db.execute(text("UPDATE bot_configs SET is_active = false WHERE vk_account_id = :id"), {"id": account_id})
    await db.commit()
    
    return {"status": "stopped"}


@app.get("/stats")
async def get_stats(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client_id = str(current_user.id)
    
    result = await db.execute(
        text("SELECT action_type, COUNT(*) as count, COUNT(CASE WHEN result = 'success' THEN 1 END) as success_count FROM activity_log WHERE client_id = :client_id AND created_at > CURRENT_DATE GROUP BY action_type"),
        {"client_id": client_id}
    )
    today_stats = {row.action_type: {"total": row.count, "success": row.success_count} for row in result.fetchall()}
    
    result = await db.execute(text("SELECT COUNT(*) as count FROM dialogues WHERE client_id = :client_id AND outcome IS NULL"), {"client_id": client_id})
    active_dialogues = result.fetchone().count
    
    result = await db.execute(text("SELECT COUNT(*) as count FROM dialogues WHERE client_id = :client_id AND outcome = 'goal_reached'"), {"client_id": client_id})
    completed_quests = result.fetchone().count
    
    return {"today": today_stats, "active_dialogues": active_dialogues, "completed_quests": completed_quests}


@app.get("/queue/status")
async def queue_status(current_user = Depends(get_current_user)):
    redis_client = await get_redis()
    queue_len = await redis_client.llen("task_queue")
    return {"queue_length": queue_len, "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
