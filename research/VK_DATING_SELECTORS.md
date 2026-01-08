# VK Dating Selectors Research Results
## Дата исследования: 2026-01-08

## Важно: Мобильная версия
VK Dating лучше автоматизировать через **m.vk.com/dating** — нет iframe, прямой доступ к DOM.

## Кнопки действий
Кнопки находятся по иконкам внутри них:

| Действие | Иконка | Селектор |
|----------|--------|----------|
| ❌ Пропустить | cancel | `button:has([class*="vkuiIcon--cancel_outline_28"])` |
| 🔥 Суперлайк | fire | `button:has([class*="vkuiIcon--fire_alt_outline_28"])` |
| ❤️ Лайк | like | `button:has([class*="vkuiIcon--like_outline_28"])` |
| ↩️ Вернуть | replay | `button:has([class*="vkuiIcon--replay_outline_28"])` |
| ⚡ Буст | flash | `button:has([class*="vkuiIcon--flash_28"])` |

## Навигация (табы)
| Таб | Иконка | Селектор |
|-----|--------|----------|
| Анкеты | cards | `[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--cards_2_outline_28"])` |
| Подборки | search_like | `[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--search_like_outline_28"])` |
| Лайки | like | `[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--like_outline_28"])` |
| Чаты | message | `[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--message_outline_28"])` |
| Профиль | user | `[class*="vkuiTabbarItem"]:has([class*="vkuiIcon--user_circle_outline_28"])` |

## Данные профиля
| Данные | Селектор |
|--------|----------|
| Имя, возраст | `[class*="vkuiTitle__level2"][class*="accent"]` |
| Текст в карточке | `[class*="vkuiText"], [class*="vkuiParagraph"]` |
| Мини-инфо (работа, образование) | `[class*="vkuiMiniInfoCell"]` |

## Иконки информации
- 📍 Локация: `vkuiIcon--place_12`
- 💼 Работа: `vkuiIcon--work_outline_20`
- 🎓 Образование: `vkuiIcon--education_outline_20`
- 💬 Цитата: `vkuiIcon--quote_closing_20`

## Структура DOM
```
vkuiPanel__in
├── Карточка с фото (background-image или img)
├── vkuiTitle__level2 (имя, возраст)
├── vkuiMiniInfoCell (город, работа, образование)
├── Теги интересов
└── Кнопки действий
    ├── cancel_outline_28 (пропустить)
    ├── fire_alt_outline_28 (суперлайк)
    └── like_outline_28 (лайк)
```

## Примечания
1. Классы типа `DvDUWVqV` — обфусцированы и могут меняться
2. Стабильные классы — все что начинается с `vkui`
3. Иконки — самый надёжный способ идентификации кнопок
4. App ID VK Dating: `7058363`
