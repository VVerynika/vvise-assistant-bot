import os
import time
import signal
import sys
import threading
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем наши модули
from problem_analyzer import ProblemAnalyzer
from google_sheets_manager import GoogleSheetsManager
from slack_integration import SlackIntegration
from clickup_integration import ClickUpIntegration
from telegram_bot import TelegramBot

# Глобальные переменные для остановки
stop_event = threading.Event()

def handle_signal(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    print(f"\n📡 Получен сигнал {signum}, завершаю работу...")
    stop_event.set()

def setup_signal_handlers():
    """Настраивает обработчики сигналов"""
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

def initialize_components():
    """Инициализирует все компоненты системы"""
    print("🚀 Инициализация системы...")
    
    # Инициализируем анализатор проблем
    analyzer = ProblemAnalyzer()
    print("✅ Анализатор проблем инициализирован")
    
    # Инициализируем Google Sheets менеджер
    sheets_manager = GoogleSheetsManager()
    if sheets_manager.sheet:
        print("✅ Google Sheets подключен")
    else:
        print("⚠️ Google Sheets не подключен")
    
    # Инициализируем интеграции
    slack_integration = SlackIntegration(analyzer=analyzer, sheets_manager=sheets_manager)
    clickup_integration = ClickUpIntegration(analyzer=analyzer, sheets_manager=sheets_manager)
    
    # Инициализируем Telegram бота
    telegram_bot = TelegramBot(
        analyzer=analyzer,
        sheets_manager=sheets_manager,
        slack_integration=slack_integration,
        clickup_integration=clickup_integration
    )
    
    return analyzer, sheets_manager, slack_integration, clickup_integration, telegram_bot

def run_component(component, component_name, stop_event):
    """Запускает компонент в отдельном потоке"""
    try:
        print(f"🔄 Запуск {component_name}...")
        if hasattr(component, 'run'):
            component.run()
        elif hasattr(component, 'run_polling'):
            component.run_polling()
        else:
            print(f"⚠️ Компонент {component_name} не имеет метода run")
    except Exception as e:
        print(f"❌ Ошибка в {component_name}: {e}")
    finally:
        print(f"🛑 {component_name} остановлен")

def main():
    """Основная функция"""
    print("🤖 Запуск бота-помощника для анализа проблем")
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Настраиваем обработчики сигналов
    setup_signal_handlers()
    
    try:
        # Инициализируем компоненты
        analyzer, sheets_manager, slack_integration, clickup_integration, telegram_bot = initialize_components()
        
        print("\n📋 Статус компонентов:")
        print(f"   🔍 Анализатор проблем: {'✅' if analyzer else '❌'}")
        print(f"   📊 Google Sheets: {'✅' if sheets_manager and sheets_manager.sheet else '❌'}")
        print(f"   💬 Slack: {'✅' if slack_integration and slack_integration.token else '❌'}")
        print(f"   📋 ClickUp: {'✅' if clickup_integration and clickup_integration.token else '❌'}")
        print(f"   🤖 Telegram: {'✅' if telegram_bot and telegram_bot.token else '❌'}")
        
        # Запускаем компоненты в отдельных потоках
        threads = []
        
        # Telegram бот
        if telegram_bot and telegram_bot.token:
            t_telegram = threading.Thread(
                target=run_component,
                args=(telegram_bot, "Telegram бот", stop_event),
                daemon=True
            )
            t_telegram.start()
            threads.append(t_telegram)
            print("✅ Telegram бот запущен")
        
        # Slack интеграция
        if slack_integration and slack_integration.token:
            t_slack = threading.Thread(
                target=run_component,
                args=(slack_integration, "Slack интеграция", stop_event),
                daemon=True
            )
            t_slack.start()
            threads.append(t_slack)
            print("✅ Slack интеграция запущена")
        
        # ClickUp интеграция
        if clickup_integration and clickup_integration.token:
            t_clickup = threading.Thread(
                target=run_component,
                args=(clickup_integration, "ClickUp интеграция", stop_event),
                daemon=True
            )
            t_clickup.start()
            threads.append(t_clickup)
            print("✅ ClickUp интеграция запущена")
        
        print(f"\n🚀 Система запущена. Запущено потоков: {len(threads)}")
        print("💡 Используйте Ctrl+C для остановки")
        
        # Основной цикл
        while not stop_event.is_set():
            try:
                # Проверяем статус потоков
                active_threads = [t for t in threads if t.is_alive()]
                if len(active_threads) < len(threads):
                    print(f"⚠️ Некоторые потоки остановлены. Активных: {len(active_threads)}/{len(threads)}")
                
                # Периодически обновляем дашборд
                if sheets_manager and analyzer and not stop_event.is_set():
                    try:
                        all_problems = analyzer.get_problems_by_status()
                        if all_problems:
                            sheets_manager.sync_problems_to_sheets(all_problems)
                            sheets_manager.update_dashboard(analyzer)
                            print(f"📊 Дашборд обновлен. Проблем: {len(all_problems)}")
                    except Exception as e:
                        print(f"⚠️ Ошибка обновления дашборда: {e}")
                
                # Ждем
                time.sleep(300)  # 5 минут
                
            except KeyboardInterrupt:
                print("\n🛑 Получен сигнал остановки...")
                stop_event.set()
                break
            except Exception as e:
                print(f"⚠️ Ошибка в основном цикле: {e}")
                time.sleep(60)
        
        print("\n🔄 Остановка системы...")
        
        # Ждем завершения потоков
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=10)
                if thread.is_alive():
                    print(f"⚠️ Поток {thread.name} не завершился корректно")
        
        print("✅ Система остановлена")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
