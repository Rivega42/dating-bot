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
    """Селекторы VK Dating"""
    # Кнопки действий
    BTN_SKIP = 'button:has([class*="cancel"]), button:has([class*="Icon--cancel"])'
    BTN_LIKE = 'button:has([class*="like"]), button:has([class*="heart"])'
    BTN_SUPERLIKE = 'button:has([class*="fire"]), button:has([class*="flame"])'
    
    # Кнопка входа в Dating
    BTN_ENTER_DATING = 'button:has-text("Войти"), button:has-text("Начать"), button:has-text("Продолжить")'


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
        
        # ДЕСКТОПНАЯ версия (как при авторизации)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            storage_state=session_path
        )
        
        # Anti-detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = await context.new_page()
        
        # Переходим на Dating (ДЕСКТОП)
        print("📱 Открываем vk.com/dating...")
        await page.goto("https://vk.com/dating", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        page.set_default_timeout(5000)
        
        current_url = page.url
        print(f"📍 Текущий URL: {current_url}")
        
        # Проверяем авторизацию
        if "login" in current_url:
            print("❌ Сессия истекла! Запустите: py auth_vk.py")
            await browser.close()
            return
        
        # Ищем кнопку входа в Dating
        try:
            enter_btn = page.locator(VKSelectors.BTN_ENTER_DATING).first
            if await enter_btn.is_visible():
                print("🔑 Нажимаем 'Войти' в Dating...")
                await enter_btn.click()
                await asyncio.sleep(3)
        except:
            pass
        
        print("🔍 Ищем элементы...")
        await asyncio.sleep(2)
        
        # Ищем имя профиля
        all_text = await page.locator('body').inner_text()
        match = re.search(r'([А-Яа-яЁё]+),\s*(\d{2})', all_text)
        if match:
            print(f"   👤 Найдено: {match.group(1)}, {match.group(2)}")
        else:
            print("   ⚠️ Карточка не найдена")
        
        # Интерактивный режим
        print("\n" + "="*50)
        print("🎮 ИНТЕРАКТИВНЫЙ РЕЖИМ")
        print("="*50)
        print("Команды:")
        print("  l - лайк")
        print("  s - скип")
        print("  p - парсить карточку")
        print("  c - перейти в чаты")
        print("  d - debug (показать кнопки)")
        print("  r - refresh страницу")
        print("  q - выход")
        print("="*50)
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'q':
                break
                
            elif cmd == 'l':
                try:
                    # Ищем все кнопки и кликаем на лайк
                    result = await page.evaluate('''
                        (() => {
                            const buttons = document.querySelectorAll('button');
                            for (let b of buttons) {
                                const cls = b.className + ' ' + b.innerHTML;
                                if (cls.includes('like') || cls.includes('heart') || cls.includes('Like')) {
                                    b.click();
                                    return 'clicked like';
                                }
                            }
                            // Пробуем последнюю кнопку
                            const allBtns = Array.from(buttons);
                            if (allBtns.length > 0) {
                                allBtns[allBtns.length - 1].click();
                                return 'clicked last button';
                            }
                            return 'no button found';
                        })()
                    ''')
                    print(f"❤️ Лайк! ({result})")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 's':
                try:
                    result = await page.evaluate('''
                        (() => {
                            const buttons = document.querySelectorAll('button');
                            for (let b of buttons) {
                                const cls = b.className + ' ' + b.innerHTML;
                                if (cls.includes('cancel') || cls.includes('skip') || cls.includes('Cancel') || cls.includes('close')) {
                                    b.click();
                                    return 'clicked skip';
                                }
                            }
                            return 'no skip button found';
                        })()
                    ''')
                    print(f"❌ Скип! ({result})")
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
                    # Ищем вкладку чатов
                    await page.evaluate('''
                        document.querySelectorAll('a, button, div').forEach(el => {
                            if (el.innerText && el.innerText.includes('Чат')) {
                                el.click();
                            }
                        });
                    ''')
                    print("💬 Переход в чаты...")
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 'd':
                # Debug - показать структуру
                try:
                    info = await page.evaluate('''
                        (() => {
                            const buttons = Array.from(document.querySelectorAll('button')).slice(-10);
                            return buttons.map((b, i) => ({
                                idx: i,
                                class: b.className.slice(0, 60),
                                text: b.innerText.slice(0, 30).replace(/\\n/g, ' ')
                            }));
                        })()
                    ''')
                    print("🔧 Последние 10 кнопок:")
                    for btn in info:
                        print(f"  {btn['idx']}: [{btn['class']}] {btn['text']}")
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == 'r':
                print("🔄 Обновляем...")
                await page.reload()
                await asyncio.sleep(3)
        
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
