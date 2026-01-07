# VK Dating Research Tools

Инструменты для исследования DOM-структуры VK Знакомства.

## Установка

```bash
cd research
pip install -r requirements.txt
playwright install chromium
```

## Запуск исследования

```bash
python vk_research.py
```

Скрипт:
1. Откроет браузер (видимый режим)
2. Перейдёт на vk.com — залогинься вручную
3. После логина нажми Enter в терминале
4. Скрипт перейдёт на VK Знакомства и соберёт данные
5. Результаты сохранятся в папку `output/`

## Что собирается

- `session.json` — сессия браузера для повторного использования
- `page_*.html` — HTML-дампы страниц
- `screenshot_*.png` — скриншоты
- `selectors_report.json` — найденные селекторы
- `dom_analysis.json` — структура DOM
