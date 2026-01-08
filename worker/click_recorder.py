"""
Рекордер кликов - записывает все клики в браузере
Кликай на элементы в браузере - информация сохраняется в clicks_log.json

Запуск: py click_recorder.py
"""
import asyncio
import os
import json
from datetime import datetime

from playwright.async_api import async_playwright


async def click_recorder():
    """Записывает все клики пользователя"""
    
    print("🎬 Рекордер кликов VK Dating")
    print("="*60)
    
    session_path = os.path.join(os.path.dirname(__file__), "vk_session.json")
    log_path = os.path.join(os.path.dirname(__file__), "..", "research", "clicks_log.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    # Загружаем предыдущие записи
    clicks_log = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            clicks_log = json.load(f)
    
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            storage_state=session_path
        )
        
        page = await context.new_page()
        
        # Инжектим скрипт для отслеживания кликов
        await page.add_init_script("""
            window._clickedElements = [];
            
            document.addEventListener('click', (e) => {
                const el = e.target;
                const rect = el.getBoundingClientRect();
                
                // Собираем путь к элементу
                let path = [];
                let current = el;
                while (current && current !== document.body) {
                    let selector = current.tagName.toLowerCase();
                    if (current.id) {
                        selector += '#' + current.id;
                    } else if (current.className && typeof current.className === 'string') {
                        const classes = current.className.split(' ').filter(c => c && !c.includes('--')).slice(0, 2);
                        if (classes.length) selector += '.' + classes.join('.');
                    }
                    path.unshift(selector);
                    current = current.parentElement;
                }
                
                const info = {
                    timestamp: new Date().toISOString(),
                    tag: el.tagName,
                    id: el.id || null,
                    className: el.className || null,
                    text: el.innerText?.slice(0, 100) || null,
                    ariaLabel: el.getAttribute('aria-label') || null,
                    href: el.href || null,
                    type: el.type || null,
                    role: el.getAttribute('role') || null,
                    rect: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    },
                    path: path.join(' > '),
                    outerHTML: el.outerHTML?.slice(0, 500) || null
                };
                
                window._clickedElements.push(info);
                console.log('CLICK RECORDED:', info.tag, info.text?.slice(0, 30));
            }, true);
        """)
        
        print("📱 Открываем vk.com/dating...")
        await page.goto("https://vk.com/dating", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        print()
        print("="*60)
        print("🎬 РЕЖИМ ЗАПИСИ АКТИВЕН")
        print("="*60)
        print()
        print("Кликай на любые элементы в браузере!")
        print("Каждый клик записывается автоматически.")
        print()
        print("Что записать:")
        print("  • Кнопки лайк/дизлайк/суперлайк")
        print("  • Вкладки (Анкеты, Лайки, Чаты, Профиль)")
        print("  • Имя и возраст на карточке")
        print("  • Любые другие элементы")
        print()
        print("Команды в консоли:")
        print("  Enter  - показать записанные клики")
        print("  s      - сохранить и показать все")
        print("  c      - очистить текущую сессию")
        print("  n      - добавить заметку к последнему клику")
        print("  q      - выход с сохранением")
        print("="*60)
        
        session_clicks = []
        
        while True:
            cmd = input("\n[Жду клик или команду] > ").strip().lower()
            
            # Получаем новые клики из браузера
            new_clicks = await page.evaluate("window._clickedElements.splice(0)")
            
            if new_clicks:
                for click in new_clicks:
                    click['session'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    session_clicks.append(click)
                    clicks_log.append(click)
                    
                    # Выводим инфо
                    print()
                    print(f"  🖱️  КЛИК #{len(session_clicks)}")
                    print(f"      Tag: {click['tag']}")
                    print(f"      Text: {click['text'][:50] if click['text'] else '-'}")
                    print(f"      Class: {click['className'][:60] if click['className'] else '-'}")
                    print(f"      aria-label: {click['ariaLabel'] or '-'}")
                    print(f"      Position: x={click['rect']['x']}, y={click['rect']['y']}")
                    print(f"      Path: {click['path'][:80]}")
            
            if cmd == 'q':
                break
                
            elif cmd == 's' or cmd == '':
                # Показать все клики сессии
                print(f"\n📋 Записано кликов в этой сессии: {len(session_clicks)}")
                for i, click in enumerate(session_clicks):
                    note = click.get('note', '')
                    note_str = f" [{note}]" if note else ""
                    print(f"  {i+1}. {click['tag']} | {click['text'][:30] if click['text'] else '-'}{note_str}")
                    
            elif cmd == 'c':
                session_clicks = []
                print("🗑️ Сессия очищена")
                
            elif cmd == 'n':
                if session_clicks:
                    note = input("Заметка: ").strip()
                    session_clicks[-1]['note'] = note
                    clicks_log[-1]['note'] = note
                    print(f"✅ Заметка добавлена: {note}")
                else:
                    print("Нет кликов для заметки")
        
        # Сохраняем лог
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(clicks_log, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Сохранено {len(clicks_log)} кликов в {log_path}")
        
        # Сохраняем читаемый отчёт
        report_path = os.path.join(os.path.dirname(log_path), "clicks_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# VK Dating - Записанные элементы\n\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            for i, click in enumerate(clicks_log):
                note = click.get('note', '')
                f.write(f"## Клик {i+1}")
                if note:
                    f.write(f" - {note}")
                f.write("\n\n")
                f.write(f"- **Tag:** `{click['tag']}`\n")
                f.write(f"- **Text:** `{click['text'][:50] if click['text'] else '-'}`\n")
                f.write(f"- **Class:** `{click['className'][:80] if click['className'] else '-'}`\n")
                f.write(f"- **aria-label:** `{click['ariaLabel'] or '-'}`\n")
                f.write(f"- **Position:** x={click['rect']['x']}, y={click['rect']['y']}\n")
                f.write(f"- **Path:** `{click['path']}`\n")
                f.write(f"\n```html\n{click['outerHTML'][:300] if click['outerHTML'] else '-'}\n```\n\n")
        
        print(f"📄 Отчёт: {report_path}")
        
        # Сохраняем сессию
        storage = await context.storage_state()
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        print("✅ Готово!")


if __name__ == "__main__":
    asyncio.run(click_recorder())
