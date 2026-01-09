"""
VK Dating селекторы - извлечено из clicks_log.json
Дата: 2026-01-09

Приоритет селекторов:
1. aria-label / data-атрибуты (самые стабильные)
2. Текст элемента (для кнопок/вкладок)
3. CSS классы (могут меняться)
"""


class VKDatingSelectors:
    """Селекторы для VK Dating mini-app"""
    
    # ========== РЕАКЦИИ (кнопки действий) ==========
    # Используем aria-label - самые надёжные!
    
    BTN_LIKE = '[aria-label="like"]'
    BTN_LIKE_ALT = '[data-reaction="like"]'
    
    BTN_DISLIKE = '[aria-label="dislike"]'
    BTN_DISLIKE_ALT = '[data-reaction="dislike"]'
    
    BTN_SUPERLIKE = '[aria-label="super-like"]'
    BTN_SUPERLIKE_ALT = '[data-reaction="super-like"]'
    
    # Кнопка отправки суперлайка в попапе
    BTN_SEND_SUPERLIKE = 'button:has-text("Отправить суперлайк")'
    
    # ========== НАВИГАЦИЯ ПО ФОТО ==========
    
    PHOTO_NEXT = '.OAf1LKm6.Mq6KKuwQ'
    PHOTO_PREV = '.OAf1LKm6.wsUQAjKL'
    PHOTO_CONTAINER = '.m_OqgbAN'
    
    # ========== ВКЛАДКИ ==========
    
    TAB_CARDS = 'span.vkuiTabsItem__label:has-text("Анкеты")'
    TAB_LIKES = 'span.vkuiTabsItem__label:has-text("Лайки")'
    TAB_CHATS = 'span.vkuiTabsItem__label:has-text("Чаты")'
    TAB_PROFILE = 'span.vkuiTabsItem__label:has-text("Профиль")'
    
    # ========== ПРОФИЛЬ (карточка анкеты) ==========
    
    PROFILE_CARD = '#current-card'
    PROFILE_NAME = '.j2wk1ydI'  # Имя + возраст в заголовке
    PROFILE_BIO = '.QLecl7_H'  # Био описание
    PROFILE_LOOKING_FOR = '.Zk9UNqxx'  # "Я ищу"
    PROFILE_EDUCATION = '.vkuiMiniInfoCell__content'  # Образование/работа
    PROFILE_INTERESTS = '.vkuiHeader__contentIn:has-text("Интересы")'
    
    # ========== ЧАТЫ ==========
    
    CHAT_INPUT = '.vkuiWriteBar__textarea'
    CHAT_SEND_BTN = '.Gk4oo6P9'
    CHAT_LIST_ITEM = '.MWrUXww6'
    CHAT_MATCHES = '.vkuiHorizontalCell__body'
    
    # ========== ФИЛЬТРЫ ==========
    
    FILTER_BTN = '.gPyaghhN'
    FILTER_AGE_SLIDER = '.vkuiSliderThumb__host'
    FILTER_GOAL = '.RWxPNm3S'
    FILTER_APPLY = 'button:has-text("Применить")'
    FILTER_SAVE = 'button:has-text("Сохранить")'
    
    # ========== НАСТРОЙКИ ПРОФИЛЯ ==========
    
    SETTINGS_BTN = '.vkuiInternalTappable'
    SETTINGS_BIO_INPUT = '.vkuiUnstyledTextField__host'
    SETTINGS_PHOTO = '.I7ZkiYCm'
    
    # ========== ОБЩИЕ КНОПКИ ==========
    
    BTN_DONE = 'button:has-text("Готово")'
    BTN_BACK = '.vkuiPanelHeaderButton__backVkcom'
    BTN_CANCEL = 'button:has-text("Отмена")'


class VKDatingHotkeys:
    """Горячие клавиши VK Dating"""
    
    LIKE = '.'        # Period
    DISLIKE = ','     # Comma
    PHOTO_NEXT = 'ArrowRight'
    PHOTO_PREV = 'ArrowLeft'


# Пример использования:
"""
from playwright.async_api import async_playwright
from vk_selectors import VKDatingSelectors as S, VKDatingHotkeys as K

async def main():
    # ... инициализация browser, page ...
    
    # Метод 1: Горячие клавиши (рекомендуется)
    await page.keyboard.press(K.LIKE)
    await page.keyboard.press(K.DISLIKE)
    
    # Метод 2: Клик по селектору в iframe
    frame = page.frame_locator('iframe').first
    await frame.locator(S.BTN_LIKE).click()
    
    # Метод 3: Переход по вкладкам
    await frame.locator(S.TAB_CHATS).click()
    
    # Метод 4: Отправка сообщения
    await frame.locator(S.CHAT_INPUT).fill("Привет!")
    await frame.locator(S.CHAT_SEND_BTN).click()
"""
