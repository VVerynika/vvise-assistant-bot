import os
import time
import telebot
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from problem_analyzer import ProblemAnalyzer
from google_sheets_manager import GoogleSheetsManager
from slack_integration import SlackIntegration
from clickup_integration import ClickUpIntegration

class TelegramBot:
    def __init__(self, token: str = None, analyzer: ProblemAnalyzer = None, 
                 sheets_manager: GoogleSheetsManager = None, 
                 slack_integration: SlackIntegration = None,
                 clickup_integration: ClickUpIntegration = None):
        self.token = token or os.getenv("TELEGRAM_TOKEN")
        self.bot = telebot.TeleBot(self.token) if self.token else None
        self.analyzer = analyzer
        self.sheets_manager = sheets_manager
        self.slack_integration = slack_integration
        self.clickup_integration = clickup_integration
        self.authorized_users = self._load_authorized_users()
        
        if self.bot:
            self.register_handlers()
    
    def _load_authorized_users(self) -> List[str]:
        """Загружает список авторизованных пользователей"""
        authorized_users = os.getenv("TELEGRAM_AUTHORIZED_USERS", "")
        if authorized_users:
            return [user.strip() for user in authorized_users.split(",")]
        return []
    
    def _is_authorized(self, user_id: int) -> bool:
        """Проверяет, авторизован ли пользователь"""
        if not self.authorized_users:
            return True  # Если список не задан, разрешаем всем
        return str(user_id) in self.authorized_users
    
    def _safe_text(self, message) -> str:
        """Безопасно извлекает текст из сообщения"""
        try:
            return getattr(message, 'text', None) or getattr(message, 'caption', None) or ""
        except Exception:
            return ""
    
    def register_handlers(self):
        """Регистрирует обработчики команд"""
        if not self.bot:
            return
        
        @self.bot.message_handler(commands=['start', 'help'])
        def handle_start(message):
            if not self._is_authorized(message.from_user.id):
                self.bot.reply_to(message, "⛔ У вас нет доступа к этому боту.")
                return
            
            help_text = """
🤖 Бот-помощник для анализа проблем и задач

📋 Доступные команды:
/status - Статус системы
/report - Отчет по проблемам
/problems - Список проблем
/forgotten - Забытые проблемы
/sync - Синхронизация с Google Sheets
/cleanup - Очистка старых данных
/restart - Перезапуск анализа
/help - Это сообщение

💡 Используйте команды для управления системой
            """
            self.bot.reply_to(message, help_text.strip())
            
            # Логируем в Google Sheets
            if self.sheets_manager:
                self.sheets_manager.log_message(message, "telegram")
        
        @self.bot.message_handler(commands=['status'])
        def handle_status(message):
            if not self._is_authorized(message.from_user.id):
                return
            
            try:
                status_text = "📊 Статус системы:\n\n"
                
                # Статус анализатора
                if self.analyzer:
                    report = self.analyzer.generate_report()
                    status_text += f"🔍 Анализатор проблем: ✅ Активен\n"
                    status_text += f"📈 Всего проблем: {report['total_problems']}\n"
                    status_text += f"🆕 Новые: {report['by_status'].get('new', 0)}\n"
                    status_text += f"⚡ В работе: {report['by_status'].get('in_progress', 0)}\n"
                    status_text += f"✅ Решенные: {report['by_status'].get('resolved', 0)}\n"
                    status_text += f"🔄 Дубликаты: {report['by_status'].get('duplicate', 0)}\n\n"
                else:
                    status_text += "🔍 Анализатор проблем: ❌ Не активен\n\n"
                
                # Статус интеграций
                if self.slack_integration and self.slack_integration.token:
                    status_text += "💬 Slack интеграция: ✅ Активна\n"
                else:
                    status_text += "💬 Slack интеграция: ❌ Не активна\n"
                
                if self.clickup_integration and self.clickup_integration.token:
                    status_text += "📋 ClickUp интеграция: ✅ Активна\n"
                else:
                    status_text += "📋 ClickUp интеграция: ❌ Не активна\n"
                
                if self.sheets_manager and self.sheets_manager.sheet:
                    status_text += "📊 Google Sheets: ✅ Подключен\n"
                else:
                    status_text += "📊 Google Sheets: ❌ Не подключен\n"
                
                status_text += f"\n⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.bot.reply_to(message, status_text)
                
            except Exception as e:
                self.bot.reply_to(message, f"❌ Ошибка получения статуса: {e}")
        
        @self.bot.message_handler(commands=['report'])
        def handle_report(message):
            if not self._is_authorized(message.from_user.id):
                return
            
            try:
                if not self.analyzer:
                    self.bot.reply_to(message, "❌ Анализатор проблем не доступен")
                    return
                
                report = self.analyzer.generate_report()
                
                report_text = "📊 Отчет по проблемам:\n\n"
                report_text += f"🔢 Общее количество: {report['total_problems']}\n\n"
                
                # Статистика по статусам
                report_text += "📋 По статусам:\n"
                for status, count in report['by_status'].items():
                    status_emoji = {
                        'new': '🆕',
                        'in_progress': '⚡',
                        'resolved': '✅',
                        'duplicate': '🔄'
                    }.get(status, '📌')
                    report_text += f"  {status_emoji} {status}: {count}\n"
                
                # Статистика по приоритетам
                report_text += "\n🚨 По приоритетам:\n"
                for priority, count in report['by_priority'].items():
                    priority_emoji = {
                        1: '🔴',
                        2: '🟠',
                        3: '🟡',
                        4: '🟢',
                        5: '⚪'
                    }.get(priority, '📌')
                    report_text += f"  {priority_emoji} {priority}: {count}\n"
                
                # Статистика по источникам
                report_text += "\n📡 По источникам:\n"
                for source, count in report['by_source'].items():
                    source_emoji = {
                        'slack': '💬',
                        'clickup': '📋',
                        'telegram': '🤖'
                    }.get(source, '📌')
                    report_text += f"  {source_emoji} {source}: {count}\n"
                
                report_text += f"\n⏰ Сгенерирован: {report['generated_at']}"
                
                self.bot.reply_to(message, report_text)
                
            except Exception as e:
                self.bot.reply_to(message, f"❌ Ошибка генерации отчета: {e}")
        
        @self.bot.message_handler(commands=['problems'])
        def handle_problems(message):
            if not self._is_authorized(message.from_user.id):
                return
            
            try:
                if not self.analyzer:
                    self.bot.reply_to(message, "❌ Анализатор проблем не доступен")
                    return
                
                # Парсим аргументы команды
                args = self._safe_text(message).split()[1:] if len(self._safe_text(message).split()) > 1 else []
                
                if args and args[0] in ['new', 'in_progress', 'resolved', 'duplicate']:
                    status = args[0]
                    problems = self.analyzer.get_problems_by_status(status)
                    title = f"📋 Проблемы со статусом: {status}"
                else:
                    problems = self.analyzer.get_problems_by_status()
                    title = "📋 Все проблемы"
                
                if not problems:
                    self.bot.reply_to(message, f"📭 {title}\n\nПроблемы не найдены")
                    return
                
                # Ограничиваем количество проблем для отображения
                display_problems = problems[:10]
                
                problems_text = f"{title}\n\n"
                
                for i, problem in enumerate(display_problems, 1):
                    priority_emoji = {
                        1: '🔴',
                        2: '🟠',
                        3: '🟡',
                        4: '🟢',
                        5: '⚪'
                    }.get(problem.priority, '📌')
                    
                    status_emoji = {
                        'new': '🆕',
                        'in_progress': '⚡',
                        'resolved': '✅',
                        'duplicate': '🔄'
                    }.get(problem.status, '📌')
                    
                    problems_text += f"{i}. {priority_emoji} {status_emoji} {problem.title[:50]}...\n"
                    problems_text += f"   👤 {problem.user} | 📅 {problem.timestamp.strftime('%m-%d %H:%M')}\n"
                    problems_text += f"   🏷️ {', '.join(problem.tags[:3])}\n\n"
                
                if len(problems) > 10:
                    problems_text += f"... и еще {len(problems) - 10} проблем"
                
                self.bot.reply_to(message, problems_text)
                
            except Exception as e:
                self.bot.reply_to(message, f"❌ Ошибка получения проблем: {e}")
        
        @self.bot.message_handler(commands=['forgotten'])
        def handle_forgotten(message):
            if not self._is_authorized(message.from_user.id):
                return
            
            try:
                if not self.analyzer:
                    self.bot.reply_to(message, "❌ Анализатор проблем не доступен")
                    return
                
                # Парсим количество дней
                args = self._safe_text(message).split()[1:] if len(self._safe_text(message).split()) > 1 else []
                days = int(args[0]) if args and args[0].isdigit() else 7
                
                problems = self.analyzer.get_forgotten_problems(days)
                
                if not problems:
                    self.bot.reply_to(message, f"✅ Забытых проблем за последние {days} дней не найдено")
                    return
                
                forgotten_text = f"⏰ Забытые проблемы (за последние {days} дней):\n\n"
                
                for i, problem in enumerate(problems[:10], 1):
                    priority_emoji = {
                        1: '🔴',
                        2: '🟠',
                        3: '🟡',
                        4: '🟢',
                        5: '⚪'
                    }.get(problem.priority, '📌')
                    
                    forgotten_text += f"{i}. {priority_emoji} {problem.title[:50]}...\n"
                    forgotten_text += f"   👤 {problem.user} | 📅 {problem.last_updated.strftime('%m-%d %H:%M')}\n"
                    forgotten_text += f"   🏷️ {', '.join(problem.tags[:3])}\n\n"
                
                if len(problems) > 10:
                    forgotten_text += f"... и еще {len(problems) - 10} забытых проблем"
                
                self.bot.reply_to(message, forgotten_text)
                
            except Exception as e:
                self.bot.reply_to(message, f"❌ Ошибка получения забытых проблем: {e}")
        
        @self.bot.message_handler(commands=['sync'])
        def handle_sync(message):
            if not self._is_authorized(message.from_user.id):
                return
            
            try:
                if not self.sheets_manager or not self.analyzer:
                    self.bot.reply_to(message, "❌ Google Sheets или анализатор не доступны")
                    return
                
                self.bot.reply_to(message, "🔄 Начинаю синхронизацию с Google Sheets...")
                
                # Получаем все проблемы
                all_problems = self.analyzer.get_problems_by_status()
                
                # Синхронизируем с Google Sheets
                self.sheets_manager.sync_problems_to_sheets(all_problems)
                self.sheets_manager.update_dashboard(self.analyzer)
                
                self.bot.reply_to(message, f"✅ Синхронизация завершена! Обработано {len(all_problems)} проблем")
                
            except Exception as e:
                self.bot.reply_to(message, f"❌ Ошибка синхронизации: {e}")
        
        @self.bot.message_handler(commands=['cleanup'])
        def handle_cleanup(message):
            if not self._is_authorized(message.from_user.id):
                return
            
            try:
                if not self.analyzer:
                    self.bot.reply_to(message, "❌ Анализатор проблем не доступен")
                    return
                
                # Парсим количество дней
                args = self._safe_text(message).split()[1:] if len(self._safe_text(message).split()) > 1 else []
                days = int(args[0]) if args and args[0].isdigit() else 90
                
                self.bot.reply_to(message, f"🧹 Начинаю очистку данных старше {days} дней...")
                
                # Очищаем старые данные
                deleted_count = self.analyzer.cleanup_old_data(days)
                
                # Очищаем старые логи в Google Sheets
                if self.sheets_manager:
                    self.sheets_manager.cleanup_old_logs(30)
                
                self.bot.reply_to(message, f"✅ Очистка завершена! Удалено {deleted_count} записей")
                
            except Exception as e:
                self.bot.reply_to(message, f"❌ Ошибка очистки: {e}")
        
        @self.bot.message_handler(commands=['restart'])
        def handle_restart(message):
            if not self._is_authorized(message.from_user.id):
                return
            
            try:
                self.bot.reply_to(message, "🔄 Перезапускаю анализ...")
                
                # Перезапускаем анализ в отдельных потоках
                import threading
                
                if self.slack_integration:
                    slack_thread = threading.Thread(
                        target=self.slack_integration.run_initial_analysis,
                        daemon=True
                    )
                    slack_thread.start()
                
                if self.clickup_integration:
                    clickup_thread = threading.Thread(
                        target=self.clickup_integration.run_initial_analysis,
                        daemon=True
                    )
                    clickup_thread.start()
                
                self.bot.reply_to(message, "✅ Анализ перезапущен")
                
            except Exception as e:
                self.bot.reply_to(message, f"❌ Ошибка перезапуска: {e}")
        
        @self.bot.message_handler(func=lambda message: True)
        def echo_message(message):
            if not self._is_authorized(message.from_user.id):
                return
            
            text = self._safe_text(message)
            if text:
                # Простой поиск по проблемам
                if self.analyzer and len(text) > 3:
                    similar_problems = self.analyzer.find_similar_problems(text, threshold=0.3)
                    
                    if similar_problems:
                        response = f"🔍 Поиск по запросу '{text}':\n\n"
                        for problem_id, similarity in similar_problems[:5]:
                            problem = next((p for p in self.analyzer.get_problems_by_status() if p.id == problem_id), None)
                            if problem:
                                response += f"📌 {problem.title[:50]}...\n"
                                response += f"   Схожесть: {similarity:.2f}\n"
                                response += f"   Статус: {problem.status}\n\n"
                        
                        if len(similar_problems) > 5:
                            response += f"... и еще {len(similar_problems) - 5} результатов"
                        
                        self.bot.reply_to(message, response)
                    else:
                        self.bot.reply_to(message, f"🔍 По запросу '{text}' ничего не найдено")
                else:
                    self.bot.reply_to(message, "💡 Используйте команды для управления системой. /help для справки")
            
            # Логируем в Google Sheets
            if self.sheets_manager:
                self.sheets_manager.log_message(message, "telegram")
    
    def run_polling(self):
        """Запускает бота в режиме polling"""
        if not self.bot:
            print("Telegram бот не инициализирован (нет токена или ошибка инициализации)")
            return
        
        backoff_seconds = 5
        while True:
            try:
                print("Telegram бот запущен...")
                self.bot.polling(none_stop=True, interval=0, timeout=60)
                backoff_seconds = 5
            except Exception as e:
                is_api_exc = hasattr(telebot, 'apihelper') and isinstance(e, getattr(telebot.apihelper, 'ApiTelegramException', Exception))
                if is_api_exc and getattr(e, 'error_code', None) == 409:
                    print("[Telegram] 409 Conflict: другой инстанс getUpdates. Ретраю позже...")
                    time.sleep(min(backoff_seconds, 300))
                    backoff_seconds = min(backoff_seconds * 2, 300)
                    continue
                print(f"Ошибка в polling: {e}")
                time.sleep(min(backoff_seconds, 60))
                backoff_seconds = min(backoff_seconds * 2, 60)
    
    def send_notification(self, text: str, chat_id: str = None):
        """Отправляет уведомление в указанный чат"""
        if not self.bot:
            return False
        
        try:
            if chat_id:
                self.bot.send_message(chat_id, text)
            else:
                # Отправляем всем авторизованным пользователям
                for user_id in self.authorized_users:
                    try:
                        self.bot.send_message(user_id, text)
                    except Exception:
                        continue
            return True
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")
            return False
    
    def send_critical_alert(self, problem):
        """Отправляет критическое уведомление о проблеме"""
        if not self.bot:
            return
        
        alert_text = f"🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА!\n\n"
        alert_text += f"📌 {problem.title}\n"
        alert_text += f"🚨 Приоритет: {problem.priority}\n"
        alert_text += f"📡 Источник: {problem.source}\n"
        alert_text += f"👤 Пользователь: {problem.user}\n"
        alert_text += f"⏰ Время: {problem.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        alert_text += f"🏷️ Категория: {problem.category}\n\n"
        alert_text += f"Требует немедленного внимания!"
        
        self.send_notification(alert_text)