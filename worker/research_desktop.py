"""
Полное исследование DOM VK Dating (десктоп)
Сохраняет все селекторы в файл VK_DESKTOP_SELECTORS.md

Запуск: py research_desktop.py
"""
import asyncio
import os
import json
from datetime import datetime

from playwright.async_api import async_playwright


async def research_vk_dating():
    """Исследует DOM vk.com/dating и сохраняет селекторы"""
    
    print("🔬 Полное исследование VK Dating...")
    
    session_path = os.path.join(os.path.dirname(__file__), "vk_session.json")
    
    if not os.path.exists(session_path):
        print("❌ Сначала запустите: py auth_vk.py")
        return
    
    results = {
        "date": datetime.now().isoformat(),
        "tabs": [],
        "action_buttons": [],
        "profile_selectors": [],
        "keyboard_shortcuts": {},
        "navigation": []
    }
    
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
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        page = await context.new_page()
        page.set_default_timeout(10000)
        
        print("📱 Открываем vk.com/dating...")
        await page.goto("https://vk.com/dating", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        
        print("\n" + "="*60)
        print("🔬 ИССЛЕДОВАНИЕ DOM")
        print("="*60)
        
        # ============================================
        # 1. ВКЛАДКИ (Анкеты, Лайки, Чаты, Профиль)
        # ============================================
        print("\n📍 1. ВКЛАДКИ")
        tabs_data = await page.evaluate('''
            (() => {
                const results = [];
                const tabTexts = ['Анкеты', 'Лайки', 'Чаты', 'Профиль'];
                
                // Ищем все кликабельные элементы
                document.querySelectorAll('a, div, span, button').forEach(el => {
                    const text = el.innerText?.trim();
                    if (!text) return;
                    
                    tabTexts.forEach(tabName => {
                        // Точное совпадение или начинается с
                        if (text === tabName || text.startsWith(tabName + ' ')) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                results.push({
                                    name: tabName,
                                    tag: el.tagName,
                                    class: el.className?.slice(0, 80) || '',
                                    id: el.id || '',
                                    href: el.href || '',
                                    text: text.slice(0, 30),
                                    rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}
                                });
                            }
                        }
                    });
                });
                
                return results;
            })()
        ''')
        
        for tab in tabs_data:
            print(f"  [{tab['name']}] {tab['tag']} class='{tab['class'][:40]}' href='{tab['href']}'")
        results["tabs"] = tabs_data
        
        # ============================================
        # 2. КНОПКИ ДЕЙСТВИЙ (Лайк, Дизлайк, Суперлайк)
        # ============================================
        print("\n📍 2. КНОПКИ ДЕЙСТВИЙ")
        buttons_data = await page.evaluate('''
            (() => {
                const results = [];
                const buttons = document.querySelectorAll('button');
                
                buttons.forEach((btn, idx) => {
                    const rect = btn.getBoundingClientRect();
                    const style = getComputedStyle(btn);
                    
                    // Кнопки в нижней части карточки (y > 500) и видимые
                    if (rect.y > 400 && rect.width > 40 && rect.height > 40 && rect.width < 200) {
                        const svgIcons = Array.from(btn.querySelectorAll('svg, [class*="Icon"]'))
                            .map(s => s.className?.baseVal || s.className || '').join(', ');
                        
                        results.push({
                            index: idx,
                            class: btn.className?.slice(0, 80) || '',
                            ariaLabel: btn.getAttribute('aria-label') || '',
                            title: btn.title || '',
                            bgColor: style.backgroundColor,
                            icons: svgIcons.slice(0, 100),
                            rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)}
                        });
                    }
                });
                
                // Сортируем по X (слева направо)
                return results.sort((a, b) => a.rect.x - b.rect.x);
            })()
        ''')
        
        for i, btn in enumerate(buttons_data):
            position = ['ЛЕВАЯ (Дизлайк)', 'СРЕДНЯЯ (Суперлайк)', 'ПРАВАЯ (Лайк)'][i] if i < 3 else f'Кнопка {i}'
            print(f"  {position}:")
            print(f"    class: {btn['class'][:50]}")
            print(f"    aria-label: {btn['ariaLabel']}")
            print(f"    bgColor: {btn['bgColor']}")
            print(f"    pos: x={btn['rect']['x']}, y={btn['rect']['y']}")
        results["action_buttons"] = buttons_data
        
        # ============================================
        # 3. ДАННЫЕ ПРОФИЛЯ
        # ============================================
        print("\n📍 3. ДАННЫЕ ПРОФИЛЯ")
        profile_data = await page.evaluate('''
            (() => {
                const results = {
                    name_age: null,
                    sections: [],
                    all_text_blocks: []
                };
                
                // Ищем имя и возраст (обычно крупный заголовок)
                document.querySelectorAll('h1, h2, h3, [class*="Title"], [class*="Name"], [class*="header"]').forEach(el => {
                    const text = el.innerText?.trim();
                    if (text && /^[А-Яа-яЁё]+,\\s*\\d{2}$/.test(text)) {
                        results.name_age = {
                            text: text,
                            tag: el.tagName,
                            class: el.className?.slice(0, 80) || ''
                        };
                    }
                });
                
                // Ищем секции профиля
                const sectionNames = ['Личное', 'Работа', 'Интересы', 'Я ищу', 'О себе'];
                document.querySelectorAll('*').forEach(el => {
                    const text = el.innerText?.trim();
                    if (!text) return;
                    
                    sectionNames.forEach(section => {
                        if (text.startsWith(section) && text.length < 200) {
                            results.sections.push({
                                section: section,
                                text: text.slice(0, 150),
                                tag: el.tagName,
                                class: el.className?.slice(0, 60) || ''
                            });
                        }
                    });
                });
                
                // Ищем все текстовые блоки в области профиля (справа от фото)
                document.querySelectorAll('div, span, p').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const text = el.innerText?.trim();
                    // Справа от центра экрана, в видимой области
                    if (rect.x > 600 && rect.y > 100 && rect.y < 800 && text && text.length > 5 && text.length < 100) {
                        results.all_text_blocks.push({
                            text: text.slice(0, 80),
                            tag: el.tagName,
                            class: el.className?.slice(0, 50) || '',
                            rect: {x: Math.round(rect.x), y: Math.round(rect.y)}
                        });
                    }
                });
                
                // Убираем дубли
                results.all_text_blocks = results.all_text_blocks.filter((v, i, a) => 
                    a.findIndex(t => t.text === v.text) === i
                ).slice(0, 20);
                
                return results;
            })()
        ''')
        
        if profile_data['name_age']:
            print(f"  Имя/возраст: {profile_data['name_age']['text']}")
            print(f"    selector: {profile_data['name_age']['tag']}.{profile_data['name_age']['class'][:30]}")
        
        print(f"\n  Секции профиля:")
        for sec in profile_data['sections'][:5]:
            print(f"    [{sec['section']}] {sec['text'][:50]}...")
        
        print(f"\n  Текстовые блоки (первые 10):")
        for block in profile_data['all_text_blocks'][:10]:
            print(f"    {block['text'][:40]}... ({block['tag']})")
        
        results["profile_selectors"] = profile_data
        
        # ============================================
        # 4. ГОРЯЧИЕ КЛАВИШИ
        # ============================================
        print("\n📍 4. ГОРЯЧИЕ КЛАВИШИ (из DOM)")
        shortcuts = await page.evaluate('''
            (() => {
                // Ищем элементы с подсказками клавиш
                const results = {};
                document.querySelectorAll('*').forEach(el => {
                    const text = el.innerText?.trim();
                    if (text && text.length < 30) {
                        if (text.includes('Дизлайк')) results['dislike'] = text;
                        if (text.includes('Суперлайк')) results['superlike'] = text;
                        if (text.includes('Лайк') && !text.includes('Дизлайк') && !text.includes('Суперлайк')) results['like'] = text;
                        if (text.includes('Предыдущее')) results['prev_photo'] = text;
                        if (text.includes('Следующее')) results['next_photo'] = text;
                    }
                });
                return results;
            })()
        ''')
        
        print(f"  Найденные подсказки: {shortcuts}")
        results["keyboard_shortcuts"] = {
            "dislike": ", (запятая / Б)",
            "like": ". (точка / Ю)", 
            "superlike": "/ (слеш)",
            "prev_photo": "ArrowLeft",
            "next_photo": "ArrowRight"
        }
        
        # ============================================
        # 5. ТЕСТ КЛАВИШ
        # ============================================
        print("\n📍 5. ТЕСТ ГОРЯЧИХ КЛАВИШ")
        
        # Активируем страницу
        await page.click('body')
        await asyncio.sleep(0.5)
        
        # Тест стрелок
        print("  Тестирую ArrowRight...")
        await page.keyboard.press('ArrowRight')
        await asyncio.sleep(0.5)
        print("  ✅ ArrowRight отправлен")
        
        print("  Тестирую ArrowLeft...")
        await page.keyboard.press('ArrowLeft')
        await asyncio.sleep(0.5)
        print("  ✅ ArrowLeft отправлен")
        
        # ============================================
        # СОХРАНЯЕМ РЕЗУЛЬТАТЫ
        # ============================================
        print("\n" + "="*60)
        print("💾 СОХРАНЕНИЕ РЕЗУЛЬТАТОВ")
        print("="*60)
        
        # Создаём Markdown документацию
        md_content = f"""# VK Dating Desktop - Селекторы

Сгенерировано: {results['date']}

## Горячие клавиши

| Действие | Клавиша | Playwright |
|----------|---------|------------|
| Дизлайк | < (Б / ,) | `page.keyboard.press(',')` |
| Лайк | > (Ю / .) | `page.keyboard.press('.')` |
| Суперлайк | / | `page.keyboard.press('/')` |
| Предыдущее фото | ← | `page.keyboard.press('ArrowLeft')` |
| Следующее фото | → | `page.keyboard.press('ArrowRight')` |

## Вкладки

"""
        for tab in tabs_data[:4]:
            md_content += f"### {tab['name']}\n"
            md_content += f"- Tag: `{tab['tag']}`\n"
            md_content += f"- Class: `{tab['class'][:60]}`\n"
            md_content += f"- Href: `{tab['href']}`\n\n"
        
        md_content += """## Кнопки действий

"""
        for i, btn in enumerate(buttons_data[:3]):
            names = ['Дизлайк (красная)', 'Суперлайк (оранжевая)', 'Лайк (фиолетовая)']
            md_content += f"### {names[i] if i < 3 else f'Кнопка {i}'}\n"
            md_content += f"- Class: `{btn['class'][:60]}`\n"
            md_content += f"- aria-label: `{btn['ariaLabel']}`\n"
            md_content += f"- Position: x={btn['rect']['x']}, y={btn['rect']['y']}\n\n"
        
        md_content += """## Парсинг профиля

```python
# Имя и возраст
"""
        if profile_data['name_age']:
            md_content += f"# Селектор: {profile_data['name_age']['tag']}, class содержит: {profile_data['name_age']['class'][:40]}\n"
        
        md_content += """
import re

async def parse_profile(page):
    # Метод 1: Через регулярку по всему тексту
    all_text = await page.locator('body').inner_text()
    match = re.search(r'([А-Яа-яЁё]+),\\s*(\\d{2})', all_text)
    if match:
        name, age = match.group(1), match.group(2)
    
    # Метод 2: Через evaluate (более надёжно)
    data = await page.evaluate('''
        (() => {
            const text = document.body.innerText;
            const match = text.match(/([А-Яа-яЁё]+),\\s*(\\d{2})/);
            return match ? {name: match[1], age: match[2]} : null;
        })()
    ''')
    return data
```

## Переход по вкладкам

```python
async def go_to_tab(page, tab_name):
    # tab_name: 'Анкеты', 'Лайки', 'Чаты', 'Профиль'
    await page.evaluate(f'''
        document.querySelectorAll('a, div, span').forEach(el => {{
            if (el.innerText?.trim() === '{tab_name}' || el.innerText?.startsWith('{tab_name} ')) {{
                el.click();
            }}
        }});
    ''')
```

## Полный пример

```python
import asyncio
from playwright.async_api import async_playwright

async def vk_dating_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="vk_session.json")
        page = await context.new_page()
        
        await page.goto("https://vk.com/dating")
        await asyncio.sleep(3)
        
        # Активируем окно
        await page.click('body')
        
        # Лайк
        await page.keyboard.press('.')
        
        # Дизлайк
        await page.keyboard.press(',')
        
        # Листать фото
        await page.keyboard.press('ArrowRight')
        await page.keyboard.press('ArrowLeft')
```
"""
        
        # Сохраняем MD
        md_path = os.path.join(os.path.dirname(__file__), "..", "research", "VK_DESKTOP_SELECTORS.md")
        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"  ✅ Сохранено: {md_path}")
        
        # Сохраняем JSON
        json_path = os.path.join(os.path.dirname(__file__), "..", "research", "vk_desktop_dom.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  ✅ Сохранено: {json_path}")
        
        # Сохраняем сессию
        storage = await context.storage_state()
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        print("\n✅ Исследование завершено!")


if __name__ == "__main__":
    asyncio.run(research_vk_dating())
