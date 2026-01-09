"""
Тестовый скрипт для VK Dating (десктоп)
Использует селекторы из vk_selectors.py + playwright-stealth

Горячие клавиши VK:
  , (Б) - Дизлайк
  . (Ю) - Лайк
  ← → (стрелки) - Листать фото

Запуск: py test_vk_dating.py
"""
import asyncio
import os
import re
import json

from playwright.async_api import async_playwright, Page, FrameLocator
from vk_selectors import VKDatingSelectors as S, VKDatingHotkeys as K

# Опциональный stealth
try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False


class VKDatingTester:
    """Тестер VK Dating с поддержкой iframe"""
    
    def __init__(self, page: Page):
        self.page = page
        self.frame: FrameLocator | None = None
    
    async def detect_iframe(self) -> bool:
        """Определяет наличие iframe и получает FrameLocator"""
        try:
            iframes = await self.page.locator('iframe').count()
            if iframes > 0:
                # Ищем iframe с VK Dating app
                for i in range(iframes):
                    iframe = self.page.frame_locator(f'iframe >> nth={i}')
                    # Проверяем есть ли там кнопка лайка
                    try:
                        btn = iframe.locator('[aria-label="like"]')
                        if await btn.count() > 0:
                            self.frame = iframe
                            print(f"📦 Найден iframe VK Dating (#{i+1} из {iframes})")
                            return True
                    except:
                        pass
                # Если не нашли по aria-label, берём первый
                self.frame = self.page.frame_locator('iframe').first
                print(f"📦 Используем первый iframe ({iframes} шт)")
                return True
            else:
                print("📄 Работаем без iframe")
                return False
        except Exception as e:
            print(f"⚠️ Ошибка определения iframe: {e}")
            return False
    
    def get_locator(self, selector: str):
        """Возвращает локатор с учётом iframe"""
        if self.frame:
            return self.frame.locator(selector)
        return self.page.locator(selector)
    
    async def get_profile_info(self) -> dict:
        """Парсит информацию о текущем профиле"""
        info = {}
        
        try:
            # Пробуем разные селекторы для имени
            selectors_name = [
                S.PROFILE_NAME,  # .j2wk1ydI
                'h2',
                '[class*="Title"]',
                '[class*="name"]',
            ]
            
            for sel in selectors_name:
                try:
                    name_el = self.get_locator(sel)
                    count = await name_el.count()
                    if count > 0:
                        name_text = await name_el.first.inner_text()
                        if name_text and len(name_text) > 1:
                            match = re.search(r'([А-Яа-яЁёA-Za-z]+),?\s*(\d{2})?', name_text)
                            if match:
                                info['name'] = match.group(1)
                                info['age'] = match.group(2) if match.group(2) else '?'
                                break
                except:
                    pass
            
            # Био
            bio_el = self.get_locator(S.PROFILE_BIO)
            if await bio_el.count() > 0:
                info['bio'] = await bio_el.first.inner_text()
                
        except Exception as e:
            pass  # Тихо игнорируем
        
        return info
    
    async def action_like(self):
        """Ставит лайк"""
        await self.page.keyboard.press(K.LIKE)
        print("❤️ Лайк!")
        await asyncio.sleep(0.8)
    
    async def action_dislike(self):
        """Ставит дизлайк"""
        await self.page.keyboard.press(K.DISLIKE)
        print("❌ Дизлайк!")
        await asyncio.sleep(0.8)
    
    async def action_superlike(self):
        """Ставит суперлайк через кнопку"""
        try:
            # Пробуем разные селекторы
            selectors = [
                S.BTN_SUPERLIKE,
                '[aria-label="super-like"]',
                '[data-reaction="super-like"]',
                'button:has([class*="fire"])',
            ]
            
            for sel in selectors:
                btn = self.get_locator(sel)
                if await btn.count() > 0:
                    await btn.click()
                    await asyncio.sleep(0.5)
                    # Подтверждение
                    confirm = self.get_locator(S.BTN_SEND_SUPERLIKE)
                    if await confirm.count() > 0:
                        await confirm.click()
                    print("🔥 Суперлайк!")
                    return
            
            print("⚠️ Кнопка суперлайка не найдена")
        except Exception as e:
            print(f"⚠️ Ошибка суперлайка: {e}")
        await asyncio.sleep(0.8)
    
    async def photo_next(self):
        await self.page.keyboard.press(K.PHOTO_NEXT)
        print("➡️ Следующее фото")
    
    async def photo_prev(self):
        await self.page.keyboard.press(K.PHOTO_PREV)
        print("⬅️ Предыдущее фото")
    
    async def go_to_tab(self, tab_name: str):
        """Переходит на вкладку через iframe"""
        tab_names_ru = {
            'cards': 'Анкеты',
            'likes': 'Лайки',
            'chats': 'Чаты',
            'profile': 'Профиль',
        }
        
        if tab_name not in tab_names_ru:
            return
            
        ru_name = tab_names_ru[tab_name]
        
        try:
            # Пробуем через iframe
            selectors = [
                f'span:has-text("{ru_name}")',
                f'text="{ru_name}"',
                f'[class*="TabsItem"]:has-text("{ru_name}")',
                f'div:has-text("{ru_name}")',
            ]
            
            for sel in selectors:
                try:
                    tab = self.get_locator(sel)
                    count = await tab.count()
                    if count > 0:
                        await tab.first.click()
                        print(f"📑 {ru_name}")
                        await asyncio.sleep(1)
                        return
                except:
                    pass
            
            print(f"⚠️ Вкладка '{ru_name}' не найдена")
            
        except Exception as e:
            print(f"⚠️ Ошибка навигации: {e}")
    
    async def send_message(self, text: str):
        try:
            input_el = self.get_locator(S.CHAT_INPUT)
            if await input_el.count() > 0:
                await input_el.fill(text)
                await asyncio.sleep(0.3)
                
                send_btn = self.get_locator(S.CHAT_SEND_BTN)
                if await send_btn.count() > 0:
                    await send_btn.click()
                    print(f"📨 Отправлено: {text[:30]}...")
                else:
                    await self.page.keyboard.press('Enter')
                    print(f"📨 Отправлено (Enter): {text[:30]}...")
            else:
                print("⚠️ Поле ввода не найдено. Откройте чат.")
        except Exception as e:
            print(f"⚠️ Ошибка отправки: {e}")
    
    async def open_filters(self):
        try:
            selectors = [
                S.FILTER_BTN,
                '[class*="filter"]',
                'button:has([class*="tune"])',
            ]
            for sel in selectors:
                btn = self.get_locator(sel)
                if await btn.count() > 0:
                    await btn.click()
                    print("⚙️ Фильтры открыты")
                    await asyncio.sleep(0.5)
                    return
            print("⚠️ Кнопка фильтров не найдена")
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
    
    async def debug_dom(self):
        """Выводит отладочную информацию о DOM"""
        print("\n🔍 DEBUG DOM:")
        
        # Проверяем iframe
        iframes = await self.page.locator('iframe').count()
        print(f"   Iframes: {iframes}")
        
        if self.frame:
            # Проверяем ключевые элементы
            checks = [
                ('[aria-label="like"]', 'Кнопка лайк'),
                ('[aria-label="dislike"]', 'Кнопка дизлайк'),
                ('[aria-label="super-like"]', 'Кнопка суперлайк'),
                ('span:has-text("Анкеты")', 'Вкладка Анкеты'),
                ('span:has-text("Чаты")', 'Вкладка Чаты'),
                ('h2', 'Заголовок h2'),
                ('[class*="Title"]', 'Title класс'),
            ]
            
            for sel, name in checks:
                try:
                    el = self.get_locator(sel)
                    count = await el.count()
                    text = ""
                    if count > 0:
                        try:
                            text = await el.first.inner_text()
                            text = text[:30].replace('\n', ' ')
                        except:
                            pass
                    status = "✅" if count > 0 else "❌"
                    print(f"   {status} {name}: {count} шт {f'({text})' if text else ''}")
                except Exception as e:
                    print(f"   ❌ {name}: ошибка - {e}")


async def test_vk_dating():
    """Тестирует VK Dating с горячими клавишами и селекторами"""
    
    print("🚀 Запуск VK Dating...")
    
    session_path = os.path.join(os.path.dirname(__file__), "vk_session.json")
    
    if not os.path.exists(session_path):
        print("❌ Сначала запустите: py auth_chrome.py")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-web-security'
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            storage_state=session_path
        )
        
        page = await context.new_page()
        
        # Применяем stealth
        if HAS_STEALTH:
            await stealth_async(page)
            print("🛡️ Stealth режим активирован")
        else:
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US', 'en'] });
                window.chrome = { runtime: {} };
            """)
        
        print("📱 Открываем vk.com/dating...")
        await page.goto("https://vk.com/dating", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        print(f"📍 URL: {page.url}")
        
        tester = VKDatingTester(page)
        await tester.detect_iframe()
        
        await page.click('body')
        await asyncio.sleep(0.3)
        
        info = await tester.get_profile_info()
        if info and info.get('name'):
            print(f"👤 Текущая: {info.get('name')}, {info.get('age', '?')}")
        
        print("\n" + "="*50)
        print("🎮 УПРАВЛЕНИЕ")
        print("="*50)
        print("  l - Лайк       d - Дизлайк    s - Суперлайк")
        print("  a - ← Фото     f - Фото →     p - Профиль")
        print("  t - Вкладки    m - Сообщение  g - Фильтры")
        print("  x - DEBUG DOM  r - Обновить   q - Выход")
        print("="*50)
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'q':
                break
                
            elif cmd in ['l', 'ю', '.']:
                await tester.action_like()
                info = await tester.get_profile_info()
                if info.get('name'):
                    print(f"👤 Новая: {info.get('name')}, {info.get('age', '?')}")
                    
            elif cmd in ['d', 'б', ',']:
                await tester.action_dislike()
                info = await tester.get_profile_info()
                if info.get('name'):
                    print(f"👤 Новая: {info.get('name')}, {info.get('age', '?')}")
                    
            elif cmd == 's':
                await tester.action_superlike()
                    
            elif cmd in ['a', 'ф']:
                await tester.photo_prev()
                
            elif cmd in ['f', 'а']:
                await tester.photo_next()
                
            elif cmd == 'p':
                info = await tester.get_profile_info()
                if info and info.get('name'):
                    print(f"👤 {info.get('name')}, {info.get('age', '?')}")
                    if 'bio' in info:
                        print(f"   📝 {info['bio']}")
                else:
                    print("Профиль не найден (введи x для debug)")
                    
            elif cmd == 't':
                print("  1=Анкеты  2=Лайки  3=Чаты  4=Профиль")
                tab = input("  Выбор: ").strip()
                tabs_map = {'1': 'cards', '2': 'likes', '3': 'chats', '4': 'profile'}
                if tab in tabs_map:
                    await tester.go_to_tab(tabs_map[tab])
            
            elif cmd == 'm':
                msg = input("  Сообщение: ").strip()
                if msg:
                    await tester.send_message(msg)
            
            elif cmd == 'g':
                await tester.open_filters()
            
            elif cmd == 'x':
                await tester.debug_dom()
                    
            elif cmd == 'r':
                await page.reload()
                await asyncio.sleep(2)
                await tester.detect_iframe()
                print("🔄 Обновлено")
        
        storage = await context.storage_state()
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        print("✅ Готово!")


if __name__ == "__main__":
    asyncio.run(test_vk_dating())
