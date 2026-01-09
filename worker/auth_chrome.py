"""
Авторизация через реальный Chrome (обходит детекцию VK)
Запуск: py auth_chrome.py
"""
import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    print("🚀 Запуск Chrome...")
    
    p = await async_playwright().start()
    
    browser = await p.chromium.launch_persistent_context(
        user_data_dir="C:/temp/vk_chrome",
        headless=False,
        channel="chrome",
        args=["--disable-blink-features=AutomationControlled"]
    )
    
    page = browser.pages[0] if browser.pages else await browser.new_page()
    
    print("🌐 Открываю vk.com...")
    await page.goto("https://vk.com")
    
    print()
    print("=" * 50)
    print("👆 Войди в VK (QR или логин)")
    print("⏳ Дождись загрузки ленты новостей")
    print("=" * 50)
    
    input("\n✅ Нажми Enter после входа...")
    
    storage = await browser.storage_state()
    with open("vk_session.json", "w", encoding="utf-8") as f:
        json.dump(storage, f, ensure_ascii=False, indent=2)
    
    print("💾 Сессия сохранена: vk_session.json")
    print("✅ Теперь запусти: py test_vk_dating.py")
    
    await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
