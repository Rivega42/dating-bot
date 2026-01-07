#!/usr/bin/env python3
"""
VK Dating DOM Research Tool

Запускает браузер, позволяет залогиниться вручную,
затем исследует DOM-структуру VK Знакомства.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Frame
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# VK Dating App IDs для исследования
VK_DATING_APPS = {
    "vk_dating": "6682509",      # VK Знакомства
    "lovoo_vk": "7933647",       # Lovoo
    "mamba": "7247498",          # Mamba  
}


class DOMResearcher:
    def __init__(self, page: Page):
        self.page = page
        self.findings = {
            "timestamp": datetime.now().isoformat(),
            "url": "",
            "selectors": {},
            "elements": [],
            "iframe_info": None
        }
    
    async def analyze_page(self, name: str):
        """Полный анализ текущей страницы"""
        self.findings["url"] = self.page.url
        
        # Скриншот
        screenshot_path = OUTPUT_DIR / f"screenshot_{name}.png"
        await self.page.screenshot(path=str(screenshot_path), full_page=True)
        console.print(f"📸 Скриншот: {screenshot_path}")
        
        # HTML дамп
        html_path = OUTPUT_DIR / f"page_{name}.html"
        html = await self.page.content()
        html_path.write_text(html, encoding="utf-8")
        console.print(f"📄 HTML: {html_path}")
        
        # Поиск iframe (VK mini apps загружаются в iframe)
        await self._analyze_iframes()
        
        return self.findings
    
    async def _analyze_iframes(self):
        """Анализ iframe на странице"""
        iframes = await self.page.query_selector_all("iframe")
        console.print(f"\n🔍 Найдено iframe: {len(iframes)}")
        
        for i, iframe in enumerate(iframes):
            src = await iframe.get_attribute("src") or "no-src"
            name = await iframe.get_attribute("name") or "no-name"
            console.print(f"  [{i}] name={name}, src={src[:80]}..." if len(src) > 80 else f"  [{i}] name={name}, src={src}")
            
            self.findings["iframe_info"] = {
                "count": len(iframes),
                "main_src": src
            }
    
    async def analyze_mini_app_frame(self):
        """Анализ содержимого Mini App внутри iframe"""
        console.print("\n🎯 Анализ Mini App iframe...")
        
        # Ждём загрузки iframe
        try:
            await self.page.wait_for_selector("iframe", timeout=10000)
        except:
            console.print("[red]❌ iframe не найден[/red]")
            return None
        
        frame = self.page.frame_locator("iframe").first
        
        # Пробуем найти типичные элементы dating-приложений
        selectors_to_check = {
            # Карточки профилей
            "card_containers": [
                ".card", ".profile-card", ".user-card", 
                "[class*='card']", "[class*='Card']",
                ".swipe-card", ".dating-card",
                "[class*='profile']", "[class*='Profile']",
                ".recommendation", "[class*='recommendation']"
            ],
            # Кнопки действий
            "action_buttons": [
                ".like-btn", ".dislike-btn", ".skip-btn",
                "[class*='like']", "[class*='Like']",
                "[class*='skip']", "[class*='Skip']",
                "[class*='pass']", "[class*='Pass']",
                "button[class*='action']",
                ".btn-heart", ".btn-cross",
                "[data-action]"
            ],
            # Информация о пользователе
            "user_info": [
                ".name", ".username", ".user-name",
                "[class*='name']", "[class*='Name']",
                ".age", "[class*='age']", "[class*='Age']",
                ".bio", ".about", ".description",
                "[class*='bio']", "[class*='about']",
                ".city", ".location", "[class*='location']"
            ],
            # Фотографии
            "photos": [
                ".photo", ".avatar", ".user-photo",
                "[class*='photo']", "[class*='Photo']",
                "[class*='image']", "[class*='Image']",
                "img[class*='profile']", "img[class*='avatar']"
            ],
            # Навигация/табы
            "navigation": [
                ".tab", ".tabs", ".nav",
                "[class*='tab']", "[class*='Tab']",
                "[class*='nav']", "[class*='Nav']",
                ".menu", "[class*='menu']"
            ],
            # Сообщения/чаты
            "messaging": [
                ".chat", ".message", ".dialog",
                "[class*='chat']", "[class*='Chat']",
                "[class*='message']", "[class*='Message']",
                "[class*='dialog']", "[class*='Dialog']",
                ".inbox", "[class*='inbox']"
            ],
            # Boost/Premium
            "boost_premium": [
                ".boost", "[class*='boost']", "[class*='Boost']",
                ".premium", "[class*='premium']", "[class*='Premium']",
                ".vip", "[class*='vip']", "[class*='Vip']",
                "[class*='super']", "[class*='Super']"
            ]
        }
        
        found_selectors = {}
        
        for category, selectors in selectors_to_check.items():
            found_selectors[category] = []
            for selector in selectors:
                try:
                    count = await frame.locator(selector).count()
                    if count > 0:
                        # Получаем дополнительную информацию
                        element = frame.locator(selector).first
                        try:
                            text = await element.inner_text()
                            text = text[:50] + "..." if len(text) > 50 else text
                        except:
                            text = ""
                        
                        found_selectors[category].append({
                            "selector": selector,
                            "count": count,
                            "sample_text": text.strip()
                        })
                except Exception as e:
                    pass
        
        self.findings["selectors"] = found_selectors
        return found_selectors
    
    async def extract_all_classes(self):
        """Извлекает все уникальные CSS классы из iframe"""
        console.print("\n📋 Извлечение всех CSS классов...")
        
        try:
            # Получаем frame
            frame_element = await self.page.query_selector("iframe")
            if not frame_element:
                return []
            
            frame = await frame_element.content_frame()
            if not frame:
                return []
            
            # Извлекаем все классы
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
            
            self.findings["all_classes"] = classes
            console.print(f"   Найдено {len(classes)} уникальных классов")
            return classes
            
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")
            return []
    
    async def get_dom_tree(self, max_depth: int = 4):
        """Получает структуру DOM-дерева из iframe"""
        console.print(f"\n🌳 Построение DOM-дерева (глубина {max_depth})...")
        
        try:
            frame_element = await self.page.query_selector("iframe")
            if not frame_element:
                return None
            
            frame = await frame_element.content_frame()
            if not frame:
                return None
            
            tree = await frame.evaluate(f"""
                (maxDepth) => {{
                    function buildTree(element, depth) {{
                        if (depth > maxDepth) return null;
                        
                        const children = [];
                        for (const child of element.children) {{
                            const childTree = buildTree(child, depth + 1);
                            if (childTree) children.push(childTree);
                        }}
                        
                        return {{
                            tag: element.tagName.toLowerCase(),
                            id: element.id || null,
                            classes: Array.from(element.classList),
                            childCount: element.children.length,
                            children: children.slice(0, 10)  // Ограничиваем
                        }};
                    }}
                    return buildTree(document.body, 0);
                }}
            """, max_depth)
            
            self.findings["dom_tree"] = tree
            return tree
            
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")
            return None
    
    def save_report(self, filename: str = "selectors_report.json"):
        """Сохраняет отчёт в файл"""
        path = OUTPUT_DIR / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.findings, f, ensure_ascii=False, indent=2)
        console.print(f"\n💾 Отчёт сохранён: {path}")
    
    def print_summary(self):
        """Выводит красивую таблицу с результатами"""
        table = Table(title="🔍 Найденные селекторы")
        table.add_column("Категория", style="cyan")
        table.add_column("Селектор", style="green")
        table.add_column("Кол-во", justify="right", style="yellow")
        table.add_column("Пример текста", style="dim")
        
        for category, items in self.findings.get("selectors", {}).items():
            for item in items:
                table.add_row(
                    category,
                    item["selector"],
                    str(item["count"]),
                    item.get("sample_text", "")[:30]
                )
        
        console.print(table)


async def wait_for_login(page: Page):
    """Ждёт пока пользователь залогинится"""
    console.print(Panel(
        "[bold yellow]👆 Залогинься в VK в открытом браузере[/bold yellow]\n"
        "После успешного входа нажми [bold green]Enter[/bold green] здесь",
        title="Авторизация"
    ))
    input()
    
    # Проверяем что залогинились
    try:
        await page.wait_for_selector("#top_profile_link, .TopNavBtn, .top_profile_name", timeout=5000)
        console.print("[green]✅ Успешная авторизация![/green]")
        return True
    except:
        console.print("[yellow]⚠️ Не уверен в авторизации, продолжаем...[/yellow]")
        return True


async def save_session(context, path: str = "output/session.json"):
    """Сохраняет сессию для повторного использования"""
    storage = await context.storage_state()
    Path(path).write_text(json.dumps(storage, indent=2))
    console.print(f"💾 Сессия сохранена: {path}")


async def load_session(path: str = "output/session.json"):
    """Загружает сохранённую сессию"""
    if Path(path).exists():
        return json.loads(Path(path).read_text())
    return None


async def main():
    console.print(Panel(
        "[bold blue]VK Dating DOM Research Tool[/bold blue]\n"
        "Исследование структуры VK Знакомства для автоматизации",
        title="🔬 Research"
    ))
    
    # Проверяем сохранённую сессию
    saved_session = await load_session()
    use_saved = False
    if saved_session:
        console.print("[cyan]Найдена сохранённая сессия. Использовать? (y/n)[/cyan]")
        use_saved = input().lower().strip() == "y"
    
    async with async_playwright() as p:
        # Запускаем браузер в видимом режиме
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        
        context_opts = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        if use_saved and saved_session:
            context_opts["storage_state"] = saved_session
        
        context = await browser.new_context(**context_opts)
        page = await context.new_page()
        
        # Переходим на VK
        console.print("\n🌐 Открываю vk.com...")
        await page.goto("https://vk.com")
        await asyncio.sleep(2)
        
        # Если нет сессии - ждём логина
        if not use_saved:
            await wait_for_login(page)
            await save_session(context)
        
        # Выбор приложения для исследования
        console.print("\n[cyan]Выбери приложение для исследования:[/cyan]")
        for i, (name, app_id) in enumerate(VK_DATING_APPS.items(), 1):
            console.print(f"  {i}. {name} (app{app_id})")
        console.print(f"  0. Ввести свой app_id")
        
        choice = input("\nНомер: ").strip()
        
        if choice == "0":
            app_id = input("Введи app_id: ").strip()
        else:
            app_id = list(VK_DATING_APPS.values())[int(choice) - 1]
        
        # Переходим на приложение
        app_url = f"https://vk.com/app{app_id}"
        console.print(f"\n🎮 Открываю {app_url}...")
        await page.goto(app_url)
        
        # Ждём загрузки
        console.print("⏳ Ожидание загрузки приложения (10 сек)...")
        await asyncio.sleep(10)
        
        # Исследование
        researcher = DOMResearcher(page)
        
        # Анализ страницы
        await researcher.analyze_page(f"app_{app_id}")
        
        # Анализ iframe
        await researcher.analyze_mini_app_frame()
        
        # Извлечение классов
        await researcher.extract_all_classes()
        
        # DOM дерево
        await researcher.get_dom_tree()
        
        # Сохранение и вывод
        researcher.save_report()
        researcher.print_summary()
        
        # Интерактивный режим
        console.print("\n[bold cyan]🎮 Интерактивный режим[/bold cyan]")
        console.print("Команды: [green]screenshot[/green], [green]analyze[/green], [green]classes[/green], [green]quit[/green]")
        console.print("Можешь кликать в браузере и затем делать screenshot/analyze")
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == "quit" or cmd == "q":
                break
            elif cmd == "screenshot" or cmd == "s":
                ts = datetime.now().strftime("%H%M%S")
                await researcher.analyze_page(f"interactive_{ts}")
            elif cmd == "analyze" or cmd == "a":
                await researcher.analyze_mini_app_frame()
                researcher.print_summary()
            elif cmd == "classes" or cmd == "c":
                classes = await researcher.extract_all_classes()
                # Фильтруем интересные классы
                interesting = [c for c in classes if any(kw in c.lower() for kw in 
                    ["card", "profile", "user", "like", "skip", "swipe", "photo", "chat", "message", "boost"])]
                console.print("\n[cyan]Интересные классы:[/cyan]")
                for cls in interesting:
                    console.print(f"  .{cls}")
            elif cmd == "save":
                researcher.save_report(f"report_{datetime.now().strftime('%H%M%S')}.json")
            else:
                console.print("Неизвестная команда")
        
        console.print("\n👋 Завершение...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
