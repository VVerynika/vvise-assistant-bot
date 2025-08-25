import os
import time
import json
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from problem_analyzer import Problem, ProblemAnalyzer
from google_sheets_manager import GoogleSheetsManager

class SlackIntegration:
    def __init__(self, token: str = None, analyzer: ProblemAnalyzer = None, sheets_manager: GoogleSheetsManager = None):
        self.token = token or os.getenv("SLACK_TOKEN")
        self.client = WebClient(token=self.token) if self.token else None
        self.analyzer = analyzer
        self.sheets_manager = sheets_manager
        self.state_path = "/workspace/.slack_state.json"
        self.channels_cache = {}
        self.users_cache = {}
        
    def _load_state(self) -> Dict:
        """Загружает состояние мониторинга Slack"""
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "last_ts_by_channel": {},
            "last_processed_message": None,
            "channels_processed": set(),
            "users_processed": set()
        }
    
    def _save_state(self, state: Dict):
        """Сохраняет состояние мониторинга Slack"""
        try:
            # Преобразуем set в list для JSON сериализации
            state_copy = state.copy()
            state_copy["channels_processed"] = list(state_copy.get("channels_processed", []))
            state_copy["users_processed"] = list(state_copy.get("users_processed", []))
            
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state_copy, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения состояния Slack: {e}")
    
    def get_all_channels(self) -> List[Dict]:
        """Получает все каналы Slack"""
        if not self.client:
            return []
        
        channels = []
        try:
            result = self.client.conversations_list(
                types="public_channel,private_channel,mpim,im",
                limit=1000
            )
            channels.extend(result["channels"])
            
            # Обрабатываем пагинацию
            while result.get("response_metadata", {}).get("next_cursor"):
                result = self.client.conversations_list(
                    types="public_channel,private_channel,mpim,im",
                    limit=1000,
                    cursor=result["response_metadata"]["next_cursor"]
                )
                channels.extend(result["channels"])
                
        except SlackApiError as e:
            print(f"Ошибка получения каналов Slack: {e}")
        
        return channels
    
    def get_channel_history(self, channel_id: str, oldest_ts: str = None, limit: int = 1000) -> List[Dict]:
        """Получает историю канала"""
        if not self.client:
            return []
        
        messages = []
        try:
            kwargs = {
                "channel": channel_id,
                "limit": limit
            }
            if oldest_ts:
                kwargs["oldest"] = oldest_ts
            
            result = self.client.conversations_history(**kwargs)
            messages.extend(result["messages"])
            
            # Обрабатываем пагинацию
            while result.get("response_metadata", {}).get("next_cursor"):
                kwargs["cursor"] = result["response_metadata"]["next_cursor"]
                result = self.client.conversations_history(**kwargs)
                messages.extend(result["messages"])
                
        except SlackApiError as e:
            print(f"Ошибка получения истории канала {channel_id}: {e}")
        
        return messages
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Получает информацию о пользователе"""
        if not self.client or user_id in self.users_cache:
            return self.users_cache.get(user_id)
        
        try:
            result = self.client.users_info(user=user_id)
            user_info = result["user"]
            self.users_cache[user_id] = user_info
            return user_info
        except SlackApiError:
            return None
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """Получает информацию о канале"""
        if not self.client or channel_id in self.channels_cache:
            return self.channels_cache.get(channel_id)
        
        try:
            result = self.client.conversations_info(channel=channel_id)
            channel_info = result["channel"]
            self.channels_cache[channel_id] = channel_info
            return channel_info
        except SlackApiError:
            return None
    
    def analyze_slack_message(self, message: Dict, channel_info: Dict) -> Optional[Problem]:
        """Анализирует сообщение Slack и создает объект проблемы"""
        try:
            # Пропускаем системные сообщения
            if message.get("subtype") in ["bot_message", "channel_join", "channel_leave"]:
                return None
            
            text = message.get("text", "")
            if not text or len(text.strip()) < 10:  # Минимальная длина для анализа
                return None
            
            # Определяем тип канала
            channel_type = "public"
            if channel_info.get("is_private"):
                channel_type = "private"
            elif channel_info.get("is_mpim"):
                channel_type = "group_dm"
            elif channel_info.get("is_im"):
                channel_type = "direct_message"
            
            # Анализируем текст
            analysis = self.analyzer.analyze_text(text) if self.analyzer else {}
            
            # Создаем ID проблемы
            problem_id = hashlib.md5(f"slack_{message['ts']}_{message.get('user', 'unknown')}".encode()).hexdigest()
            
            # Получаем информацию о пользователе
            user_info = self.get_user_info(message.get("user", ""))
            user_name = user_info.get("real_name", user_info.get("name", "Unknown")) if user_info else "Unknown"
            
            # Определяем приоритет на основе анализа и типа канала
            priority = analysis.get("priority", 3)
            if channel_type == "direct_message":
                priority = min(priority, 2)  # Личные сообщения имеют повышенный приоритет
            
            # Создаем объект проблемы
            problem = Problem(
                id=problem_id,
                title=text[:100] + "..." if len(text) > 100 else text,
                description=text,
                source="slack",
                source_id=message["ts"],
                channel_task=f"#{channel_info.get('name', 'unknown')} ({channel_type})",
                user=user_name,
                timestamp=datetime.fromtimestamp(float(message["ts"])),
                priority=priority,
                status="new",
                category=analysis.get("category", "general"),
                tags=analysis.get("tags", []),
                related_problems=[],
                last_updated=datetime.fromtimestamp(float(message["ts"])),
                progress_notes=[]
            )
            
            return problem
            
        except Exception as e:
            print(f"Ошибка анализа сообщения Slack: {e}")
            return None
    
    def process_channel_history(self, channel_id: str, oldest_ts: str = None) -> List[Problem]:
        """Обрабатывает историю канала и извлекает проблемы"""
        if not self.client:
            return []
        
        problems = []
        channel_info = self.get_channel_info(channel_id)
        if not channel_info:
            return []
        
        try:
            messages = self.get_channel_history(channel_id, oldest_ts)
            
            for message in messages:
                problem = self.analyze_slack_message(message, channel_info)
                if problem:
                    problems.append(problem)
                    
                    # Добавляем в базу данных
                    if self.analyzer:
                        self.analyzer.add_problem(problem)
                    
                    # Логируем в Google Sheets
                    if self.sheets_manager:
                        self.sheets_manager.log_message(
                            type("Message", (), {"text": problem.description, "from_user": type("User", (), {"username": problem.user})()}),
                            "slack"
                        )
            
            print(f"Обработано {len(messages)} сообщений из канала {channel_info.get('name', channel_id)}, найдено {len(problems)} проблем")
            
        except Exception as e:
            print(f"Ошибка обработки истории канала {channel_id}: {e}")
        
        return problems
    
    def monitor_new_messages(self, check_interval: int = 60):
        """Мониторит новые сообщения в реальном времени"""
        if not self.client:
            print("Slack клиент не инициализирован")
            return
        
        state = self._load_state()
        last_ts_by_channel = state.get("last_ts_by_channel", {})
        
        print("Начинаю мониторинг новых сообщений Slack...")
        
        while True:
            try:
                channels = self.get_all_channels()
                
                for channel in channels:
                    channel_id = channel["id"]
                    latest_known = last_ts_by_channel.get(channel_id)
                    
                    # Получаем новые сообщения
                    new_messages = self.get_channel_history(
                        channel_id, 
                        oldest_ts=latest_known,
                        limit=100
                    )
                    
                    if new_messages:
                        # Обрабатываем новые сообщения
                        problems = []
                        for message in new_messages:
                            problem = self.analyze_slack_message(message, channel)
                            if problem:
                                problems.append(problem)
                                
                                # Добавляем в базу данных
                                if self.analyzer:
                                    self.analyzer.add_problem(problem)
                        
                        # Обновляем timestamp последнего сообщения
                        if new_messages:
                            newest_ts = new_messages[0]["ts"]
                            if not latest_known or float(newest_ts) > float(latest_known):
                                last_ts_by_channel[channel_id] = newest_ts
                        
                        if problems:
                            print(f"Найдено {len(problems)} новых проблем в канале {channel.get('name', channel_id)}")
                            
                            # Уведомляем через Telegram если есть критические проблемы
                            critical_problems = [p for p in problems if p.priority <= 2]
                            if critical_problems and self.analyzer:
                                self._notify_critical_problems(critical_problems)
                
                # Сохраняем состояние
                state["last_ts_by_channel"] = last_ts_by_channel
                self._save_state(state)
                
                # Ждем следующей проверки
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"Ошибка мониторинга Slack: {e}")
                time.sleep(check_interval)
    
    def _notify_critical_problems(self, problems: List[Problem]):
        """Уведомляет о критических проблемах"""
        if not problems:
            return
        
        try:
            # Здесь можно добавить уведомления через Telegram или другие каналы
            for problem in problems:
                print(f"🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: {problem.title}")
                print(f"   Приоритет: {problem.priority}")
                print(f"   Канал: {problem.channel_task}")
                print(f"   Пользователь: {problem.user}")
                print(f"   Время: {problem.timestamp}")
                print("---")
        except Exception as e:
            print(f"Ошибка уведомления о критических проблемах: {e}")
    
    def get_important_messages(self, days_back: int = 7) -> List[Dict]:
        """Получает важные сообщения за последние дни"""
        if not self.client:
            return []
        
        important_messages = []
        cutoff_time = datetime.now() - timedelta(days=days_back)
        cutoff_ts = str(cutoff_time.timestamp())
        
        try:
            channels = self.get_all_channels()
            
            for channel in channels:
                messages = self.get_channel_history(channel["id"], oldest_ts=cutoff_ts)
                
                for message in messages:
                    # Проверяем важность сообщения
                    if self._is_important_message(message):
                        message_info = {
                            "channel": channel.get("name", "unknown"),
                            "channel_type": "public" if not channel.get("is_private") else "private",
                            "user": self.get_user_info(message.get("user", "")),
                            "text": message.get("text", ""),
                            "timestamp": message.get("ts"),
                            "reactions": message.get("reactions", []),
                            "thread_count": message.get("thread_ts") is not None
                        }
                        important_messages.append(message_info)
            
            # Сортируем по времени
            important_messages.sort(key=lambda x: float(x["timestamp"]), reverse=True)
            
        except Exception as e:
            print(f"Ошибка получения важных сообщений: {e}")
        
        return important_messages
    
    def _is_important_message(self, message: Dict) -> bool:
        """Определяет, является ли сообщение важным"""
        text = message.get("text", "").lower()
        
        # Ключевые слова для важных сообщений
        important_keywords = [
            "срочно", "критично", "важно", "проблема", "ошибка", "баг",
            "urgent", "critical", "important", "issue", "error", "bug",
            "жалоба", "недоволен", "плохо", "complaint", "dissatisfied"
        ]
        
        # Проверяем наличие ключевых слов
        for keyword in important_keywords:
            if keyword in text:
                return True
        
        # Проверяем реакции (много реакций = важное сообщение)
        reactions = message.get("reactions", [])
        total_reactions = sum(reaction.get("count", 0) for reaction in reactions)
        if total_reactions >= 3:
            return True
        
        # Проверяем наличие ответов в треде
        if message.get("thread_ts"):
            return True
        
        return False
    
    def run_initial_analysis(self):
        """Запускает первоначальный анализ всех данных Slack"""
        if not self.client:
            print("Slack клиент не инициализирован")
            return
        
        print("Начинаю первоначальный анализ данных Slack...")
        
        try:
            channels = self.get_all_channels()
            total_problems = 0
            
            for channel in channels:
                print(f"Анализирую канал: {channel.get('name', channel['id'])}")
                
                # Получаем всю историю канала
                problems = self.process_channel_history(channel["id"])
                total_problems += len(problems)
                
                # Небольшая пауза между каналами
                time.sleep(1)
            
            print(f"Первоначальный анализ завершен. Найдено {total_problems} проблем.")
            
            # Обновляем дашборд
            if self.sheets_manager and self.analyzer:
                all_problems = self.analyzer.get_problems_by_status()
                self.sheets_manager.sync_problems_to_sheets(all_problems)
                self.sheets_manager.update_dashboard(self.analyzer)
                
        except Exception as e:
            print(f"Ошибка первоначального анализа Slack: {e}")
    
    def run(self):
        """Основной метод запуска интеграции со Slack"""
        if not self.token:
            print("SLACK_TOKEN не задан — Slack интеграция отключена")
            return
        
        if not self.client:
            print("Не удалось инициализировать Slack клиент")
            return
        
        print("Slack интеграция запущена")
        
        try:
            # Запускаем первоначальный анализ в отдельном потоке
            import threading
            initial_analysis_thread = threading.Thread(
                target=self.run_initial_analysis,
                daemon=True
            )
            initial_analysis_thread.start()
            
            # Запускаем мониторинг новых сообщений
            self.monitor_new_messages()
            
        except KeyboardInterrupt:
            print("Slack интеграция остановлена")
        except Exception as e:
            print(f"Ошибка в Slack интеграции: {e}")