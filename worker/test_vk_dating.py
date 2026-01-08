"""
Тестовый скрипт для VK Dating (десктоп)
Горячие клавиши VK:
  < (Б/,) - Дизлайк
  > (Ю/.) - Лайк
  ← → (стрелки) - Листать фото

Запуск: py test_vk_dating.py
"""
import asyncio
import os
import re
import json

from playwright.async_api import async_playwright


async def test_vk_dating():
    """Тестирует VK Dating с горячими клавишами"""
    
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
        
        # Парсим текущую карточку
        def parse_profile(text):
            match = re.search(r'([А-Яа-яЁё]+),\s*(\d{2})', text)
            if match:
                return f"{match.group(1)}, {match.group(2)}"
            return None
        
        all_text = await page.locator('body').inner_text()
        profile = parse_profile(all_text)
        if profile:
            print(f"👤 Текущая карточка: {profile}")
        
        # Активируем окно кликом
        await page.click('body')
        await asyncio.sleep(0.3)
        
        print("\n" + "="*50)
        print("🎮 УПРАВЛЕНИЕ")
        print("="*50)
        print("  l (или ю/.) - Лайк")
        print("  d (или б/,) - Дизлайк")
        print("  s           - Суперлайк")
        print("  a (или ф)   - ← Предыдущее фото")
        print("  f (или а)   - → Следующее фото")
        print("  p           - Показать профиль")
        print("  t           - Вкладки")
        print("  r           - Обновить")
        print("  q           - Выход")
        print("="*50)
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'q':
                break
                
            elif cmd in ['l', 'ю', '.', '>']:
                # Лайк - клавиша > (точка/Ю)
                await page.keyboard.press('.')
                print("❤️ Лайк!")
                await asyncio.sleep(1)
                all_text = await page.locator('body').inner_text()
                profile = parse_profile(all_text)
                if profile:
                    print(f"👤 Новая: {profile}")
                    
            elif cmd in ['d', 'б', ',', '<']:
                # Дизлайк - клавиша < (запятая/Б)
                await page.keyboard.press(',')
                print("❌ Дизлайк!")
                await asyncio.sleep(1)
                all_text = await page.locator('body').inner_text()
                profile = parse_profile(all_text)
                if profile:
                    print(f"👤 Новая: {profile}")
                    
            elif cmd == 's':
                # Суперлайк
                await page.keyboard.press('/')
                print("🔥 Суперлайк!")
                await asyncio.sleep(1)
                    
            elif cmd in ['a', 'ф', 'left']:
                await page.keyboard.press('ArrowLeft')
                print("⬅️ Предыдущее фото")
                
            elif cmd in ['f', 'а', 'right']:
                await page.keyboard.press('ArrowRight')
                print("➡️ Следующее фото")
                
            elif cmd == 'p':
                all_text = await page.locator('body').inner_text()
                profile = parse_profile(all_text)
                if profile:
                    print(f"👤 {profile}")
                    for section in ['Я ищу', 'Работа', 'Интересы', 'Личное']:
                        if section in all_text:
                            idx = all_text.index(section)
                            snippet = all_text[idx:idx+80].replace('\n', ' ')
                            print(f"   {snippet}")
                else:
                    print("Профиль не найден")
                    
            elif cmd == 't':
                print("  1=Анкеты  2=Лайки  3=Чаты  4=Профиль")
                tab = input("  Выбор: ").strip()
                tabs = {'1': 'Анкеты', '2': 'Лайки', '3': 'Чаты', '4': 'Профиль'}
                if tab in tabs:
                    await page.click(f'text="{tabs[tab]}"')
                    print(f"📑 {tabs[tab]}")
                    await asyncio.sleep(1)
                    
            elif cmd == 'r':
                await page.reload()
                print("🔄 Обновлено")
                await asyncio.sleep(2)
        
        # Сохраняем сессию
        storage = await context.storage_state()
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        print("✅ Готово!")


if __name__ == "__main__":
    asyncio.run(test_vk_dating())
