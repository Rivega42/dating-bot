#!/usr/bin/env python3
"""
Мониторинг сетевых запросов Mini App
Полезно для понимания API endpoints
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from rich.console import Console
from rich.table import Table

console = Console()

class NetworkMonitor:
    def __init__(self):
        self.requests = []
    
    def on_request(self, request):
        if "api" in request.url or "method" in request.url:
            self.requests.append({
                "time": datetime.now().isoformat(),
                "method": request.method,
                "url": request.url,
                "type": "request"
            })
            console.print(f"[cyan]→ {request.method}[/cyan] {request.url[:80]}")
    
    def on_response(self, response):
        if "api" in response.url or "method" in response.url:
            self.requests.append({
                "time": datetime.now().isoformat(),
                "status": response.status,
                "url": response.url,
                "type": "response"
            })
            color = "green" if response.status == 200 else "red"
            console.print(f"[{color}]← {response.status}[/{color}] {response.url[:80]}")
    
    def save(self, filename: str):
        path = Path("output") / filename
        path.write_text(json.dumps(self.requests, indent=2, ensure_ascii=False))
        console.print(f"💾 Сохранено: {path}")


async def main():
    session_path = Path("output/session.json")
    if not session_path.exists():
        console.print("[red]❌ Сначала запусти vk_research.py и залогинься[/red]")
        return
    
    session = json.loads(session_path.read_text())
    app_id = input("App ID (по умолчанию 6682509): ").strip() or "6682509"
    
    monitor = NetworkMonitor()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=session,
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # Подписываемся на события
        page.on("request", monitor.on_request)
        page.on("response", monitor.on_response)
        
        console.print(f"\n🔍 Мониторинг сети для app{app_id}")
        console.print("Делай действия в браузере, запросы будут логироваться\n")
        
        await page.goto(f"https://vk.com/app{app_id}")
        
        console.print("\n[yellow]Нажми Enter чтобы сохранить лог и выйти[/yellow]")
        input()
        
        monitor.save(f"network_log_{app_id}.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
