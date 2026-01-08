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
    # Кнопки действий - ищем по иконкам
    BTN_SKIP = 'button:has([class*="cancel_outline"]), button:has([class*="Icon--cancel"])'
    BTN_LIKE = 'button:has([class*="like_outline"]):not([class*="TabbarItem"]), button:has([class*="heart"]):not([class*="TabbarItem"])'
    BTN_SUPERLIKE = 'button:has([class*="fire"]), button:has([class*="flame"])'
    
    # Данные профиля - более широкие селекторы
    PROFILE_NAME = '[class*="Title"][class*="accent"], [class*="Title"][class*="level-2"]'
    PROFILE_INFO = '[class*="MiniInfoCell"], [class*="Subhead"]'
    
    # Табы - по тексту
    TAB_CHATS = 'text=Чаты'
    TAB_PROFILE = 'text=Профиль'
    TAB_CARDS = 'text=Анкеты'
    
    # Кнопка входа в Dating
    BTN_ENTER_DATING = 'button:has-text("Войти"), button:has-text("Начать")'


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
        page.set_default_timeout(5000)  # Уменьшаем таймаут для быстрого фидбека
        
        # Переходим на Dating
        print("📱 Открываем m.vk.com/dating...")
        await page.goto("https://m.vk.com/dating", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # Проверяем нужен ли вход в Dating
        current_url = page.url
        print(f"📍 Текущий URL: {current_url}")
        
        # Ищем кнопку входа
        enter_btn = page.locator(VKSelectors.BTN_ENTER_DATING).first
        if await enter_btn.is_visible():
            print("🔑 Требуется вход в Dating...")
            await enter_btn.click()
            print("⏳ Ждём загрузки анкет...")
            await asyncio.sleep(3)
        
        # Ждём появления кнопок действий
        print("🔍 Ищем кнопки...")
        await asyncio.sleep(2)
        
        # Проверяем кнопки
        print("\n🎮 Тест кнопок:")
        
        # Пробуем разные селекторы для skip
        skip_selectors = [
            'button:has([class*="cancel"])',
            '[class*="ActionButton"]:first-child',
            'button >> nth=0'
        ]
        
        skip_found = False
        for sel in skip_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    print(f"   ❌ Skip: ✅ найдена ({sel})")
                    skip_found = True
                    VKSelectors.BTN_SKIP = sel
                    break
            except:
                pass
        if not skip_found:
            print("   ❌ Skip: не найдена")
        
        # Пробуем разные селекторы для like
        like_selectors = [
            'button:has([class*="like"])',
            'button:has([class*="heart"])',
            '[class*="ActionButton"]:last-child',
            'button >> nth=-1'
        ]
        
        like_found = False
        for sel in like_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    print(f"   ❤️ Like: ✅ найдена ({sel})")
                    like_found = True
                    VKSelectors.BTN_LIKE = sel
                    break
            except:
                pass
        if not like_found:
            print("   ❤️ Like: не найдена")
        
        # Ищем имя профиля
        print("\n🔍 Ищем имя профиля...")
        name_found = False
        name_text = ""
        
        # Ищем текст с паттерном "Имя, возраст"
        all_text = await page.locator('body').inner_text()
        match = re.search(r'([А-Яа-яЁё]+),\s*(\d{2})', all_text)
        if match:
            name_text = f"{match.group(1)}, {match.group(2)}"
            print(f"   👤 Найдено: {name_text}")
            name_found = True
        
        # Интерактивный режим
        print("\n" + "="*50)
        print("🎮 ИНТЕРАКТИВНЫЙ РЕЖИМ")
        print("="*50)
        print("Команды:")
        print("  l - лайк (клик по правой кнопке)")
        print("  s - скип (клик по левой кнопке)")
        print("  p - парсить карточку")
        print("  c - перейти в чаты")
        print("  d - debug (показать HTML)")
        print("  q - выход")
        print("="*50)
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'q':
                break
                
            elif cmd == 'l':
                try:
                    # Ищем кнопку лайка (обычно справа, фиолетовая)
                    buttons = page.locator('button').all()
                    btns = await buttons
                    if len(btns) >= 3:
                        await btns[-1].click()  # Последняя кнопка - лайк
                        print("❤️ Лайк!")
                    else:
                        # Пробуем по цвету/позиции
                        await page.evaluate('''
                            document.querySelectorAll('button').forEach(b => {
                                if (b.querySelector('[class*="like"]') || b.querySelector('[class*="heart"]')) {
                                    b.click();
                                }
                            });
                        ''')
                        print("❤️ Лайк (через JS)!")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 's':
                try:
                    # Ищем кнопку скипа (обычно слева, красная)
                    buttons = page.locator('button').all()
                    btns = await buttons
                    if len(btns) >= 3:
                        await btns[-3].click()  # Третья с конца - скип
                        print("❌ Скип!")
                    else:
                        await page.evaluate('''
                            document.querySelectorAll('button').forEach(b => {
                                if (b.querySelector('[class*="cancel"]') || b.querySelector('[class*="close"]')) {
                                    b.click();
                                }
                            });
                        ''')
                        print("❌ Скип (через JS)!")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 'p':
                try:
                    all_text = await page.locator('body').inner_text()
                    match = re.search(r'([А-Яа-яЁё]+),\s*(\d{2})', all_text)
                    if match:
                        print(f"👤 {match.group(1)}, {match.group(2)}")
                    else:
                        print("Карточка не найдена")
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 'c':
                try:
                    await page.locator('text=Чаты').click()
                    print("💬 Переход в чаты...")
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 'd':
                # Debug - показать структуру кнопок
                try:
                    buttons_html = await page.evaluate('''
                        Array.from(document.querySelectorAll('button')).slice(-5).map(b => ({
                            class: b.className.slice(0, 50),
                            text: b.innerText.slice(0, 20),
                            icons: Array.from(b.querySelectorAll('[class*="Icon"]')).map(i => i.className.slice(0, 40))
                        }))
                    ''')
                    print("🔧 Последние 5 кнопок:")
                    for i, btn in enumerate(buttons_html):
                        print(f"  {i}: {btn}")
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
