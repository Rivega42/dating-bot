import os
import httpx
from fastapi import FastAPI, Request

app = FastAPI()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    alerts = data.get("alerts", [])
    
    for alert in alerts:
        status = alert.get("status", "firing")
        name = alert.get("labels", {}).get("alertname", "Unknown")
        severity = alert.get("labels", {}).get("severity", "info")
        summary = alert.get("annotations", {}).get("summary", "")
        
        emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")
        status_emoji = "✅" if status == "resolved" else emoji
        
        msg = f"{status_emoji} *{name}*\n{summary}\nStatus: {status}"
        
        if TOKEN and CHAT_ID:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
                )
    
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
