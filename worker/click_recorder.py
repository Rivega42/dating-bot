"""
Рекордер кликов - записывает клики с подписями
После каждого клика спрашивает что это было

Запуск: py click_recorder.py
"""
import asyncio
import os
import json
from datetime import datetime

from playwright.async_api import async_playwright


async def click_recorder():
    """Записывает клики с подписями пользователя"""
    
    print("🎬 Рекордер кликов VK Dating")
    print("="*60)
    
    session_path = os.path.join(os.path.dirname(__file__), "vk_session.json")
    log_path = os.path.join(os.path.dirname(__file__), "..", "research", "clicks_log.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    # Загружаем предыдущие записи
    clicks_log = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                clicks_log = json.load(f)
        except:
            clicks_log = []
    
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
            window._clickId = 0;
            
            document.addEventListener('mousedown', (e) => {
                const el = document.elementFromPoint(e.clientX, e.clientY) || e.target;
                const rect = el.getBoundingClientRect();
                
                // Собираем путь
                let path = [];
                let current = el;
                for (let i = 0; i < 10 && current && current !== document.body; i++) {
                    let selector = current.tagName.toLowerCase();
                    if (current.id) {
                        selector += '#' + current.id;
                    } else if (current.className && typeof current.className === 'string') {
                        const classes = current.className.split(' ').filter(c => c && c.length < 30).slice(0, 3);
                        if (classes.length) selector += '.' + classes.join('.');
                    }
                    path.unshift(selector);
                    current = current.parentElement;
                }
                
                // Ищем ближайшую кнопку/ссылку
                let clickable = el;
                let search = el;
                for (let i = 0; i < 5 && search; i++) {
                    if (search.tagName === 'BUTTON' || search.tagName === 'A' || search.getAttribute('role') === 'button') {
                        clickable = search;
                        break;
                    }
                    search = search.parentElement;
                }
                
                const clickableRect = clickable.getBoundingClientRect();
                
                window._clickId++;
                const info = {
                    id: window._clickId,
                    timestamp: new Date().toISOString(),
                    element: {
                        tag: el.tagName,
                        id: el.id || null,
                        className: (typeof el.className === 'string' ? el.className : '') || null,
                        text: el.innerText?.slice(0, 150)?.replace(/\\n/g, ' ') || null,
                        ariaLabel: el.getAttribute('aria-label') || null,
                    },
                    clickable: {
                        tag: clickable.tagName,
                        id: clickable.id || null,
                        className: (typeof clickable.className === 'string' ? clickable.className : '') || null,
                        text: clickable.innerText?.slice(0, 150)?.replace(/\\n/g, ' ') || null,
                        ariaLabel: clickable.getAttribute('aria-label') || null,
                        href: clickable.href || null,
                    },
                    rect: {x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height)},
                    clickableRect: {x: Math.round(clickableRect.x), y: Math.round(clickableRect.y), width: Math.round(clickableRect.width), height: Math.round(clickableRect.height)},
                    path: path.join(' > '),
                    outerHTML: clickable.outerHTML?.slice(0, 800) || null
                };
                
                window._clickedElements.push(info);
            }, true);
        """)
        
        print("📱 Открываем vk.com/dating...")
        await page.goto("https://vk.com/dating", wait_until="domcontentloaded", timeout=60000)
        
        # Ждём загрузки контента
        print("⏳ Ждём загрузку страницы...")
        await asyncio.sleep(5)
        
        print()
        print("="*60)
        print("🎬 ЗАПИСЬ НАЧАЛАСЬ!")
        print("="*60)
        print()
        print("1. Кликни на элемент в браузере")
        print("2. Введи название (например: btn_like, tab_chats)")
        print("3. Повтори для всех элементов")
        print()
        print("Подсказки для названий:")
        print("  btn_like      - кнопка лайка")
        print("  btn_dislike   - кнопка дизлайка")
        print("  btn_superlike - кнопка суперлайка")
        print("  tab_cards     - вкладка Анкеты")
        print("  tab_likes     - вкладка Лайки")
        print("  tab_chats     - вкладка Чаты")
        print("  tab_profile   - вкладка Профиль")
        print("  profile_name  - имя на карточке")
        print("  profile_age   - возраст")
        print("  photo         - фото карточки")
        print()
        print("Введи 'q' для выхода, 's' для показа всех записей")
        print("="*60)
        
        session_clicks = []
        click_count = 0
        
        while True:
            # Ждём клик
            print("\n⏳ Кликни на элемент в браузере...")
            
            # Polling для кликов
            click = None
            while not click:
                await asyncio.sleep(0.2)
                try:
                    new_clicks = await page.evaluate("window._clickedElements.splice(0)")
                    if new_clicks:
                        click = new_clicks[-1]  # Берём последний клик
                except:
                    pass
            
            click_count += 1
            
            # Показываем инфо о клике
            print(f"\n{'='*60}")
            print(f"🖱️  КЛИК #{click_count}")
            print(f"{'='*60}")
            print(f"  Tag: {click['element']['tag']}")
            print(f"  Text: {click['element']['text'][:50] if click['element']['text'] else '-'}")
            print(f"  Class: {click['element']['className'][:60] if click['element']['className'] else '-'}")
            print(f"  Position: x={click['rect']['x']}, y={click['rect']['y']}")
            
            # Спрашиваем название
            label = input("\n📝 Что это? (название или q/s): ").strip()
            
            if label.lower() == 'q':
                break
            elif label.lower() == 's':
                # Показать все записи
                print(f"\n📋 Записано элементов: {len(session_clicks)}")
                for c in session_clicks:
                    print(f"  • {c['label']}: {c['element']['tag']} | {c['element']['text'][:30] if c['element']['text'] else '-'}")
                continue
            elif label == '':
                print("⏭️ Пропущено")
                continue
            
            # Сохраняем с меткой
            click['label'] = label
            click['session'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            session_clicks.append(click)
            clicks_log.append(click)
            
            print(f"✅ Сохранено: {label}")
            
            # Сохраняем в файл сразу
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(clicks_log, f, ensure_ascii=False, indent=2)
        
        # Финальный вывод
        print(f"\n{'='*60}")
        print(f"📋 ИТОГО ЗАПИСАНО: {len(session_clicks)} элементов")
        print(f"{'='*60}")
        for c in session_clicks:
            print(f"  • {c['label']}")
            print(f"    Tag: {c['clickable']['tag']}")
            print(f"    Class: {c['clickable']['className'][:50] if c['clickable']['className'] else '-'}")
            print()
        
        print(f"💾 Сохранено в {log_path}")
        
        # Генерируем Python код с селекторами
        selectors_path = os.path.join(os.path.dirname(log_path), "selectors.py")
        with open(selectors_path, "w", encoding="utf-8") as f:
            f.write('"""VK Dating селекторы - сгенерировано автоматически"""\n\n')
            f.write('class VKDatingSelectors:\n')
            for c in session_clicks:
                label = c['label'].upper().replace(' ', '_')
                class_name = c['clickable']['className'] or c['element']['className'] or ''
                first_class = class_name.split()[0] if class_name else ''
                if first_class:
                    f.write(f'    {label} = ".{first_class}"  # {c["clickable"]["tag"]}\n')
                else:
                    f.write(f'    {label} = "{c["clickable"]["tag"].lower()}"  # no class\n')
        
        print(f"🐍 Селекторы: {selectors_path}")
        
        # Сохраняем сессию
        storage = await context.storage_state()
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        print("✅ Готово!")


if __name__ == "__main__":
    asyncio.run(click_recorder())
