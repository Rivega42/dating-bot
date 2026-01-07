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
        
        return self.findings
    
    async def analyze_vk_dating(self):
        """Анализ VK Dating страницы (прямой DOM, не iframe)"""
        console.print("\n🎯 Анализ VK Dating...")
        
        selectors_to_check = {
            # Навигация Dating
            "navigation_tabs": [
                "[class*='DatingTabs']", "[class*='dating-tabs']",
                "[class*='TabsItem']", "[class*='tabs_item']",
                "[data-tab]", ".vkuiTabsItem",
                "a[href*='dating']", "[class*='Tabs']",
                "[class*='vkuiTabs']"
            ],
            # Карточки анкет
            "profile_cards": [
                "[class*='DatingCard']", "[class*='dating-card']",
                "[class*='DatingProfile']", "[class*='dating_profile']",
                "[class*='Recommendation']", "[class*='recommendation']",
                "[class*='StackCard']", "[class*='stack-card']",
                "[class*='UserCard']", "[class*='user-card']",
                "[class*='vkuiCard']"
            ],
            # Фото профиля
            "profile_photos": [
                "[class*='DatingPhoto']", "[class*='dating-photo']",
                "[class*='ProfilePhoto']", "[class*='profile_photo']",
                "[class*='Gallery']", ".vkuiImage",
                "img[class*='dating']", "img[class*='profile']",
                "[class*='Avatar']"
            ],
            # Информация профиля
            "profile_info": [
                "[class*='DatingName']", "[class*='dating-name']",
                "[class*='ProfileName']", "[class*='profile_name']",
                "[class*='DatingAge']", "[class*='dating-age']",
                "[class*='DatingCity']", "[class*='dating-city']",
                "[class*='DatingAbout']", "[class*='dating-about']",
                "[class*='DatingBio']", "[class*='dating-bio']"
            ],
            # Кнопки действий (лайк/скип)
            "action_buttons": [
                "[class*='DatingAction']", "[class*='dating-action']",
                "[class*='LikeButton']", "[class*='like-button']",
                "[class*='SkipButton']", "[class*='skip-button']",
                "[class*='DislikeButton']", "[class*='dislike-button']",
                "button[class*='dating']", "[class*='ActionButton']",
                "[class*='DatingLike']", "[class*='DatingSkip']",
                "[class*='DatingPass']"
            ],
            # Мэтчи
            "matches": [
                "[class*='Match']", "[class*='match']",
                "[class*='DatingMatch']", "[class*='dating-match']",
                "[class*='MutualLike']", "[class*='mutual']"
            ],
            # Чаты/Сообщения
            "chats": [
                "[class*='DatingChat']", "[class*='dating-chat']",
                "[class*='DatingDialog']", "[class*='dating-dialog']",
                "[class*='DatingMessage']", "[class*='dating-message']",
                "[class*='Conversation']", "[class*='conversation']"
            ],
            # Boost/Premium
            "boost": [
                "[class*='Boost']", "[class*='boost']",
                "[class*='Premium']", "[class*='premium']",
                "[class*='Super']", "[class*='super']",
                "[class*='DatingBoost']"
            ]
        }
        
        found_selectors = {}
        
        for category, selectors in selectors_to_check.items():
            found_selectors[category] = []
            for selector in selectors:
                try:
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        element = self.page.locator(selector).first
                        try:
                            text = await element.inner_text()
                            text = text[:50] + "..." if len(text) > 50 else text
                        except:
                            text = ""
                        
                        # Получаем реальный класс элемента
                        try:
                            class_attr = await element.get_attribute("class") or ""
                        except:
                            class_attr = ""
                        
                        found_selectors[category].append({
                            "selector": selector,
                            "count": count,
                            "sample_text": text.strip(),
                            "actual_class": class_attr[:100]
                        })
                except Exception as e:
                    pass
        
        self.findings["selectors"] = found_selectors
        return found_selectors
    
    async def extract_all_classes(self):
        """Извлекает все уникальные CSS классы со страницы"""
        console.print("\n📋 Извлечение всех CSS классов...")
        
        try:
            classes = await self.page.evaluate("""
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
        """Получает структуру DOM-дерева"""
        console.print(f"\n🌳 Построение DOM-дерева (глубина {max_depth})...")
        
        try:
            tree = await self.page.evaluate(f"""
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
                            children: children.slice(0, 10)
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
        # Запускаем браузер с anti-detection настройками
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check"
            ]
        )
        
        context_opts = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
            "color_scheme": "dark"
        }
        
        if use_saved and saved_session:
            context_opts["storage_state"] = saved_session
        
        context = await browser.new_context(**context_opts)
        
        # Добавляем скрипт для скрытия автоматизации
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Подменяем plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Подменяем languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });
            
            // Chrome runtime
            window.chrome = {
                runtime: {}
            };
        """)
        
        page = await context.new_page()
        
        # Переходим на VK
        console.print("\n🌐 Открываю vk.com...")
        await page.goto("https://vk.com")
        await asyncio.sleep(2)
        
        # Если нет сессии - ждём логина
        if not use_saved:
            await wait_for_login(page)
            await save_session(context)
        
        # Переходим на VK Dating
        console.print("\n💕 Открываю VK Dating...")
        await page.goto("https://vk.com/dating")
        
        console.print("⏳ Ожидание загрузки (15 сек)...")
        await asyncio.sleep(15)
        
        # Делаем скриншот чтобы увидеть что загрузилось
        await page.screenshot(path=str(OUTPUT_DIR / "dating_initial.png"))
        console.print(f"📸 Скриншот: {OUTPUT_DIR / 'dating_initial.png'}")
        
        # Исследование
        researcher = DOMResearcher(page)
        
        # Анализ страницы
        await researcher.analyze_page("vk_dating")
        
        # Анализ VK Dating
        await researcher.analyze_vk_dating()
        
        # Извлечение классов
        await researcher.extract_all_classes()
        
        # DOM дерево
        await researcher.get_dom_tree()
        
        # Сохранение и вывод
        researcher.save_report()
        researcher.print_summary()
        
        # Интерактивный режим
        console.print("\n[bold cyan]🎮 Интерактивный режим[/bold cyan]")
        console.print("Команды: [green]screenshot[/green], [green]analyze[/green], [green]classes[/green], [green]tabs[/green], [green]quit[/green]")
        console.print("Можешь кликать в браузере и затем делать screenshot/analyze")
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == "quit" or cmd == "q":
                break
            elif cmd == "screenshot" or cmd == "s":
                ts = datetime.now().strftime("%H%M%S")
                await researcher.analyze_page(f"interactive_{ts}")
            elif cmd == "analyze" or cmd == "a":
                await researcher.analyze_vk_dating()
                researcher.print_summary()
            elif cmd == "classes" or cmd == "c":
                classes = await researcher.extract_all_classes()
                # Фильтруем интересные классы
                interesting = [c for c in classes if any(kw in c.lower() for kw in 
                    ["dating", "card", "profile", "user", "like", "skip", "swipe", "photo", "chat", "message", "boost", "match", "action"])]
                console.print("\n[cyan]Интересные классы:[/cyan]")
                for cls in interesting[:50]:
                    console.print(f"  .{cls}")
            elif cmd == "tabs":
                # Попробуем кликнуть на разные табы
                console.print("Пробую найти табы...")
                tabs = await page.locator("[class*='Tab'], [class*='tab'], [data-tab]").all()
                console.print(f"Найдено {len(tabs)} табов")
                for i, tab in enumerate(tabs[:10]):
                    try:
                        text = await tab.inner_text()
                        console.print(f"  [{i}] {text[:30]}")
                    except:
                        pass
            elif cmd == "save":
                researcher.save_report(f"report_{datetime.now().strftime('%H%M%S')}.json")
            else:
                console.print("Неизвестная команда")
        
        console.print("\n👋 Завершение...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
