"""
Скрипт настройки VK cookies для тестирования
Запуск: python setup_env.py
"""
import os

def main():
    print("=" * 50)
    print("🔧 Настройка VK Dating Bot")
    print("=" * 50)
    print()
    print("Этот скрипт создаст файл .env с вашими VK cookies.")
    print("Cookies нужны для авторизации в VK Dating.")
    print()
    print("Как получить cookies:")
    print("1. Откройте vk.com в браузере")
    print("2. F12 → Application → Cookies → https://vk.com")
    print("3. Скопируйте значения remixsid и remixnsid")
    print()
    
    remixsid = input("Введите remixsid: ").strip()
    if not remixsid:
        print("❌ remixsid обязателен!")
        return
    
    remixnsid = input("Введите remixnsid (или Enter чтобы пропустить): ").strip()
    
    # Создаём .env
    env_content = f"""# VK Dating Bot - Environment Variables
# Сгенерировано автоматически

# VK Cookies (НЕ КОММИТИТЬ В GIT!)
VK_REMIXSID={remixsid}
VK_REMIXNSID={remixnsid}

# Опционально - для полного воркера
# DATABASE_URL=postgresql://user:pass@localhost:5432/dating_bot
# REDIS_URL=redis://localhost:6379/0
"""
    
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    
    # Проверяем существует ли файл
    if os.path.exists(env_path):
        overwrite = input(f"\n⚠️ Файл .env уже существует. Перезаписать? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("❌ Отменено")
            return
    
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print()
    print("=" * 50)
    print(f"✅ Файл создан: {env_path}")
    print("=" * 50)
    print()
    print("Теперь можно запустить тест:")
    print("  python test_vk_dating.py")
    print()


if __name__ == "__main__":
    main()
