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
    print("Дождитесь полной загрузки главной страницы VK!")
    print()
    
    async with async_playwright() as p:
        # Запуск видимого браузера - ДЕСКТОПНЫЙ режим для QR кода
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Десктопный контекст для авторизации (там есть QR)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
        await page.goto("https://vk.com", wait_until="domcontentloaded")
        
        # Ждём пока пользователь авторизуется
        print()
        print("👆 Авторизуйтесь в открытом браузере (через QR или логин)!")
        print("⏳ Дождитесь загрузки ленты новостей!")
        print()
        input("✅ После полного входа в VK нажмите Enter здесь...")
        
        # Ждём стабилизации
        print("⏳ Ждём завершения редиректов...")
        await asyncio.sleep(3)
        
        current_url = page.url
        print(f"📍 Текущий URL: {current_url}")
        
        # Проверяем что авторизовались (не на странице логина)
        if "login" in current_url and "act=restore" not in current_url:
            print("⚠️ Кажется вы ещё не авторизовались.")
            print("   Войдите в VK и нажмите Enter ещё раз.")
            input("✅ Нажмите Enter когда будете на главной странице VK...")
            await asyncio.sleep(2)
        
        # Сохраняем сессию СРАЗУ (без перехода на Dating)
        print("💾 Сохраняю сессию...")
        storage = await context.storage_state()
        
        session_path = os.path.join(os.path.dirname(__file__), "vk_session.json")
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        # Теперь пробуем перейти на Dating
        print("📱 Переходим на Dating...")
        try:
            await page.goto("https://vk.com/dating", wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"⚠️ Редирект при переходе: {e}")
            # Ждём и пробуем ещё раз
            await asyncio.sleep(3)
            try:
                await page.goto("https://vk.com/dating", wait_until="domcontentloaded", timeout=30000)
            except:
                pass
        
        await asyncio.sleep(2)
        final_url = page.url
        print(f"📍 Финальный URL: {final_url}")
        
        # Обновляем сессию после Dating
        storage = await context.storage_state()
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
