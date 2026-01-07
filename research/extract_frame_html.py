#!/usr/bin/env python3
"""
Извлекает полный HTML из iframe Mini App
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from rich.console import Console

console = Console()

async def main():
    session_path = Path("output/session.json")
    if not session_path.exists():
        console.print("[red]❌ Сначала запусти vk_research.py и залогинься[/red]")
        return
    
    session = json.loads(session_path.read_text())
    
    app_id = input("App ID (по умолчанию 6682509): ").strip() or "6682509"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=session,
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        console.print(f"🌐 Открываю https://vk.com/app{app_id}...")
        await page.goto(f"https://vk.com/app{app_id}")
        
        console.print("⏳ Ждём загрузки (15 сек)...")
        await asyncio.sleep(15)
        
        # Получаем iframe
        frame_element = await page.query_selector("iframe")
        if not frame_element:
            console.print("[red]❌ iframe не найден[/red]")
            return
        
        frame = await frame_element.content_frame()
        if not frame:
            console.print("[red]❌ Не удалось получить content_frame[/red]")
            return
        
        # Извлекаем HTML
        html = await frame.content()
        
        output_path = Path(f"output/frame_html_{app_id}.html")
        output_path.write_text(html, encoding="utf-8")
        console.print(f"[green]✅ HTML сохранён: {output_path}[/green]")
        console.print(f"   Размер: {len(html)} символов")
        
        # Извлекаем все атрибуты data-*
        data_attrs = await frame.evaluate("""
            () => {
                const elements = document.querySelectorAll('*');
                const attrs = new Set();
                elements.forEach(el => {
                    for (const attr of el.attributes) {
                        if (attr.name.startsWith('data-')) {
                            attrs.add(`${attr.name}="${attr.value.substring(0, 50)}"`);
                        }
                    }
                });
                return Array.from(attrs).sort();
            }
        """)
        
        console.print(f"\n[cyan]Data-атрибуты ({len(data_attrs)}):[/cyan]")
        for attr in data_attrs[:30]:
            console.print(f"  {attr}")
        
        input("\nНажми Enter для завершения...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
