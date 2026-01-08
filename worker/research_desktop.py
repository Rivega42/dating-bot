"""
Исследование DOM десктопной версии VK Dating
Запуск: py research_desktop.py
"""
import asyncio
import os
import json
from playwright.async_api import async_playwright


async def research_vk_dating():
    """Исследует DOM vk.com/dating"""
    
    print("🔬 Исследование VK Dating (десктоп)...")
    
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
        page.set_default_timeout(10000)
        
        print("📱 Открываем vk.com/dating...")
        await page.goto("https://vk.com/dating", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)
        
        print("\n" + "="*60)
        print("🔬 ИССЛЕДОВАНИЕ DOM")
        print("="*60)
        
        # 1. Исследуем кнопки действий
        print("\n📍 1. КНОПКИ ДЕЙСТВИЙ (лайк/скип/суперлайк)")
        buttons_info = await page.evaluate('''
            (() => {
                const results = [];
                // Ищем кнопки в области карточки
                const buttons = document.querySelectorAll('button');
                buttons.forEach((btn, i) => {
                    const rect = btn.getBoundingClientRect();
                    // Фильтруем кнопки в нижней части (где обычно лайк/скип)
                    if (rect.bottom > 600 && rect.width > 50 && rect.width < 200) {
                        results.push({
                            index: i,
                            class: btn.className,
                            ariaLabel: btn.getAttribute('aria-label'),
                            title: btn.title,
                            innerHTML: btn.innerHTML.slice(0, 100),
                            rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}
                        });
                    }
                });
                return results;
            })()
        ''')
        for btn in buttons_info:
            print(f"  Button: class={btn['class'][:50]}, aria={btn['ariaLabel']}, title={btn['title']}")
            print(f"    pos: x={btn['rect']['x']:.0f}, y={btn['rect']['y']:.0f}, w={btn['rect']['w']:.0f}")
        
        # 2. Исследуем вкладки
        print("\n📍 2. ВКЛАДКИ (Анкеты, Лайки, Чаты, Профиль)")
        tabs_info = await page.evaluate('''
            (() => {
                const results = [];
                // Ищем элементы с текстом вкладок
                const elements = document.querySelectorAll('a, button, div, span');
                const tabNames = ['Анкеты', 'Лайки', 'Чаты', 'Профиль'];
                elements.forEach(el => {
                    tabNames.forEach(name => {
                        if (el.innerText && el.innerText.includes(name) && el.innerText.length < 30) {
                            results.push({
                                tag: el.tagName,
                                class: el.className.slice(0, 60),
                                text: el.innerText.slice(0, 30),
                                href: el.href || ''
                            });
                        }
                    });
                });
                return results.slice(0, 12);
            })()
        ''')
        for tab in tabs_info:
            print(f"  {tab['tag']}: class={tab['class']}, text='{tab['text']}', href={tab['href']}")
        
        # 3. Исследуем данные профиля
        print("\n📍 3. ДАННЫЕ ПРОФИЛЯ (имя, возраст, инфо)")
        profile_info = await page.evaluate('''
            (() => {
                const text = document.body.innerText;
                // Ищем паттерн "Имя, возраст"
                const nameMatch = text.match(/([А-Яа-яЁё]+),\\s*(\\d{2})/);
                
                // Ищем секции
                const sections = {};
                ['Личное', 'Работа', 'Интересы', 'Я ищу'].forEach(section => {
                    const idx = text.indexOf(section);
                    if (idx > -1) {
                        sections[section] = text.slice(idx, idx + 100).replace(/\\n/g, ' ');
                    }
                });
                
                return {
                    name: nameMatch ? nameMatch[1] : null,
                    age: nameMatch ? nameMatch[2] : null,
                    sections: sections
                };
            })()
        ''')
        print(f"  Имя: {profile_info['name']}, Возраст: {profile_info['age']}")
        for section, content in profile_info['sections'].items():
            print(f"  {section}: {content[:60]}...")
        
        # 4. Тестируем горячие клавиши
        print("\n📍 4. ТЕСТ ГОРЯЧИХ КЛАВИШ")
        print("  Попробуем нажать клавиши...")
        
        # Сохраняем текущее имя
        initial_name = profile_info['name']
        
        # Нажимаем стрелку вправо (следующее фото)
        await page.keyboard.press('ArrowRight')
        await asyncio.sleep(0.5)
        print("  → ArrowRight (следующее фото)")
        
        await page.keyboard.press('ArrowLeft')
        await asyncio.sleep(0.5)
        print("  ← ArrowLeft (предыдущее фото)")
        
        # 5. Ищем селекторы для кнопок
        print("\n📍 5. ПОИСК СЕЛЕКТОРОВ КНОПОК")
        
        # Красная кнопка (дизлайк/скип)
        skip_selector = await page.evaluate('''
            (() => {
                const buttons = document.querySelectorAll('button');
                for (let btn of buttons) {
                    const style = getComputedStyle(btn);
                    const bgColor = style.backgroundColor;
                    // Красная кнопка
                    if (bgColor.includes('rgb(255') || bgColor.includes('rgb(239') || 
                        btn.className.includes('dislike') || btn.className.includes('skip') ||
                        btn.innerHTML.includes('cancel') || btn.innerHTML.includes('close')) {
                        return {
                            found: true,
                            class: btn.className,
                            selector: btn.className.split(' ')[0] ? '.' + btn.className.split(' ')[0] : null
                        };
                    }
                }
                return {found: false};
            })()
        ''')
        print(f"  Skip/Dislike: {skip_selector}")
        
        # Фиолетовая кнопка (лайк)
        like_selector = await page.evaluate('''
            (() => {
                const buttons = document.querySelectorAll('button');
                for (let btn of buttons) {
                    const style = getComputedStyle(btn);
                    const bgColor = style.backgroundColor;
                    // Фиолетовая кнопка
                    if (bgColor.includes('rgb(137') || bgColor.includes('rgb(138') ||
                        btn.className.includes('like') || 
                        btn.innerHTML.includes('like') || btn.innerHTML.includes('heart')) {
                        return {
                            found: true,
                            class: btn.className,
                            bgColor: bgColor
                        };
                    }
                }
                return {found: false};
            })()
        ''')
        print(f"  Like: {like_selector}")
        
        # 6. Проверяем работу клавиш для лайка
        print("\n📍 6. ТЕСТ КЛАВИШ ДЕЙСТВИЙ")
        print("  Нажмите в браузере на карточку, чтобы активировать окно")
        input("  Затем нажмите Enter здесь для теста клавиши '3' (лайк)...")
        
        # Кликаем на карточку чтобы активировать
        try:
            await page.click('body')
            await asyncio.sleep(0.3)
        except:
            pass
        
        # Пробуем разные клавиши
        keys_to_test = [
            ('1', 'Дизлайк'),
            ('2', 'Суперлайк'),
            ('3', 'Лайк'),
            ('ArrowLeft', 'Предыдущее фото'),
            ('ArrowRight', 'Следующее фото'),
        ]
        
        print("\n  Какую клавишу протестировать?")
        for i, (key, desc) in enumerate(keys_to_test):
            print(f"    {i+1}. {key} - {desc}")
        
        choice = input("  Введите номер (или 'q' для выхода): ").strip()
        
        if choice.isdigit() and 1 <= int(choice) <= len(keys_to_test):
            key, desc = keys_to_test[int(choice)-1]
            print(f"\n  Нажимаю '{key}' ({desc})...")
            await page.keyboard.press(key)
            await asyncio.sleep(1)
            
            # Проверяем изменилось ли имя
            new_profile = await page.evaluate('''
                (() => {
                    const text = document.body.innerText;
                    const nameMatch = text.match(/([А-Яа-яЁё]+),\\s*(\\d{2})/);
                    return nameMatch ? nameMatch[1] + ', ' + nameMatch[2] : null;
                })()
            ''')
            print(f"  Текущая карточка: {new_profile}")
            if new_profile != f"{initial_name}, {profile_info['age']}":
                print(f"  ✅ Карточка изменилась! Клавиша работает!")
            else:
                print(f"  ⚠️ Карточка не изменилась")
        
        # 7. Интерактивный режим
        print("\n" + "="*60)
        print("🎮 ИНТЕРАКТИВНЫЙ ТЕСТ")
        print("="*60)
        print("Команды:")
        print("  1 - Дизлайк (клавиша 1)")
        print("  2 - Суперлайк (клавиша 2)")
        print("  3 - Лайк (клавиша 3)")
        print("  4 - Предыдущее фото")
        print("  5 - Следующее фото")
        print("  p - Парсить профиль")
        print("  t - Перейти на вкладку (Анкеты/Лайки/Чаты/Профиль)")
        print("  q - Выход")
        print("="*60)
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'q':
                break
            elif cmd == '1':
                await page.keyboard.press('1')
                print("❌ Дизлайк!")
                await asyncio.sleep(1)
            elif cmd == '2':
                await page.keyboard.press('2')
                print("🔥 Суперлайк!")
                await asyncio.sleep(1)
            elif cmd == '3':
                await page.keyboard.press('3')
                print("❤️ Лайк!")
                await asyncio.sleep(1)
            elif cmd == '4':
                await page.keyboard.press('ArrowLeft')
                print("⬅️ Предыдущее фото")
            elif cmd == '5':
                await page.keyboard.press('ArrowRight')
                print("➡️ Следующее фото")
            elif cmd == 'p':
                profile = await page.evaluate('''
                    (() => {
                        const text = document.body.innerText;
                        const nameMatch = text.match(/([А-Яа-яЁё]+),\\s*(\\d{2})/);
                        return {
                            name: nameMatch ? nameMatch[1] : null,
                            age: nameMatch ? nameMatch[2] : null,
                            fullText: text.slice(0, 500)
                        };
                    })()
                ''')
                print(f"👤 {profile['name']}, {profile['age']}")
            elif cmd == 't':
                tab = input("  Какая вкладка? (1=Анкеты, 2=Лайки, 3=Чаты, 4=Профиль): ").strip()
                tab_names = {'1': 'Анкеты', '2': 'Лайки', '3': 'Чаты', '4': 'Профиль'}
                if tab in tab_names:
                    await page.evaluate(f'''
                        document.querySelectorAll('a, div, span').forEach(el => {{
                            if (el.innerText && el.innerText.trim() === '{tab_names[tab]}') {{
                                el.click();
                            }}
                        }});
                    ''')
                    print(f"📑 Переход на '{tab_names[tab]}'...")
                    await asyncio.sleep(1)
        
        # Сохраняем сессию
        storage = await context.storage_state()
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        print("✅ Исследование завершено!")


if __name__ == "__main__":
    asyncio.run(research_vk_dating())
