"""
Auth Sessions Router - VK Authorization via Browser
"""
import json
import asyncio
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db

router = APIRouter(prefix="/auth-sessions", tags=["auth-sessions"])


class CreateAuthSessionRequest(BaseModel):
    vk_account_id: str


class AuthSessionResponse(BaseModel):
    session_id: str
    status: str
    websocket_url: str


class MouseClickRequest(BaseModel):
    x: int
    y: int


class TypeTextRequest(BaseModel):
    text: str


class KeyPressRequest(BaseModel):
    key: str


# In-memory auth sessions (in production, use Redis)
auth_sessions = {}


@router.post("", response_model=AuthSessionResponse)
async def create_auth_session(
    request: CreateAuthSessionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new authorization session for VK account.
    Returns session_id and WebSocket URL for browser streaming.
    """
    # Verify account exists
    result = await db.execute(
        text("SELECT id FROM vk_accounts WHERE id = :id"),
        {"id": request.vk_account_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="VK account not found")
    
    # Create auth session via Redis task
    import uuid
    session_id = str(uuid.uuid4())
    
    auth_sessions[session_id] = {
        "vk_account_id": request.vk_account_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Send task to worker
    from database import redis_client
    await redis_client.lpush("auth_queue", json.dumps({
        "type": "create_auth_session",
        "session_id": session_id,
        "vk_account_id": request.vk_account_id
    }))
    
    return AuthSessionResponse(
        session_id=session_id,
        status="pending",
        websocket_url=f"/ws/auth/{session_id}"
    )


@router.get("/{session_id}")
async def get_auth_session(session_id: str):
    """Get auth session status"""
    session = auth_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/click")
async def click_in_session(session_id: str, request: MouseClickRequest):
    """Send mouse click to auth session"""
    from database import redis_client
    await redis_client.publish(f"auth_control:{session_id}", json.dumps({
        "action": "click",
        "x": request.x,
        "y": request.y
    }))
    return {"status": "sent"}


@router.post("/{session_id}/type")
async def type_in_session(session_id: str, request: TypeTextRequest):
    """Send text input to auth session"""
    from database import redis_client
    await redis_client.publish(f"auth_control:{session_id}", json.dumps({
        "action": "type",
        "text": request.text
    }))
    return {"status": "sent"}


@router.post("/{session_id}/key")
async def press_key_in_session(session_id: str, request: KeyPressRequest):
    """Send key press to auth session"""
    from database import redis_client
    await redis_client.publish(f"auth_control:{session_id}", json.dumps({
        "action": "key",
        "key": request.key
    }))
    return {"status": "sent"}


@router.post("/{session_id}/complete")
async def complete_auth_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Complete auth session - save cookies and close browser.
    """
    session = auth_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    from database import redis_client
    
    # Request session data from worker
    await redis_client.publish(f"auth_control:{session_id}", json.dumps({
        "action": "complete"
    }))
    
    # Wait for session data (with timeout)
    for _ in range(30):  # 30 second timeout
        await asyncio.sleep(1)
        result = await redis_client.get(f"auth_result:{session_id}")
        if result:
            data = json.loads(result)
            
            if data.get("success"):
                # Save session to database
                session_data = json.dumps(data["session_data"]).encode()
                await db.execute(
                    text("""
                        UPDATE vk_accounts 
                        SET session_data_encrypted = :session_data,
                            status = 'active',
                            error_message = NULL,
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": session["vk_account_id"],
                        "session_data": session_data
                    }
                )
                await db.commit()
                
                # Cleanup
                del auth_sessions[session_id]
                await redis_client.delete(f"auth_result:{session_id}")
                
                return {"status": "completed", "message": "VK account authorized successfully"}
            else:
                raise HTTPException(status_code=400, detail=data.get("error", "Authorization failed"))
    
    raise HTTPException(status_code=408, detail="Authorization timeout")


@router.delete("/{session_id}")
async def cancel_auth_session(session_id: str):
    """Cancel and close auth session"""
    session = auth_sessions.pop(session_id, None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    from database import redis_client
    await redis_client.publish(f"auth_control:{session_id}", json.dumps({
        "action": "cancel"
    }))
    
    return {"status": "cancelled"}
