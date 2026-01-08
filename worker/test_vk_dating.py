"""
Тестовый скрипт для проверки VK Dating автоматизации
Запуск: py test_vk_dating.py
"""
import asyncio
import os
import re
import json
from datetime import datetime

from playwright.async_api import async_playwright


class VKSelectors:
    """Селекторы VK Dating (m.vk.com/dating)"""
    # Кнопки действий
    BTN_SKIP = 'button:has([class*="vkuiIcon--cancel_outline_28"])'
    BTN_LIKE = 'button:has([class*="vkuiIcon--like_outline_28"]):not([class*="TabbarItem"])'
    BTN_SUPERLIKE = 'button:has([class*="vkuiIcon--fire_alt_outline_28"])'
    
    # Данные профиля
    PROFILE_NAME = '[class*="vkuiTitle__level2"][class*="accent"]'
    PROFILE_INFO = '[class*="vkuiMiniInfoCell"]'
    PROFILE_TEXT = '[class*="vkuiText"], [class*="vkuiParagraph"]'
    
    # Чат
    CHAT_INPUT = '[class*="vkuiWriteBar__textarea"]'
    CHAT_SEND = '[class*="vkuiWriteBarIcon__modeSend"]'
    
    # Табы
    TAB_CARDS = '[class*="vkuiIcon--cards_2_outline_28"]'
    TAB_CHATS = '[class*="vkuiIcon--message_outline_28"]'
    TAB_PROFILE = '[class*="vkuiIcon--user_circle_outline_28"]'


async def test_vk_dating():
    """Тестирует подключение к VK Dating"""
    
    print("🚀 Запуск теста VK Dating...")
    
    # Проверяем наличие сессии
    session_path = os.path.join(os.path.dirname(__file__), "vk_session.json")
    
    if not os.path.exists(session_path):
        print("❌ Файл сессии не найден!")
        print("   Сначала запустите: py auth_vk.py")
        return
    
    print(f"✅ Сессия найдена: {session_path}")
    
    async with async_playwright() as p:
        # Запуск браузера
        print("🌐 Запуск браузера...")
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Загружаем сохранённую сессию
        context = await browser.new_context(
            viewport={"width": 414, "height": 896},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            storage_state=session_path
        )
        
        # Anti-detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = await context.new_page()
        
        # Переходим на Dating
        print("📱 Открываем m.vk.com/dating...")
        await page.goto("https://m.vk.com/dating", wait_until="domcontentloaded")
        
        # Ждём загрузки
        await asyncio.sleep(3)
        
        # Проверяем авторизацию
        current_url = page.url
        print(f"📍 Текущий URL: {current_url}")
        
        if "login" in current_url or "auth" in current_url:
            print("❌ Сессия истекла! Запустите: py auth_vk.py")
            await browser.close()
            return
        
        # Пробуем найти карточку
        print("🔍 Ищем карточку профиля...")
        try:
            name_el = page.locator(VKSelectors.PROFILE_NAME).first
            await name_el.wait_for(timeout=10000)
            name_text = await name_el.inner_text()
            print(f"✅ Найдена карточка: {name_text}")
            
            # Парсим имя и возраст
            match = re.match(r'^(.+?),\s*(\d+)$', name_text.strip())
            if match:
                print(f"   Имя: {match.group(1)}")
                print(f"   Возраст: {match.group(2)}")
            
            # Получаем дополнительную инфу
            info_els = page.locator(VKSelectors.PROFILE_INFO)
            count = await info_els.count()
            if count > 0:
                print(f"   Инфо:")
                for i in range(min(count, 3)):
                    text = await info_els.nth(i).inner_text()
                    print(f"     - {text}")
            
        except Exception as e:
            print(f"⚠️ Карточка не найдена: {e}")
            await page.screenshot(path="debug_screenshot.png")
            print("📸 Скриншот сохранён: debug_screenshot.png")
        
        # Тест кнопок
        print("\n🎮 Тест кнопок:")
        
        skip_btn = page.locator(VKSelectors.BTN_SKIP).first
        like_btn = page.locator(VKSelectors.BTN_LIKE).first
        
        skip_visible = await skip_btn.is_visible()
        like_visible = await like_btn.is_visible()
        
        print(f"   ❌ Skip: {'✅ видна' if skip_visible else '❌ не видна'}")
        print(f"   ❤️ Like: {'✅ видна' if like_visible else '❌ не видна'}")
        
        # Интерактивный режим
        print("\n" + "="*50)
        print("🎮 ИНТЕРАКТИВНЫЙ РЕЖИМ")
        print("="*50)
        print("Команды:")
        print("  l - лайк")
        print("  s - скип")
        print("  p - парсить карточку")
        print("  c - перейти в чаты")
        print("  q - выход")
        print("="*50)
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'q':
                break
                
            elif cmd == 'l':
                try:
                    await page.locator(VKSelectors.BTN_LIKE).first.click()
                    print("❤️ Лайк!")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 's':
                try:
                    await page.locator(VKSelectors.BTN_SKIP).first.click()
                    print("❌ Скип!")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 'p':
                try:
                    name_el = page.locator(VKSelectors.PROFILE_NAME).first
                    name_text = await name_el.inner_text()
                    print(f"👤 {name_text}")
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 'c':
                try:
                    await page.locator(VKSelectors.TAB_CHATS).click()
                    print("💬 Переход в чаты...")
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"Ошибка: {e}")
        
        # Сохраняем обновлённую сессию
        print("\n💾 Сохраняю сессию...")
        storage = await context.storage_state()
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        print("👋 Закрываем браузер...")
        await browser.close()
        print("✅ Тест завершён!")


if __name__ == "__main__":
    asyncio.run(test_vk_dating())
