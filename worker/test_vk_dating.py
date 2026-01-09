"""
Тестовый скрипт для VK Dating (десктоп)
Использует селекторы из vk_selectors.py

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
                self.frame = self.page.frame_locator('iframe').first
                print(f"📦 Найден iframe ({iframes} шт)")
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
            # Имя и возраст
            name_el = self.get_locator(S.PROFILE_NAME)
            if await name_el.count() > 0:
                name_text = await name_el.first.inner_text()
                match = re.search(r'([А-Яа-яЁёA-Za-z]+),?\s*(\d{2})?', name_text)
                if match:
                    info['name'] = match.group(1)
                    info['age'] = match.group(2) if match.group(2) else '?'
            
            # Био
            bio_el = self.get_locator(S.PROFILE_BIO)
            if await bio_el.count() > 0:
                info['bio'] = await bio_el.first.inner_text()
            
            # Что ищет
            looking_el = self.get_locator(S.PROFILE_LOOKING_FOR)
            if await looking_el.count() > 0:
                info['looking_for'] = await looking_el.first.inner_text()
                
        except Exception as e:
            print(f"⚠️ Ошибка парсинга: {e}")
        
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
            btn = self.get_locator(S.BTN_SUPERLIKE)
            if await btn.count() > 0:
                await btn.click()
                await asyncio.sleep(0.5)
                # Подтверждение в попапе
                confirm = self.get_locator(S.BTN_SEND_SUPERLIKE)
                if await confirm.count() > 0:
                    await confirm.click()
                print("🔥 Суперлайк!")
            else:
                print("⚠️ Кнопка суперлайка не найдена")
        except Exception as e:
            print(f"⚠️ Ошибка суперлайка: {e}")
        await asyncio.sleep(0.8)
    
    async def photo_next(self):
        """Следующее фото"""
        await self.page.keyboard.press(K.PHOTO_NEXT)
        print("➡️ Следующее фото")
    
    async def photo_prev(self):
        """Предыдущее фото"""
        await self.page.keyboard.press(K.PHOTO_PREV)
        print("⬅️ Предыдущее фото")
    
    async def go_to_tab(self, tab_name: str):
        """Переходит на вкладку"""
        tabs = {
            'cards': S.TAB_CARDS,
            'likes': S.TAB_LIKES,
            'chats': S.TAB_CHATS,
            'profile': S.TAB_PROFILE,
        }
        tab_names_ru = {
            'cards': 'Анкеты',
            'likes': 'Лайки',
            'chats': 'Чаты',
            'profile': 'Профиль',
        }
        
        if tab_name in tabs:
            try:
                tab = self.get_locator(tabs[tab_name])
                if await tab.count() > 0:
                    await tab.click()
                    print(f"📑 {tab_names_ru[tab_name]}")
                    await asyncio.sleep(1)
                else:
                    # Fallback на текст
                    await self.page.click(f'text="{tab_names_ru[tab_name]}"')
                    print(f"📑 {tab_names_ru[tab_name]} (text)")
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ Ошибка навигации: {e}")
    
    async def send_message(self, text: str):
        """Отправляет сообщение в открытом чате"""
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
                    # Enter как альтернатива
                    await self.page.keyboard.press('Enter')
                    print(f"📨 Отправлено (Enter): {text[:30]}...")
            else:
                print("⚠️ Поле ввода не найдено. Откройте чат.")
        except Exception as e:
            print(f"⚠️ Ошибка отправки: {e}")
    
    async def open_filters(self):
        """Открывает фильтры"""
        try:
            btn = self.get_locator(S.FILTER_BTN)
            if await btn.count() > 0:
                await btn.click()
                print("⚙️ Фильтры открыты")
                await asyncio.sleep(0.5)
            else:
                print("⚠️ Кнопка фильтров не найдена")
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")


async def test_vk_dating():
    """Тестирует VK Dating с горячими клавишами и селекторами"""
    
    print("🚀 Запуск VK Dating...")
    
    session_path = os.path.join(os.path.dirname(__file__), "vk_session.json")
    
    if not os.path.exists(session_path):
        print("❌ Сначала запустите: py auth_vk.py")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            storage_state=session_path
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = await context.new_page()
        
        print("📱 Открываем vk.com/dating...")
        await page.goto("https://vk.com/dating", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        print(f"📍 URL: {page.url}")
        
        # Инициализируем тестер
        tester = VKDatingTester(page)
        await tester.detect_iframe()
        
        # Активируем окно кликом
        await page.click('body')
        await asyncio.sleep(0.3)
        
        # Показываем текущий профиль
        info = await tester.get_profile_info()
        if info:
            name = info.get('name', '?')
            age = info.get('age', '?')
            print(f"👤 Текущая: {name}, {age}")
            if 'bio' in info:
                print(f"   📝 {info['bio'][:60]}...")
        
        print("\n" + "="*50)
        print("🎮 УПРАВЛЕНИЕ")
        print("="*50)
        print("  l (или ю/.) - Лайк")
        print("  d (или б/,) - Дизлайк")
        print("  s           - Суперлайк")
        print("  a (←)       - Предыдущее фото")
        print("  f (→)       - Следующее фото")
        print("  p           - Показать профиль")
        print("  t           - Вкладки (1-4)")
        print("  m           - Отправить сообщение")
        print("  g           - Фильтры")
        print("  r           - Обновить")
        print("  q           - Выход")
        print("="*50)
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'q':
                break
                
            elif cmd in ['l', 'ю', '.', '>']:
                await tester.action_like()
                info = await tester.get_profile_info()
                if info.get('name'):
                    print(f"👤 Новая: {info.get('name')}, {info.get('age', '?')}")
                    
            elif cmd in ['d', 'б', ',', '<']:
                await tester.action_dislike()
                info = await tester.get_profile_info()
                if info.get('name'):
                    print(f"👤 Новая: {info.get('name')}, {info.get('age', '?')}")
                    
            elif cmd == 's':
                await tester.action_superlike()
                    
            elif cmd in ['a', 'ф', 'left']:
                await tester.photo_prev()
                
            elif cmd in ['f', 'а', 'right']:
                await tester.photo_next()
                
            elif cmd == 'p':
                info = await tester.get_profile_info()
                if info:
                    print(f"👤 {info.get('name', '?')}, {info.get('age', '?')}")
                    if 'bio' in info:
                        print(f"   📝 {info['bio']}")
                    if 'looking_for' in info:
                        print(f"   🔍 {info['looking_for']}")
                else:
                    print("Профиль не найден")
                    
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
                    
            elif cmd == 'r':
                await page.reload()
                await asyncio.sleep(2)
                await tester.detect_iframe()
                print("🔄 Обновлено")
        
        # Сохраняем сессию
        storage = await context.storage_state()
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        print("✅ Готово!")


if __name__ == "__main__":
    asyncio.run(test_vk_dating())
