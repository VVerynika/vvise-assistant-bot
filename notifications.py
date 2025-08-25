#!/usr/bin/env python3
"""
Модуль для управления уведомлениями через различные каналы
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from pathlib import Path
import requests

class NotificationManager:
    def __init__(self, config_file="/workspace/config/notifications.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Загружаем конфигурацию
        self.config = self._load_config()
        
        # История уведомлений для предотвращения спама
        self.notification_history = {}
        
        # Статистика уведомлений
        self.stats = {
            'total_sent': 0,
            'successful': 0,
            'failed': 0,
            'by_channel': {}
        }
        
    def _load_config(self) -> Dict:
        """Загружает конфигурацию уведомлений"""
        default_config = {
            'telegram': {
                'enabled': True,
                'token': os.getenv('TELEGRAM_TOKEN'),
                'chat_ids': os.getenv('TELEGRAM_AUTHORIZED_USERS', '').split(','),
                'rate_limit': 60,  # секунд между уведомлениями
                'max_notifications_per_hour': 100
            },
            'slack': {
                'enabled': True,
                'token': os.getenv('SLACK_TOKEN'),
                'channels': ['#general'],
                'rate_limit': 30,
                'max_notifications_per_hour': 50
            },
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'recipients': [],
                'rate_limit': 300,
                'max_notifications_per_hour': 20
            },
            'webhook': {
                'enabled': False,
                'urls': [],
                'rate_limit': 10,
                'max_notifications_per_hour': 200
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # Объединяем с дефолтной конфигурацией
                    for key, value in user_config.items():
                        if key in default_config:
                            default_config[key].update(value)
            except Exception as e:
                self.logger.error(f"Ошибка загрузки конфигурации: {e}")
                
        return default_config
    
    def _save_config(self):
        """Сохраняет конфигурацию"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения конфигурации: {e}")
    
    def _can_send_notification(self, channel: str, notification_type: str) -> bool:
        """Проверяет, можно ли отправить уведомление"""
        if channel not in self.config:
            return False
            
        channel_config = self.config[channel]
        if not channel_config.get('enabled', False):
            return False
            
        # Проверяем rate limit
        key = f"{channel}_{notification_type}"
        last_sent = self.notification_history.get(key, 0)
        rate_limit = channel_config.get('rate_limit', 60)
        
        if time.time() - last_sent < rate_limit:
            return False
            
        # Проверяем лимит в час
        hour_ago = time.time() - 3600
        hourly_count = sum(1 for timestamp in self.notification_history.values() 
                          if timestamp > hour_ago)
        max_per_hour = channel_config.get('max_notifications_per_hour', 100)
        
        if hourly_count >= max_per_hour:
            return False
            
        return True
    
    def _update_notification_history(self, channel: str, notification_type: str):
        """Обновляет историю уведомлений"""
        key = f"{channel}_{notification_type}"
        self.notification_history[key] = time.time()
        
        # Очищаем старые записи
        hour_ago = time.time() - 3600
        self.notification_history = {
            k: v for k, v in self.notification_history.items() 
            if v > hour_ago
        }
    
    def send_telegram_notification(self, message: str, chat_id: str = None, 
                                  parse_mode: str = 'HTML') -> bool:
        """Отправляет уведомление в Telegram"""
        if not self._can_send_notification('telegram', 'message'):
            return False
            
        try:
            token = self.config['telegram']['token']
            if not token:
                self.logger.error("Telegram токен не настроен")
                return False
                
            # Определяем chat_id
            if chat_id:
                chat_ids = [chat_id]
            else:
                chat_ids = self.config['telegram']['chat_ids']
                
            if not chat_ids:
                self.logger.error("Не указаны chat_id для Telegram")
                return False
                
            # Отправляем сообщения
            success_count = 0
            for cid in chat_ids:
                if not cid.strip():
                    continue
                    
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {
                    'chat_id': cid.strip(),
                    'text': message,
                    'parse_mode': parse_mode
                }
                
                response = requests.post(url, data=data, timeout=10)
                if response.status_code == 200:
                    success_count += 1
                else:
                    self.logger.error(f"Ошибка отправки в Telegram {cid}: {response.text}")
                    
            if success_count > 0:
                self._update_notification_history('telegram', 'message')
                self._update_stats('telegram', True)
                self.logger.info(f"Отправлено {success_count}/{len(chat_ids)} уведомлений в Telegram")
                return True
            else:
                self._update_stats('telegram', False)
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка отправки в Telegram: {e}")
            self._update_stats('telegram', False)
            return False
    
    def send_slack_notification(self, message: str, channel: str = None) -> bool:
        """Отправляет уведомление в Slack"""
        if not self._can_send_notification('slack', 'message'):
            return False
            
        try:
            token = self.config['slack']['token']
            if not token:
                self.logger.error("Slack токен не настроен")
                return False
                
            # Определяем канал
            if channel:
                channels = [channel]
            else:
                channels = self.config['slack']['channels']
                
            if not channels:
                self.logger.error("Не указаны каналы для Slack")
                return False
                
            # Отправляем сообщения
            success_count = 0
            for ch in channels:
                if not ch.strip():
                    continue
                    
                url = "https://slack.com/api/chat.postMessage"
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                data = {
                    'channel': ch.strip(),
                    'text': message
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        success_count += 1
                    else:
                        self.logger.error(f"Ошибка Slack API {ch}: {result.get('error')}")
                else:
                    self.logger.error(f"Ошибка HTTP {ch}: {response.status_code}")
                    
            if success_count > 0:
                self._update_notification_history('slack', 'message')
                self._update_stats('slack', True)
                self.logger.info(f"Отправлено {success_count}/{len(channels)} уведомлений в Slack")
                return True
            else:
                self._update_stats('slack', False)
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка отправки в Slack: {e}")
            self._update_stats('slack', False)
            return False
    
    def send_email_notification(self, subject: str, message: str, 
                               recipients: List[str] = None) -> bool:
        """Отправляет уведомление по email"""
        if not self._can_send_notification('email', 'message'):
            return False
            
        try:
            email_config = self.config['email']
            if not email_config.get('enabled', False):
                return False
                
            # Определяем получателей
            if recipients:
                email_recipients = recipients
            else:
                email_recipients = email_config['recipients']
                
            if not email_recipients:
                self.logger.error("Не указаны получатели для email")
                return False
                
            # Здесь должна быть реализация отправки email
            # Для простоты просто логируем
            self.logger.info(f"Email уведомление: {subject} -> {email_recipients}")
            
            self._update_notification_history('email', 'message')
            self._update_stats('email', True)
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки email: {e}")
            self._update_stats('email', False)
            return False
    
    def send_webhook_notification(self, data: Dict, webhook_url: str = None) -> bool:
        """Отправляет уведомление через webhook"""
        if not self._can_send_notification('webhook', 'message'):
            return False
            
        try:
            webhook_config = self.config['webhook']
            if not webhook_config.get('enabled', False):
                return False
                
            # Определяем URL
            if webhook_url:
                urls = [webhook_url]
            else:
                urls = webhook_config['urls']
                
            if not urls:
                self.logger.error("Не указаны URL для webhook")
                return False
                
            # Отправляем уведомления
            success_count = 0
            for url in urls:
                if not url.strip():
                    continue
                    
                response = requests.post(url.strip(), json=data, timeout=10)
                if response.status_code in [200, 201, 202]:
                    success_count += 1
                else:
                    self.logger.error(f"Ошибка webhook {url}: {response.status_code}")
                    
            if success_count > 0:
                self._update_notification_history('webhook', 'message')
                self._update_stats('webhook', True)
                self.logger.info(f"Отправлено {success_count}/{len(urls)} webhook уведомлений")
                return True
            else:
                self._update_stats('webhook', False)
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка отправки webhook: {e}")
            self._update_stats('webhook', False)
            return False
    
    def send_critical_alert(self, title: str, message: str, 
                           priority: str = 'high') -> bool:
        """Отправляет критическое уведомление по всем каналам"""
        self.logger.warning(f"КРИТИЧЕСКОЕ УВЕДОМЛЕНИЕ: {title}")
        
        # Форматируем сообщение
        formatted_message = f"🚨 {title}\n\n{message}\n\nПриоритет: {priority.upper()}\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Отправляем по всем каналам
        results = []
        
        if self.config['telegram']['enabled']:
            results.append(self.send_telegram_notification(formatted_message))
            
        if self.config['slack']['enabled']:
            results.append(self.send_slack_notification(formatted_message))
            
        if self.config['email']['enabled']:
            results.append(self.send_email_notification(f"КРИТИЧЕСКОЕ УВЕДОМЛЕНИЕ: {title}", formatted_message))
            
        if self.config['webhook']['enabled']:
            webhook_data = {
                'type': 'critical_alert',
                'title': title,
                'message': message,
                'priority': priority,
                'timestamp': datetime.now().isoformat()
            }
            results.append(self.send_webhook_notification(webhook_data))
            
        return any(results)
    
    def send_problem_notification(self, problem_data: Dict) -> bool:
        """Отправляет уведомление о проблеме"""
        title = f"Проблема: {problem_data.get('title', 'Без названия')}"
        
        message = f"""
🔍 Новая проблема обнаружена

📋 Название: {problem_data.get('title', 'Не указано')}
📝 Описание: {problem_data.get('description', 'Не указано')[:200]}...
🏷️ Категория: {problem_data.get('category', 'Не указано')}
⚡ Приоритет: {problem_data.get('priority', 'Не указано')}
📊 Статус: {problem_data.get('status', 'Не указано')}
👤 Пользователь: {problem_data.get('user', 'Не указано')}
📅 Время: {problem_data.get('timestamp', 'Не указано')}
        """.strip()
        
        # Определяем приоритет уведомления
        priority = problem_data.get('priority', 3)
        if priority <= 2:
            return self.send_critical_alert(title, message, 'high')
        else:
            return self.send_telegram_notification(message)
    
    def _update_stats(self, channel: str, success: bool):
        """Обновляет статистику уведомлений"""
        self.stats['total_sent'] += 1
        
        if success:
            self.stats['successful'] += 1
        else:
            self.stats['failed'] += 1
            
        if channel not in self.stats['by_channel']:
            self.stats['by_channel'][channel] = {'sent': 0, 'successful': 0, 'failed': 0}
            
        self.stats['by_channel'][channel]['sent'] += 1
        if success:
            self.stats['by_channel'][channel]['successful'] += 1
        else:
            self.stats['by_channel'][channel]['failed'] += 1
    
    def get_stats(self) -> Dict:
        """Получает статистику уведомлений"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Сбрасывает статистику"""
        self.stats = {
            'total_sent': 0,
            'successful': 0,
            'failed': 0,
            'by_channel': {}
        }
    
    def test_notifications(self) -> Dict:
        """Тестирует все каналы уведомлений"""
        test_message = f"🧪 Тестовое уведомление\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        results = {
            'telegram': False,
            'slack': False,
            'email': False,
            'webhook': False
        }
        
        # Тестируем Telegram
        if self.config['telegram']['enabled']:
            results['telegram'] = self.send_telegram_notification(test_message)
            
        # Тестируем Slack
        if self.config['slack']['enabled']:
            results['slack'] = self.send_slack_notification(test_message)
            
        # Тестируем Email
        if self.config['email']['enabled']:
            results['email'] = self.send_email_notification("Тест", test_message)
            
        # Тестируем Webhook
        if self.config['webhook']['enabled']:
            test_data = {'type': 'test', 'message': test_message, 'timestamp': datetime.now().isoformat()}
            results['webhook'] = self.send_webhook_notification(test_data)
            
        return results

def main():
    """Основная функция для тестирования"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование системы уведомлений")
    parser.add_argument("--test", action="store_true", help="Тестировать все каналы")
    parser.add_argument("--message", "-m", type=str, default="Тестовое уведомление",
                       help="Сообщение для отправки")
    parser.add_argument("--channel", "-c", type=str, choices=['telegram', 'slack', 'email', 'webhook'],
                       help="Канал для отправки")
    parser.add_argument("--stats", action="store_true", help="Показать статистику")
    
    args = parser.parse_args()
    
    # Настройка логирования
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    manager = NotificationManager()
    
    if args.test:
        print("🧪 Тестирование всех каналов уведомлений...")
        results = manager.test_notifications()
        
        print("\n📊 Результаты тестирования:")
        for channel, success in results.items():
            status = "✅ Успешно" if success else "❌ Ошибка"
            print(f"  {channel}: {status}")
            
    elif args.channel:
        print(f"📤 Отправка сообщения в канал {args.channel}...")
        
        if args.channel == 'telegram':
            success = manager.send_telegram_notification(args.message)
        elif args.channel == 'slack':
            success = manager.send_slack_notification(args.message)
        elif args.channel == 'email':
            success = manager.send_email_notification("Тест", args.message)
        elif args.channel == 'webhook':
            test_data = {'type': 'test', 'message': args.message, 'timestamp': datetime.now().isoformat()}
            success = manager.send_webhook_notification(test_data)
            
        if success:
            print("✅ Сообщение отправлено")
        else:
            print("❌ Ошибка отправки")
            
    elif args.stats:
        stats = manager.get_stats()
        print("\n📊 Статистика уведомлений:")
        print(f"  Всего отправлено: {stats['total_sent']}")
        print(f"  Успешно: {stats['successful']}")
        print(f"  Ошибок: {stats['failed']}")
        
        if stats['by_channel']:
            print("\n  По каналам:")
            for channel, channel_stats in stats['by_channel'].items():
                print(f"    {channel}: {channel_stats['sent']} отправлено, "
                      f"{channel_stats['successful']} успешно, {channel_stats['failed']} ошибок")
                      
    else:
        print("Использование:")
        print("  --test                    # Тестировать все каналы")
        print("  --channel CHANNEL -m MSG  # Отправить сообщение в канал")
        print("  --stats                   # Показать статистику")

if __name__ == "__main__":
    main()