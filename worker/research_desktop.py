"""
Интерактивное исследование DOM VK Dating
Запуск: py research_desktop.py
"""
import asyncio
import os
import json

from playwright.async_api import async_playwright


async def research_vk_dating():
    """Интерактивное исследование DOM"""
    
    print("🔬 Исследование VK Dating...")
    
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            storage_state=session_path
        )
        
        page = await context.new_page()
        page.set_default_timeout(10000)
        
        print("📱 Открываем vk.com/dating...")
        await page.goto("https://vk.com/dating", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        
        print("\n" + "="*60)
        print("🔬 ИНТЕРАКТИВНОЕ ИССЛЕДОВАНИЕ")
        print("="*60)
        print("Команды:")
        print("  1 - Найти ВСЕ кнопки на странице")
        print("  2 - Найти вкладки дейтинга")
        print("  3 - Найти текст профиля (имя, возраст)")
        print("  4 - Показать HTML элемента под курсором (кликни в браузере)")
        print("  5 - Выполнить свой JS код")
        print("  6 - Скриншот + HTML")
        print("  7 - Тест клика по вкладке")
        print("  q - Выход")
        print("="*60)
        
        while True:
            cmd = input("\n> ").strip()
            
            if cmd == 'q':
                break
                
            elif cmd == '1':
                # Все кнопки
                print("\n🔍 Ищу все кнопки...")
                buttons = await page.evaluate('''
                    (() => {
                        const results = [];
                        document.querySelectorAll('button').forEach((btn, i) => {
                            const rect = btn.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                results.push({
                                    i: i,
                                    class: btn.className?.slice(0, 60) || '',
                                    text: btn.innerText?.slice(0, 30)?.replace(/\\n/g, ' ') || '',
                                    aria: btn.getAttribute('aria-label') || '',
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    w: Math.round(rect.width),
                                    h: Math.round(rect.height)
                                });
                            }
                        });
                        return results;
                    })()
                ''')
                print(f"Найдено {len(buttons)} кнопок:\n")
                for btn in buttons:
                    print(f"  [{btn['i']}] x={btn['x']:4} y={btn['y']:4} w={btn['w']:3} | {btn['text'][:20]:20} | {btn['aria'][:20]:20} | {btn['class'][:30]}")
                    
            elif cmd == '2':
                # Вкладки дейтинга
                print("\n🔍 Ищу вкладки дейтинга...")
                tabs = await page.evaluate('''
                    (() => {
                        const results = [];
                        // Ищем по тексту
                        const keywords = ['Анкеты', 'Лайки', 'Чаты', 'Профиль', 'Подборки'];
                        document.querySelectorAll('*').forEach(el => {
                            const text = el.innerText?.trim();
                            if (!text || text.length > 50) return;
                            
                            keywords.forEach(kw => {
                                if (text.includes(kw)) {
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 0 && rect.y > 0 && rect.y < 200) {
                                        results.push({
                                            text: text.slice(0, 30),
                                            tag: el.tagName,
                                            class: el.className?.slice(0, 50) || '',
                                            x: Math.round(rect.x),
                                            y: Math.round(rect.y)
                                        });
                                    }
                                }
                            });
                        });
                        // Убираем дубли
                        return results.filter((v, i, a) => a.findIndex(t => t.text === v.text && t.tag === v.tag) === i);
                    })()
                ''')
                print(f"Найдено {len(tabs)} элементов:\n")
                for tab in tabs:
                    print(f"  [{tab['tag']}] x={tab['x']:4} y={tab['y']:4} | '{tab['text']}' | {tab['class'][:40]}")
                    
            elif cmd == '3':
                # Текст профиля
                print("\n🔍 Ищу имя и возраст...")
                profile = await page.evaluate('''
                    (() => {
                        const text = document.body.innerText;
                        const lines = text.split('\\n').filter(l => l.trim());
                        
                        // Ищем паттерн "Имя, возраст"
                        const matches = [];
                        lines.forEach(line => {
                            const m = line.match(/([А-Яа-яЁё]+),\\s*(\\d{2})/);
                            if (m) {
                                matches.push({line: line.slice(0, 50), name: m[1], age: m[2]});
                            }
                        });
                        
                        return {
                            matches: matches,
                            sample_lines: lines.slice(0, 30)
                        };
                    })()
                ''')
                
                if profile['matches']:
                    print("Найдены совпадения:")
                    for m in profile['matches']:
                        print(f"  👤 {m['name']}, {m['age']} (строка: '{m['line']}')")
                else:
                    print("Паттерн 'Имя, возраст' не найден")
                    print("\nПервые 30 строк текста:")
                    for i, line in enumerate(profile['sample_lines'][:30]):
                        print(f"  {i}: {line[:60]}")
                        
            elif cmd == '4':
                print("\nКликни на элемент в браузере, затем нажми Enter...")
                input()
                # Получаем элемент под фокусом
                info = await page.evaluate('''
                    (() => {
                        const el = document.activeElement;
                        return {
                            tag: el.tagName,
                            class: el.className,
                            id: el.id,
                            text: el.innerText?.slice(0, 100),
                            html: el.outerHTML?.slice(0, 300)
                        };
                    })()
                ''')
                print(f"Активный элемент:")
                print(f"  Tag: {info['tag']}")
                print(f"  Class: {info['class']}")
                print(f"  ID: {info['id']}")
                print(f"  Text: {info['text']}")
                print(f"  HTML: {info['html']}")
                
            elif cmd == '5':
                print("Введи JS код:")
                js_code = input("JS> ")
                try:
                    result = await page.evaluate(js_code)
                    print(f"Результат: {result}")
                except Exception as e:
                    print(f"Ошибка: {e}")
                    
            elif cmd == '6':
                # Скриншот
                screenshot_path = "screenshot.png"
                await page.screenshot(path=screenshot_path)
                print(f"✅ Скриншот: {screenshot_path}")
                
                # HTML
                html = await page.content()
                html_path = "page.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"✅ HTML: {html_path}")
                
            elif cmd == '7':
                print("Какую вкладку кликнуть? (введи текст, например 'Анкеты'):")
                tab_name = input("Tab> ").strip()
                if tab_name:
                    result = await page.evaluate(f'''
                        (() => {{
                            let clicked = false;
                            document.querySelectorAll('*').forEach(el => {{
                                const text = el.innerText?.trim();
                                if (text === '{tab_name}' || text?.startsWith('{tab_name} ')) {{
                                    const rect = el.getBoundingClientRect();
                                    if (rect.y > 0 && rect.y < 200 && !clicked) {{
                                        el.click();
                                        clicked = true;
                                    }}
                                }}
                            }});
                            return clicked ? 'clicked' : 'not found';
                        }})()
                    ''')
                    print(f"Результат: {result}")
                    await asyncio.sleep(1)
        
        # Сохраняем сессию
        storage = await context.storage_state()
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        print("✅ Готово!")


if __name__ == "__main__":
    asyncio.run(research_vk_dating())
