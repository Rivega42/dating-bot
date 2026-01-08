#!/usr/bin/env python3
"""
VK Dating Research - извлечение классов из iframe
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


async def extract_iframe_classes(page):
    """Извлекает классы из iframe Dating приложения"""
    console.print("\n🔍 Ищу iframe Dating приложения...")
    
    # Находим все iframes
    iframes = page.frames
    console.print(f"   Найдено {len(iframes)} фреймов")
    
    all_classes = []
    
    for i, frame in enumerate(iframes):
        url = frame.url
        console.print(f"   [{i}] {url[:80]}...")
        
        # Ищем iframe с Dating (vk-apps.com или dating)
        if "vk-apps" in url or "dating" in url or i > 0:
            console.print(f"   [green]→ Анализирую этот фрейм[/green]")
            
            try:
                classes = await frame.evaluate("""
                    () => {
                        const allElements = document.querySelectorAll('*');
                        const classSet = new Set();
                        allElements.forEach(el => {
                            el.classList.forEach(cls => classSet.add(cls));
                        });
                        return Array.from(classSet).sort();
                    }
                """)
                
                console.print(f"   Найдено {len(classes)} классов в этом фрейме")
                all_classes.extend(classes)
                
                # Сохраняем HTML фрейма
                try:
                    html = await frame.content()
                    frame_path = OUTPUT_DIR / f"iframe_{i}.html"
                    frame_path.write_text(html, encoding="utf-8")
                    console.print(f"   [green]✅ HTML сохранён: {frame_path}[/green]")
                except:
                    pass
                    
            except Exception as e:
                console.print(f"   [yellow]Ошибка: {e}[/yellow]")
    
    return list(set(all_classes))


async def main():
    console.print(Panel(
        "[bold blue]VK Dating Research[/bold blue]\n"
        "Извлечение классов из iframe",
        title="🔬 Research v4"
    ))
    
    chrome_user_data = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
    
    if not PLAYWRIGHT_PROFILE.exists():
        console.print("\n[yellow]📁 Создаю копию профиля Chrome...[/yellow]")
        console.print("[yellow]⚠️  Закрой Chrome![/yellow]")
        console.print("Нажми Enter когда Chrome закрыт...")
        input()
        
        try:
            PLAYWRIGHT_PROFILE.mkdir(parents=True, exist_ok=True)
            default_src = chrome_user_data / "Default"
            default_dst = PLAYWRIGHT_PROFILE / "Default"
            default_dst.mkdir(exist_ok=True)
            
            for f in ["Cookies", "Login Data", "Web Data", "Preferences"]:
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
            console.print(f"[red]Ошибка: {e}[/red]")
            return
    else:
        console.print(f"\n[green]✅ Используем существующий профиль[/green]")
    
    async with async_playwright() as p:
        console.print("\n🚀 Запускаю браузер...")
        
        try:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(PLAYWRIGHT_PROFILE),
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                viewport={"width": 1920, "height": 1080},
                locale="ru-RU",
                timezone_id="Europe/Moscow"
            )
            console.print("[green]✅ Браузер запущен![/green]")
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")
            return
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # VK
        console.print("\n🌐 Открываю VK...")
        try:
            await page.goto("https://vk.com", wait_until="domcontentloaded", timeout=30000)
        except:
            pass
        await asyncio.sleep(3)
        
        content = await page.content()
        if "Войти" in content or "Вход" in content:
            console.print("\n[yellow]⚠️  Залогинься в VK и нажми Enter...[/yellow]")
            input()
        
        # Dating
        console.print("\n💕 Открываю VK Dating...")
        try:
            await page.goto("https://vk.com/dating", wait_until="domcontentloaded", timeout=60000)
        except:
            pass
        
        console.print("⏳ Ожидание загрузки Dating приложения...")
        for i in range(20):
            await asyncio.sleep(2)
            console.print(f"   {(i+1)*2} сек...")
            
            # Проверяем есть ли iframe
            if len(page.frames) > 1:
                console.print(f"   [green]Найден iframe![/green]")
                break
        
        # Скриншот
        await page.screenshot(path=str(OUTPUT_DIR / "dating.png"))
        console.print(f"[green]📸 {OUTPUT_DIR / 'dating.png'}[/green]")
        
        # Извлекаем классы из ВСЕХ фреймов
        all_classes = await extract_iframe_classes(page)
        
        # Фильтруем интересные
        keywords = ["dating", "card", "profile", "user", "like", "skip", "swipe", 
                   "photo", "chat", "message", "boost", "match", "action", "dialog",
                   "recommendation", "stack", "avatar", "name", "age", "button",
                   "heart", "cross", "super", "gallery", "slide", "info", "bio",
                   "interest", "tag", "badge", "modal", "popup", "tab", "nav"]
        
        interesting = [c for c in all_classes if any(kw in c.lower() for kw in keywords)]
        
        console.print(f"\n[cyan]Всего классов: {len(all_classes)}[/cyan]")
        console.print(f"[cyan]Интересных: {len(interesting)}[/cyan]")
        
        if interesting:
            console.print("\n[bold]Интересные классы:[/bold]")
            for cls in sorted(interesting)[:50]:
                console.print(f"  .{cls}")
        
        # Сохраняем
        report = {
            "timestamp": datetime.now().isoformat(),
            "url": page.url,
            "frames_count": len(page.frames),
            "all_classes": sorted(all_classes),
            "interesting_classes": sorted(interesting)
        }
        (OUTPUT_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        console.print(f"\n[green]💾 {OUTPUT_DIR / 'report.json'}[/green]")
        
        # Интерактив
        console.print("\n" + "="*50)
        console.print("[bold cyan]🎮 ИНТЕРАКТИВНЫЙ РЕЖИМ[/bold cyan]")
        console.print("  [green]s[/green]=скриншот  [green]c[/green]=классы из iframe  [green]h[/green]=html  [green]q[/green]=выход")
        console.print("="*50)
        
        while True:
            try:
                cmd = input("\n> ").strip().lower()
            except:
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
                # Сохраняем HTML всех фреймов
                for i, frame in enumerate(page.frames):
                    try:
                        html = await frame.content()
                        path = OUTPUT_DIR / f"html_{ts}_frame{i}.html"
                        path.write_text(html, encoding="utf-8")
                        console.print(f"[green]📄 {path}[/green]")
                    except:
                        pass
            elif cmd == "c":
                classes = await extract_iframe_classes(page)
                interesting = [c for c in classes if any(kw in c.lower() for kw in keywords)]
                console.print(f"\n[cyan]Интересные классы ({len(interesting)}):[/cyan]")
                for cls in sorted(interesting)[:50]:
                    console.print(f"  .{cls}")
        
        console.print("\n👋 Закрываю...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
