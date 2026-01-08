#!/usr/bin/env python3
"""
VK Dating Research - используя реальный профиль Chrome

Запускает твой настоящий Chrome с сохранённым профилем,
чтобы обойти детекцию автоматизации.
"""

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Путь к Chrome профилю (Windows)
CHROME_USER_DATA = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"


async def main():
    console.print(Panel(
        "[bold blue]VK Dating Research[/bold blue]\n"
        "Используем реальный Chrome профиль",
        title="🔬 Research v2"
    ))
    
    # Проверяем что Chrome закрыт
    console.print("\n[yellow]⚠️  ВАЖНО: Закрой все окна Chrome перед продолжением![/yellow]")
    console.print("Нажми Enter когда Chrome закрыт...")
    input()
    
    async with async_playwright() as p:
        # Запускаем Chrome с реальным профилем
        console.print("\n🚀 Запускаю Chrome с твоим профилем...")
        
        try:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(CHROME_USER_DATA),
                channel="chrome",  # Используем установленный Chrome
                headless=False,
                args=[
                    "--start-maximized",
                    "--profile-directory=Default"  # Основной профиль
                ],
                viewport={"width": 1920, "height": 1080},
                timeout=60000  # 60 секунд на запуск
            )
            console.print("[green]✅ Chrome запущен![/green]")
        except Exception as e:
            console.print(f"[red]Ошибка запуска Chrome: {e}[/red]")
            console.print("\n[yellow]Попробуй:[/yellow]")
            console.print("1. Убедись что Chrome полностью закрыт (проверь Task Manager)")
            console.print("2. Или запусти скрипт от имени администратора")
            return
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # Переходим на VK Dating
        console.print("\n💕 Открываю VK Dating...")
        try:
            await page.goto("https://vk.com/dating", timeout=30000)
            console.print("[green]✅ Страница открыта![/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Таймаут загрузки, но продолжаем: {e}[/yellow]")
        
        console.print("⏳ Ожидание загрузки...")
        for i in range(10):
            await asyncio.sleep(2)
            console.print(f"   {(i+1)*2} сек...")
        
        # Скриншот
        console.print("\n📸 Делаю скриншот...")
        await page.screenshot(path=str(OUTPUT_DIR / "chrome_dating.png"))
        console.print(f"[green]✅ Скриншот: {OUTPUT_DIR / 'chrome_dating.png'}[/green]")
        
        # HTML
        console.print("📄 Сохраняю HTML...")
        html = await page.content()
        (OUTPUT_DIR / "chrome_dating.html").write_text(html, encoding="utf-8")
        console.print(f"[green]✅ HTML: {OUTPUT_DIR / 'chrome_dating.html'}[/green]")
        
        # Извлекаем классы
        console.print("\n📋 Извлечение CSS классов...")
        classes = await page.evaluate("""
            () => {
                const allElements = document.querySelectorAll('*');
                const classSet = new Set();
                allElements.forEach(el => {
                    el.classList.forEach(cls => classSet.add(cls));
                });
                return Array.from(classSet).sort();
            }
        """)
        
        # Фильтруем интересные
        interesting = [c for c in classes if any(kw in c.lower() for kw in 
            ["dating", "card", "profile", "user", "like", "skip", "swipe", 
             "photo", "chat", "message", "boost", "match", "action", "dialog",
             "recommendation", "stack"])]
        
        console.print(f"\n[cyan]Найдено {len(classes)} классов, {len(interesting)} интересных:[/cyan]")
        for cls in interesting[:30]:
            console.print(f"  .{cls}")
        
        # Сохраняем отчёт
        report = {
            "timestamp": datetime.now().isoformat(),
            "url": page.url,
            "all_classes": classes,
            "interesting_classes": interesting
        }
        
        report_path = OUTPUT_DIR / "chrome_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        console.print(f"\n💾 Отчёт: {report_path}")
        
        # Интерактивный режим
        console.print("\n" + "="*50)
        console.print("[bold cyan]🎮 ИНТЕРАКТИВНЫЙ РЕЖИМ[/bold cyan]")
        console.print("="*50)
        console.print("Команды:")
        console.print("  [green]s[/green] = скриншот")
        console.print("  [green]c[/green] = показать классы")
        console.print("  [green]h[/green] = сохранить HTML")
        console.print("  [green]q[/green] = выйти")
        console.print("\nКликай в браузере, потом вводи команды здесь")
        console.print("="*50)
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
            except EOFError:
                break
            
            if cmd == "q":
                break
            elif cmd == "s":
                ts = datetime.now().strftime("%H%M%S")
                path = OUTPUT_DIR / f"screen_{ts}.png"
                await page.screenshot(path=str(path))
                console.print(f"[green]📸 {path}[/green]")
            elif cmd == "h":
                ts = datetime.now().strftime("%H%M%S")
                path = OUTPUT_DIR / f"html_{ts}.html"
                html = await page.content()
                path.write_text(html, encoding="utf-8")
                console.print(f"[green]📄 {path}[/green]")
            elif cmd == "c":
                classes = await page.evaluate("""
                    () => {
                        const allElements = document.querySelectorAll('*');
                        const classSet = new Set();
                        allElements.forEach(el => {
                            el.classList.forEach(cls => classSet.add(cls));
                        });
                        return Array.from(classSet).sort();
                    }
                """)
                interesting = [c for c in classes if any(kw in c.lower() for kw in 
                    ["dating", "card", "profile", "user", "like", "skip", "photo", 
                     "chat", "message", "boost", "match", "action", "dialog"])]
                console.print(f"\n[cyan]Интересные классы ({len(interesting)}):[/cyan]")
                for cls in interesting[:40]:
                    console.print(f"  .{cls}")
            else:
                console.print("[yellow]Неизвестная команда. Используй: s, c, h, q[/yellow]")
        
        console.print("\n👋 Закрываю...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
