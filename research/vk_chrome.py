#!/usr/bin/env python3
"""
VK Dating Research - используя копию профиля Chrome
"""

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from rich.console import Console
from rich.panel import Panel

console = Console()

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

PLAYWRIGHT_PROFILE = Path("output/chrome_profile")


async def main():
    console.print(Panel(
        "[bold blue]VK Dating Research[/bold blue]\n"
        "Копируем профиль Chrome для исследования",
        title="🔬 Research v3"
    ))
    
    chrome_user_data = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
    
    if not PLAYWRIGHT_PROFILE.exists():
        console.print("\n[yellow]📁 Создаю копию профиля Chrome...[/yellow]")
        console.print("[yellow]⚠️  ВАЖНО: Закрой Chrome перед копированием![/yellow]")
        console.print("Нажми Enter когда Chrome закрыт...")
        input()
        
        try:
            PLAYWRIGHT_PROFILE.mkdir(parents=True, exist_ok=True)
            default_src = chrome_user_data / "Default"
            default_dst = PLAYWRIGHT_PROFILE / "Default"
            default_dst.mkdir(exist_ok=True)
            
            files_to_copy = ["Cookies", "Login Data", "Web Data", "Preferences", "Secure Preferences"]
            for f in files_to_copy:
                src = default_src / f
                if src.exists():
                    shutil.copy2(src, default_dst / f)
                    console.print(f"  ✅ {f}")
            
            for folder in ["Local Storage", "Session Storage", "IndexedDB"]:
                src = default_src / folder
                if src.exists():
                    shutil.copytree(src, default_dst / folder, dirs_exist_ok=True)
                    console.print(f"  ✅ {folder}")
                
            console.print("[green]✅ Профиль скопирован![/green]")
            
        except Exception as e:
            console.print(f"[red]Ошибка копирования: {e}[/red]")
            return
    else:
        console.print(f"\n[green]✅ Используем существующий профиль[/green]")
    
    async with async_playwright() as p:
        console.print("\n🚀 Запускаю браузер...")
        
        try:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(PLAYWRIGHT_PROFILE),
                headless=False,
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                ],
                viewport={"width": 1920, "height": 1080},
                locale="ru-RU",
                timezone_id="Europe/Moscow"
            )
            console.print("[green]✅ Браузер запущен![/green]")
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")
            return
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # Переходим на VK
        console.print("\n🌐 Открываю VK...")
        try:
            await page.goto("https://vk.com", wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            console.print(f"[yellow]⚠️ {e}[/yellow]")
        
        await asyncio.sleep(3)
        
        # Проверяем залогинены ли
        content = await page.content()
        if "Войти" in content or "Вход" in content:
            console.print("\n[yellow]⚠️  Нужна авторизация![/yellow]")
            console.print("Залогинься в VK в открытом браузере и нажми Enter...")
            input()
            await asyncio.sleep(2)
        
        # Переходим на Dating с обработкой редиректов
        console.print("\n💕 Открываю VK Dating...")
        try:
            await page.goto("https://vk.com/dating", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            console.print(f"[yellow]⚠️ Редирект или таймаут: {type(e).__name__}[/yellow]")
            console.print("Ждём завершения загрузки...")
        
        # Ждём пока страница стабилизируется
        console.print("⏳ Ожидание загрузки...")
        for i in range(15):
            await asyncio.sleep(2)
            console.print(f"   {(i+1)*2} сек... URL: {page.url[:50]}...")
            if "dating" in page.url:
                console.print("[green]✅ VK Dating загружен![/green]")
                break
        
        # Скриншот
        console.print("\n📸 Делаю скриншот...")
        await page.screenshot(path=str(OUTPUT_DIR / "dating.png"))
        console.print(f"[green]✅ {OUTPUT_DIR / 'dating.png'}[/green]")
        
        # HTML
        html = await page.content()
        (OUTPUT_DIR / "dating.html").write_text(html, encoding="utf-8")
        console.print(f"[green]✅ {OUTPUT_DIR / 'dating.html'}[/green]")
        
        # Классы
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
        
        interesting = [c for c in classes if any(kw in c.lower() for kw in 
            ["dating", "card", "profile", "user", "like", "skip", "swipe", 
             "photo", "chat", "message", "boost", "match", "action", "dialog",
             "recommendation", "stack", "avatar", "name", "age"])]
        
        console.print(f"\n[cyan]Найдено {len(classes)} классов, {len(interesting)} интересных:[/cyan]")
        for cls in interesting[:30]:
            console.print(f"  .{cls}")
        
        # Сохраняем
        report = {
            "timestamp": datetime.now().isoformat(),
            "url": page.url,
            "all_classes": classes,
            "interesting_classes": interesting
        }
        (OUTPUT_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        
        # Интерактив
        console.print("\n" + "="*50)
        console.print("[bold cyan]🎮 ИНТЕРАКТИВНЫЙ РЕЖИМ[/bold cyan]")
        console.print("  [green]s[/green]=скриншот  [green]c[/green]=классы  [green]h[/green]=html  [green]q[/green]=выход")
        console.print("="*50)
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
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
                     "chat", "message", "boost", "match", "action", "dialog", "avatar", "name"])]
                console.print(f"\n[cyan]Интересные классы ({len(interesting)}):[/cyan]")
                for cls in interesting[:40]:
                    console.print(f"  .{cls}")
        
        console.print("\n👋 Закрываю...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
