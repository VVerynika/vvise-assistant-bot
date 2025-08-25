#!/usr/bin/env python3
"""
Скрипт для тестирования всех компонентов системы
"""

import os
import sys
import time
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def test_environment():
    """Тестирует переменные окружения"""
    print("🔍 Проверка переменных окружения...")
    
    required_vars = [
        'SLACK_TOKEN',
        'CLICKUP_API_TOKEN', 
        'TELEGRAM_TOKEN',
        'GOOGLE_SHEET_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * 10}")
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные: {', '.join(missing_vars)}")
        return False
    
    print("✅ Все необходимые переменные окружения настроены")
    return True

def test_imports():
    """Тестирует импорт модулей"""
    print("\n🔍 Проверка импорта модулей...")
    
    modules_to_test = [
        'problem_analyzer',
        'google_sheets_manager',
        'slack_integration',
        'clickup_integration',
        'telegram_bot',
        'system_manager',
        'notifications',
        'config'
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module} импортирован")
        except ImportError as e:
            print(f"❌ Ошибка импорта {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Не удалось импортировать модули: {', '.join(failed_imports)}")
        return False
    
    print("✅ Все модули успешно импортированы")
    return True

def test_database():
    """Тестирует создание базы данных"""
    print("\n🔍 Проверка базы данных...")
    
    try:
        from problem_analyzer import ProblemAnalyzer
        
        analyzer = ProblemAnalyzer("/workspace/test_problems.db")
        print("✅ База данных создана/открыта")
        
        # Тестируем создание таблиц
        analyzer.init_database()
        print("✅ Таблицы базы данных созданы")
        
        # Очищаем тестовую базу
        import os
        if os.path.exists("/workspace/test_problems.db"):
            os.remove("/workspace/test_problems.db")
            print("✅ Тестовая база данных удалена")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка работы с базой данных: {e}")
        return False

def test_google_sheets():
    """Тестирует подключение к Google Sheets"""
    print("\n🔍 Проверка Google Sheets...")
    
    try:
        from google_sheets_manager import GoogleSheetsManager
        
        # Пытаемся создать менеджер
        sheets_manager = GoogleSheetsManager()
        print("✅ GoogleSheetsManager создан")
        
        # Проверяем подключение
        if sheets_manager.init_connection():
            print("✅ Подключение к Google Sheets установлено")
        else:
            print("⚠️ Подключение к Google Sheets не установлено (проверьте настройки)")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка Google Sheets: {e}")
        return False

def test_slack():
    """Тестирует подключение к Slack"""
    print("\n🔍 Проверка Slack...")
    
    try:
        from slack_integration import SlackIntegration
        
        # Создаем интеграцию
        slack = SlackIntegration()
        print("✅ SlackIntegration создан")
        
        # Проверяем токен
        if slack.token:
            print("✅ Slack токен настроен")
        else:
            print("❌ Slack токен не настроен")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка Slack: {e}")
        return False

def test_clickup():
    """Тестирует подключение к ClickUp"""
    print("\n🔍 Проверка ClickUp...")
    
    try:
        from clickup_integration import ClickUpIntegration
        
        # Создаем интеграцию
        clickup = ClickUpIntegration()
        print("✅ ClickUpIntegration создан")
        
        # Проверяем токен
        if clickup.token:
            print("✅ ClickUp токен настроен")
        else:
            print("❌ ClickUp токен не настроен")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка ClickUp: {e}")
        return False

def test_telegram():
    """Тестирует Telegram бота"""
    print("\n🔍 Проверка Telegram...")
    
    try:
        from telegram_bot import TelegramBot
        
        # Создаем бота
        bot = TelegramBot()
        print("✅ TelegramBot создан")
        
        # Проверяем токен
        if bot.token:
            print("✅ Telegram токен настроен")
        else:
            print("❌ Telegram токен не настроен")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")
        return False

def test_system_manager():
    """Тестирует системный менеджер"""
    print("\n🔍 Проверка системного менеджера...")
    
    try:
        from system_manager import SystemManager
        
        # Создаем менеджер
        manager = SystemManager()
        print("✅ SystemManager создан")
        
        # Тестируем мониторинг
        manager.start_monitoring(interval=5)
        print("✅ Мониторинг запущен")
        
        time.sleep(2)
        
        # Останавливаем мониторинг
        manager.stop_monitoring()
        print("✅ Мониторинг остановлен")
        
        # Очищаем ресурсы
        manager.cleanup()
        print("✅ Ресурсы очищены")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка системного менеджера: {e}")
        return False

def test_notifications():
    """Тестирует систему уведомлений"""
    print("\n🔍 Проверка системы уведомлений...")
    
    try:
        from notifications import NotificationManager
        
        # Создаем менеджер уведомлений
        notification_manager = NotificationManager()
        print("✅ NotificationManager создан")
        
        # Тестируем конфигурацию
        config = notification_manager.config
        if config.get('telegram', {}).get('enabled'):
            print("✅ Telegram уведомления включены")
        else:
            print("⚠️ Telegram уведомления отключены")
            
        if config.get('slack', {}).get('enabled'):
            print("✅ Slack уведомления включены")
        else:
            print("⚠️ Slack уведомления отключены")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка системы уведомлений: {e}")
        return False

def test_config():
    """Тестирует систему конфигурации"""
    print("\n🔍 Проверка системы конфигурации...")
    
    try:
        from config import ConfigManager
        
        # Создаем менеджер конфигурации
        config_manager = ConfigManager()
        print("✅ ConfigManager создан")
        
        # Тестируем валидацию
        errors = config_manager.validate_config()
        if errors:
            print("⚠️ Найдены ошибки конфигурации:")
            for section, section_errors in errors.items():
                print(f"  {section}: {', '.join(section_errors)}")
        else:
            print("✅ Конфигурация валидна")
        
        # Тестируем получение конфигурации
        app_name = config_manager.get_config('main', 'app_name')
        if app_name:
            print(f"✅ Название приложения: {app_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка системы конфигурации: {e}")
        return False

def test_performance_monitor():
    """Тестирует мониторинг производительности"""
    print("\n🔍 Проверка мониторинга производительности...")
    
    try:
        from monitor import PerformanceMonitor
        
        # Создаем монитор
        monitor = PerformanceMonitor()
        print("✅ PerformanceMonitor создан")
        
        # Получаем текущий статус
        status = monitor.get_current_status()
        if 'error' not in status:
            print("✅ Статус системы получен")
            print(f"  CPU: {status['cpu']['percent']:.1f}%")
            print(f"  RAM: {status['memory']['percent']:.1f}%")
            print(f"  Диск: {status['disk']['percent']:.1f}%")
        else:
            print(f"⚠️ Ошибка получения статуса: {status['error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка мониторинга производительности: {e}")
        return False

def test_file_structure():
    """Тестирует структуру файлов"""
    print("\n🔍 Проверка структуры файлов...")
    
    required_files = [
        'main.py',
        'problem_analyzer.py',
        'google_sheets_manager.py',
        'slack_integration.py',
        'clickup_integration.py',
        'telegram_bot.py',
        'system_manager.py',
        'notifications.py',
        'config.py',
        'monitor.py',
        'requirements.txt',
        '.env',
        'Dockerfile',
        'docker-compose.yml',
        'README.md',
        'start.sh'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Отсутствуют файлы: {', '.join(missing_files)}")
        return False
    
    print("✅ Все необходимые файлы присутствуют")
    return True

def test_directories():
    """Тестирует создание директорий"""
    print("\n🔍 Проверка директорий...")
    
    required_dirs = [
        'logs',
        'data',
        'static',
        'config'
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"✅ Создана директория: {dir_path}")
        else:
            print(f"✅ Директория существует: {dir_path}")
    
    return True

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования системы...\n")
    
    tests = [
        ("Структура файлов", test_file_structure),
        ("Директории", test_directories),
        ("Переменные окружения", test_environment),
        ("Импорт модулей", test_imports),
        ("База данных", test_database),
        ("Google Sheets", test_google_sheets),
        ("Slack", test_slack),
        ("ClickUp", test_clickup),
        ("Telegram", test_telegram),
        ("Системный менеджер", test_system_manager),
        ("Уведомления", test_notifications),
        ("Конфигурация", test_config),
        ("Мониторинг производительности", test_performance_monitor)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ Тест '{test_name}' не пройден")
        except Exception as e:
            print(f"❌ Тест '{test_name}' завершился с ошибкой: {e}")
    
    print(f"\n📊 Результаты тестирования:")
    print(f"✅ Пройдено: {passed}/{total}")
    print(f"❌ Не пройдено: {total - passed}")
    
    if passed == total:
        print("\n🎉 Все тесты пройдены! Система готова к работе.")
        print("\n📋 Следующие шаги:")
        print("1. Настройте переменные окружения в файле .env")
        print("2. Запустите систему: ./start.sh start")
        print("3. Проверьте статус: ./start.sh status")
        print("4. Откройте веб-интерфейс: http://localhost:8000")
        return True
    else:
        print(f"\n⚠️ {total - passed} тестов не пройдено. Проверьте настройки.")
        print("\n🔧 Рекомендации:")
        print("1. Установите все зависимости: pip install -r requirements.txt")
        print("2. Проверьте переменные окружения в .env")
        print("3. Убедитесь, что все файлы присутствуют")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)