#!/usr/bin/env python3
"""
Скрипт для запуска системы в фоновом режиме
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime
from pathlib import Path

# Настройка логирования
def setup_logging():
    """Настраивает логирование"""
    log_dir = Path("/workspace/logs")
    log_dir.mkdir(exist_ok=True)
    
    # Основной лог файл
    main_log = log_dir / "main.log"
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Файловый обработчик
    file_handler = logging.FileHandler(main_log, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

def run_component(component_name: str, component_func, logger):
    """Запускает компонент в отдельном потоке"""
    try:
        logger.info(f"Запуск компонента: {component_name}")
        component_func()
    except Exception as e:
        logger.error(f"Ошибка в компоненте {component_name}: {e}")
        logger.exception("Детали ошибки:")

def main():
    """Основная функция"""
    # Настраиваем логирование
    logger = setup_logging()
    logger.info("🚀 Запуск системы в фоновом режиме...")
    
    try:
        # Импортируем модули
        from problem_analyzer import ProblemAnalyzer
        from google_sheets_manager import GoogleSheetsManager
        from slack_integration import SlackIntegration
        from clickup_integration import ClickUpIntegration
        from telegram_bot import TelegramBot
        
        logger.info("✅ Все модули импортированы")
        
        # Инициализируем компоненты
        logger.info("🔧 Инициализация компонентов...")
        
        analyzer = ProblemAnalyzer()
        logger.info("✅ ProblemAnalyzer инициализирован")
        
        sheets_manager = GoogleSheetsManager()
        logger.info("✅ GoogleSheetsManager инициализирован")
        
        slack_integration = SlackIntegration(analyzer=analyzer, sheets_manager=sheets_manager)
        logger.info("✅ SlackIntegration инициализирован")
        
        clickup_integration = ClickUpIntegration(analyzer=analyzer, sheets_manager=sheets_manager)
        logger.info("✅ ClickUpIntegration инициализирован")
        
        telegram_bot = TelegramBot(
            analyzer=analyzer,
            sheets_manager=sheets_manager,
            slack_integration=slack_integration,
            clickup_integration=clickup_integration
        )
        logger.info("✅ TelegramBot инициализирован")
        
        # Флаг для остановки
        stop_event = threading.Event()
        
        def signal_handler(signum, frame):
            """Обработчик сигналов для graceful shutdown"""
            logger.info(f"Получен сигнал {signum}, начинаем остановку...")
            stop_event.set()
        
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Запускаем компоненты в отдельных потоках
        threads = []
        
        # Slack интеграция
        slack_thread = threading.Thread(
            target=run_component,
            args=("Slack", slack_integration.run, logger),
            daemon=True
        )
        threads.append(slack_thread)
        slack_thread.start()
        
        # ClickUp интеграция
        clickup_thread = threading.Thread(
            target=run_component,
            args=("ClickUp", clickup_integration.run, logger),
            daemon=True
        )
        threads.append(clickup_thread)
        clickup_thread.start()
        
        # Telegram бот
        telegram_thread = threading.Thread(
            target=run_component,
            args=("Telegram", telegram_bot.run_polling, logger),
            daemon=True
        )
        threads.append(telegram_thread)
        telegram_thread.start()
        
        logger.info("✅ Все компоненты запущены в фоновом режиме")
        
        # Основной цикл мониторинга
        while not stop_event.is_set():
            try:
                # Обновляем дашборд каждые 5 минут
                time.sleep(300)
                
                if not stop_event.is_set():
                    logger.info("📊 Обновление дашборда...")
                    try:
                        sheets_manager.update_dashboard(analyzer)
                        logger.info("✅ Дашборд обновлен")
                    except Exception as e:
                        logger.error(f"Ошибка обновления дашборда: {e}")
                
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                time.sleep(60)
        
        logger.info("🛑 Получен сигнал остановки, ожидаем завершения потоков...")
        
        # Ждем завершения потоков
        for thread in threads:
            thread.join(timeout=30)
            if thread.is_alive():
                logger.warning(f"Поток {thread.name} не завершился в течение 30 секунд")
        
        logger.info("✅ Система остановлена")
        
    except ImportError as e:
        logger.error(f"Ошибка импорта модуля: {e}")
        logger.error("Убедитесь, что все зависимости установлены")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        logger.exception("Детали ошибки:")
        sys.exit(1)

if __name__ == "__main__":
    main()