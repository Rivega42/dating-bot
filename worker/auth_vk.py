"""
Скрипт для ручной авторизации в VK и сохранения сессии
Запуск: py auth_vk.py
"""
import asyncio
import json
import os
from playwright.async_api import async_playwright


async def auth_vk():
    print("=" * 50)
    print("🔐 Авторизация в VK")
    print("=" * 50)
    print()
    print("Откроется браузер. Войдите в свой аккаунт VK.")
    print("После входа нажмите Enter в этом окне.")
    print()
    
    async with async_playwright() as p:
        # Запуск видимого браузера
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={"width": 414, "height": 896},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            locale="ru-RU",
            timezone_id="Europe/Moscow"
        )
        
        # Anti-detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = await context.new_page()
        
        # Открываем VK
        print("🌐 Открываю vk.com...")
        await page.goto("https://m.vk.com/dating", wait_until="domcontentloaded")
        
        # Ждём пока пользователь авторизуется
        print()
        print("👆 Авторизуйтесь в открытом браузере!")
        print()
        input("✅ После входа в VK Dating нажмите Enter здесь...")
        
        # Проверяем что авторизовались
        current_url = page.url
        print(f"📍 Текущий URL: {current_url}")
        
        if "login" in current_url or "auth" in current_url:
            print("❌ Похоже вы не авторизовались. Попробуйте ещё раз.")
            await browser.close()
            return
        
        # Сохраняем сессию
        print("💾 Сохраняю сессию...")
        storage = await context.storage_state()
        
        session_path = os.path.join(os.path.dirname(__file__), "vk_session.json")
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        print()
        print("=" * 50)
        print(f"✅ Сессия сохранена: {session_path}")
        print("=" * 50)
        print()
        print("Теперь запустите тест:")
        print("  py test_vk_dating.py")
        print()
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(auth_vk())
