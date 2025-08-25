#!/usr/bin/env python3
"""
Скрипт для быстрого запуска и настройки системы
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_banner():
    """Выводит баннер системы"""
    print("=" * 60)
    print("🤖 БОТ-ПОМОЩНИК ДЛЯ АНАЛИЗА ПРОБЛЕМ")
    print("=" * 60)
    print("🚀 Система автоматического анализа данных из Slack и ClickUp")
    print("📊 Выявление дублирующихся и связанных проблем")
    print("🔔 Уведомления через Telegram и другие каналы")
    print("📈 Отчеты в Google Sheets")
    print("=" * 60)

def check_python_version():
    """Проверяет версию Python"""
    print("🔍 Проверка версии Python...")
    
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8+")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_dependencies():
    """Проверяет и устанавливает зависимости"""
    print("\n🔍 Проверка зависимостей...")
    
    try:
        # Проверяем pip
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      check=True, capture_output=True)
        print("✅ pip доступен")
        
        # Устанавливаем зависимости
        print("📦 Установка зависимостей...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Зависимости установлены")
            return True
        else:
            print(f"❌ Ошибка установки зависимостей: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки зависимостей: {e}")
        return False

def check_environment():
    """Проверяет переменные окружения"""
    print("\n🔍 Проверка переменных окружения...")
    
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
        print(f"\n⚠️ Отсутствуют переменные: {', '.join(missing_vars)}")
        print("📝 Создайте файл .env на основе .env.example")
        return False
    
    print("✅ Все необходимые переменные настроены")
    return True

def create_directories():
    """Создает необходимые директории"""
    print("\n📁 Создание директорий...")
    
    directories = ['logs', 'data', 'static', 'config', 'backups']
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Создана директория: {dir_name}")
        else:
            print(f"✅ Директория существует: {dir_name}")
    
    return True

def run_tests():
    """Запускает тесты системы"""
    print("\n🧪 Запуск тестов системы...")
    
    try:
        result = subprocess.run([sys.executable, "test_system.py"],
                              capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Ошибки:", result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Ошибка запуска тестов: {e}")
        return False

def start_system():
    """Запускает систему"""
    print("\n🚀 Запуск системы...")
    
    try:
        # Запускаем в фоновом режиме
        process = subprocess.Popen([sys.executable, "run_background.py"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Ждем немного для инициализации
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ Система запущена в фоновом режиме")
            
            # Сохраняем PID
            with open("bot.pid", "w") as f:
                f.write(str(process.pid))
            
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Ошибка запуска: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        return False

def show_status():
    """Показывает статус системы"""
    print("\n📊 Статус системы...")
    
    try:
        result = subprocess.run([sys.executable, "manage.py", "status"],
                              capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Ошибки:", result.stderr)
            
    except Exception as e:
        print(f"❌ Ошибка получения статуса: {e}")

def show_next_steps():
    """Показывает следующие шаги"""
    print("\n" + "=" * 60)
    print("🎉 СИСТЕМА УСПЕШНО НАСТРОЕНА!")
    print("=" * 60)
    print("\n📋 Доступные команды:")
    print("  ./start.sh start              # Запуск системы")
    print("  ./start.sh stop               # Остановка системы")
    print("  ./start.sh status             # Статус системы")
    print("  ./start.sh logs               # Просмотр логов")
    print("  ./start.sh test               # Запуск тестов")
    print("  python3 manage.py status      # Статус через Python")
    print("  python3 monitor.py --status   # Мониторинг системы")
    
    print("\n🌐 Веб-интерфейс:")
    print("  http://localhost:8000         # Основной интерфейс")
    
    print("\n📱 Telegram бот:")
    print("  Используйте команды: /start, /help, /status")
    
    print("\n📊 Google Sheets:")
    print("  Проверьте таблицу по ID из переменной GOOGLE_SHEET_ID")
    
    print("\n🔧 Управление:")
    print("  python3 config.py --validate  # Валидация конфигурации")
    print("  python3 notifications.py --test # Тест уведомлений")
    
    print("\n📚 Документация:")
    print("  README.md                      # Основная документация")
    print("  .env.example                   # Пример переменных окружения")
    
    print("\n" + "=" * 60)

def main():
    """Основная функция"""
    print_banner()
    
    # Проверяем версию Python
    if not check_python_version():
        sys.exit(1)
    
    # Устанавливаем зависимости
    if not check_dependencies():
        print("❌ Не удалось установить зависимости")
        sys.exit(1)
    
    # Проверяем переменные окружения
    if not check_environment():
        print("\n⚠️ Настройте переменные окружения и запустите скрипт снова")
        print("📝 Пример: cp .env.example .env && nano .env")
        sys.exit(1)
    
    # Создаем директории
    if not create_directories():
        print("❌ Не удалось создать директории")
        sys.exit(1)
    
    # Запускаем тесты
    if not run_tests():
        print("⚠️ Тесты не пройдены, но продолжаем...")
    
    # Запускаем систему
    if start_system():
        # Показываем статус
        time.sleep(2)
        show_status()
        
        # Показываем следующие шаги
        show_next_steps()
    else:
        print("❌ Не удалось запустить систему")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Запуск прерван пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)