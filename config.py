#!/usr/bin/env python3
"""
Модуль для управления конфигурацией системы
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self, config_dir="/workspace/config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Загружаем переменные окружения
        load_dotenv()
        
        # Основные конфигурационные файлы
        self.config_files = {
            'main': self.config_dir / 'config.json',
            'notifications': self.config_dir / 'notifications.json',
            'database': self.config_dir / 'database.json',
            'api': self.config_dir / 'api.json',
            'logging': self.config_dir / 'logging.json'
        }
        
        # Загружаем конфигурацию
        self.config = self._load_all_configs()
        
    def _load_all_configs(self) -> Dict[str, Any]:
        """Загружает все конфигурации"""
        configs = {}
        
        for name, file_path in self.config_files.items():
            configs[name] = self._load_config_file(file_path, name)
            
        return configs
    
    def _load_config_file(self, file_path: Path, config_name: str) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        default_configs = {
            'main': {
                'app_name': 'Bot Assistant',
                'version': '1.0.0',
                'debug': False,
                'timezone': 'UTC',
                'language': 'ru',
                'max_workers': 4,
                'log_level': 'INFO',
                'data_retention_days': 90,
                'backup_enabled': True,
                'backup_interval_hours': 24
            },
            'notifications': {
                'telegram': {
                    'enabled': True,
                    'token': os.getenv('TELEGRAM_TOKEN'),
                    'chat_ids': os.getenv('TELEGRAM_AUTHORIZED_USERS', '').split(','),
                    'rate_limit': 60,
                    'max_per_hour': 100
                },
                'slack': {
                    'enabled': True,
                    'token': os.getenv('SLACK_TOKEN'),
                    'channels': ['#general'],
                    'rate_limit': 30,
                    'max_per_hour': 50
                },
                'email': {
                    'enabled': False,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'recipients': []
                },
                'webhook': {
                    'enabled': False,
                    'urls': [],
                    'rate_limit': 10,
                    'max_per_hour': 200
                }
            },
            'database': {
                'type': 'sqlite',
                'sqlite': {
                    'path': '/workspace/data/problems.db',
                    'backup_enabled': True,
                    'backup_path': '/workspace/backups'
                },
                'postgresql': {
                    'enabled': False,
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'bot_assistant',
                    'username': 'botuser',
                    'password': os.getenv('POSTGRES_PASSWORD', 'botpass123')
                },
                'redis': {
                    'enabled': False,
                    'host': 'localhost',
                    'port': 6379,
                    'database': 0,
                    'password': None
                }
            },
            'api': {
                'slack': {
                    'token': os.getenv('SLACK_TOKEN'),
                    'workspace_id': None,
                    'rate_limit': 1000,
                    'retry_attempts': 3,
                    'timeout': 30
                },
                'clickup': {
                    'token': os.getenv('CLICKUP_API_TOKEN'),
                    'workspace_id': os.getenv('CLICKUP_WORKSPACE_ID'),
                    'rate_limit': 100,
                    'retry_attempts': 3,
                    'timeout': 30
                },
                'google_sheets': {
                    'sheet_id': os.getenv('GOOGLE_SHEET_ID'),
                    'service_account_path': os.getenv('SERVICE_ACCOUNT_JSON_PATH'),
                    'rate_limit': 300,
                    'retry_attempts': 3,
                    'timeout': 60
                },
                'telegram': {
                    'token': os.getenv('TELEGRAM_TOKEN'),
                    'authorized_users': os.getenv('TELEGRAM_AUTHORIZED_USERS', '').split(','),
                    'rate_limit': 30,
                    'retry_attempts': 3,
                    'timeout': 10
                }
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file_enabled': True,
                'file_path': '/workspace/logs/app.log',
                'file_max_size': '10MB',
                'file_backup_count': 5,
                'console_enabled': True,
                'syslog_enabled': False,
                'syslog_host': 'localhost',
                'syslog_port': 514
            }
        }
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if file_path.suffix == '.json':
                        user_config = json.load(f)
                    elif file_path.suffix in ['.yml', '.yaml']:
                        user_config = yaml.safe_load(f)
                    else:
                        user_config = {}
                        
                    # Объединяем с дефолтной конфигурацией
                    default_config = default_configs.get(config_name, {})
                    merged_config = self._deep_merge(default_config, user_config)
                    return merged_config
                    
            except Exception as e:
                print(f"Ошибка загрузки конфигурации {config_name}: {e}")
                
        return default_configs.get(config_name, {})
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Глубокое объединение словарей"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def get_config(self, config_name: str, key: str = None, default: Any = None) -> Any:
        """Получает значение конфигурации"""
        if config_name not in self.config:
            return default
            
        config = self.config[config_name]
        
        if key is None:
            return config
            
        # Поддерживаем точечную нотацию для вложенных ключей
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set_config(self, config_name: str, key: str, value: Any) -> bool:
        """Устанавливает значение конфигурации"""
        if config_name not in self.config:
            return False
            
        config = self.config[config_name]
        
        # Поддерживаем точечную нотацию для вложенных ключей
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
            
        current[keys[-1]] = value
        
        # Сохраняем в файл
        return self._save_config_file(config_name)
    
    def _save_config_file(self, config_name: str) -> bool:
        """Сохраняет конфигурацию в файл"""
        if config_name not in self.config_files:
            return False
            
        file_path = self.config_files[config_name]
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix == '.json':
                    json.dump(self.config[config_name], f, indent=2, ensure_ascii=False)
                elif file_path.suffix in ['.yml', '.yaml']:
                    yaml.dump(self.config[config_name], f, default_flow_style=False, allow_unicode=True)
                    
            return True
            
        except Exception as e:
            print(f"Ошибка сохранения конфигурации {config_name}: {e}")
            return False
    
    def reload_config(self) -> bool:
        """Перезагружает конфигурацию"""
        try:
            self.config = self._load_all_configs()
            return True
        except Exception as e:
            print(f"Ошибка перезагрузки конфигурации: {e}")
            return False
    
    def validate_config(self) -> Dict[str, list]:
        """Валидирует конфигурацию"""
        errors = {}
        
        # Проверяем основные настройки
        main_config = self.config.get('main', {})
        if not main_config.get('app_name'):
            errors.setdefault('main', []).append('app_name не указан')
            
        # Проверяем API настройки
        api_config = self.config.get('api', {})
        
        # Slack
        slack_config = api_config.get('slack', {})
        if not slack_config.get('token'):
            errors.setdefault('api.slack', []).append('SLACK_TOKEN не настроен')
            
        # ClickUp
        clickup_config = api_config.get('clickup', {})
        if not clickup_config.get('token'):
            errors.setdefault('api.clickup', []).append('CLICKUP_API_TOKEN не настроен')
            
        # Google Sheets
        sheets_config = api_config.get('google_sheets', {})
        if not sheets_config.get('sheet_id'):
            errors.setdefault('api.google_sheets', []).append('GOOGLE_SHEET_ID не настроен')
        if not sheets_config.get('service_account_path'):
            errors.setdefault('api.google_sheets', []).append('SERVICE_ACCOUNT_JSON_PATH не настроен')
            
        # Telegram
        telegram_config = api_config.get('telegram', {})
        if not telegram_config.get('token'):
            errors.setdefault('api.telegram', []).append('TELEGRAM_TOKEN не настроен')
            
        # Проверяем базу данных
        db_config = self.config.get('database', {})
        if db_config.get('type') == 'postgresql':
            pg_config = db_config.get('postgresql', {})
            if not pg_config.get('password'):
                errors.setdefault('database.postgresql', []).append('POSTGRES_PASSWORD не настроен')
                
        return errors
    
    def get_env_vars(self) -> Dict[str, str]:
        """Получает все переменные окружения"""
        return {
            'SLACK_TOKEN': os.getenv('SLACK_TOKEN', ''),
            'CLICKUP_API_TOKEN': os.getenv('CLICKUP_API_TOKEN', ''),
            'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN', ''),
            'GOOGLE_SHEET_ID': os.getenv('GOOGLE_SHEET_ID', ''),
            'SERVICE_ACCOUNT_JSON_PATH': os.getenv('SERVICE_ACCOUNT_JSON_PATH', ''),
            'CLICKUP_WORKSPACE_ID': os.getenv('CLICKUP_WORKSPACE_ID', ''),
            'TELEGRAM_AUTHORIZED_USERS': os.getenv('TELEGRAM_AUTHORIZED_USERS', ''),
            'POSTGRES_PASSWORD': os.getenv('POSTGRES_PASSWORD', '')
        }
    
    def export_config(self, format: str = 'json') -> str:
        """Экспортирует конфигурацию"""
        if format == 'json':
            return json.dumps(self.config, indent=2, ensure_ascii=False)
        elif format == 'yaml':
            return yaml.dump(self.config, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Неподдерживаемый формат: {format}")
    
    def import_config(self, config_data: str, format: str = 'json') -> bool:
        """Импортирует конфигурацию"""
        try:
            if format == 'json':
                new_config = json.loads(config_data)
            elif format == 'yaml':
                new_config = yaml.safe_load(config_data)
            else:
                raise ValueError(f"Неподдерживаемый формат: {format}")
                
            # Объединяем с существующей конфигурацией
            for config_name, config_value in new_config.items():
                if config_name in self.config:
                    self.config[config_name] = self._deep_merge(self.config[config_name], config_value)
                else:
                    self.config[config_name] = config_value
                    
            # Сохраняем все конфигурации
            for config_name in self.config:
                self._save_config_file(config_name)
                
            return True
            
        except Exception as e:
            print(f"Ошибка импорта конфигурации: {e}")
            return False
    
    def create_default_configs(self) -> bool:
        """Создает файлы конфигурации по умолчанию"""
        try:
            for config_name in self.config:
                self._save_config_file(config_name)
            return True
        except Exception as e:
            print(f"Ошибка создания конфигураций по умолчанию: {e}")
            return False

def main():
    """Основная функция для тестирования"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Управление конфигурацией системы")
    parser.add_argument("--validate", action="store_true", help="Валидировать конфигурацию")
    parser.add_argument("--export", choices=['json', 'yaml'], help="Экспортировать конфигурацию")
    parser.add_argument("--create-defaults", action="store_true", help="Создать конфигурации по умолчанию")
    parser.add_argument("--get", type=str, help="Получить значение конфигурации (config.key)")
    parser.add_argument("--set", nargs=2, metavar=('KEY', 'VALUE'), help="Установить значение конфигурации")
    parser.add_argument("--reload", action="store_true", help="Перезагрузить конфигурацию")
    
    args = parser.parse_args()
    
    config_manager = ConfigManager()
    
    if args.validate:
        print("🔍 Валидация конфигурации...")
        errors = config_manager.validate_config()
        
        if errors:
            print("❌ Найдены ошибки:")
            for section, section_errors in errors.items():
                print(f"  {section}:")
                for error in section_errors:
                    print(f"    - {error}")
        else:
            print("✅ Конфигурация валидна")
            
    elif args.export:
        print(f"📤 Экспорт конфигурации в формате {args.export}...")
        try:
            exported = config_manager.export_config(args.export)
            print(exported)
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            
    elif args.create_defaults:
        print("📝 Создание конфигураций по умолчанию...")
        if config_manager.create_default_configs():
            print("✅ Конфигурации созданы")
        else:
            print("❌ Ошибка создания конфигураций")
            
    elif args.get:
        print(f"🔍 Получение значения: {args.get}")
        value = config_manager.get_config(*args.get.split('.', 1))
        print(f"Значение: {value}")
        
    elif args.set:
        key, value = args.set
        print(f"🔧 Установка значения: {key} = {value}")
        
        # Пытаемся преобразовать значение
        try:
            if value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)
        except:
            pass
            
        if config_manager.set_config(*key.split('.', 1), value):
            print("✅ Значение установлено")
        else:
            print("❌ Ошибка установки значения")
            
    elif args.reload:
        print("🔄 Перезагрузка конфигурации...")
        if config_manager.reload_config():
            print("✅ Конфигурация перезагружена")
        else:
            print("❌ Ошибка перезагрузки")
            
    else:
        print("Использование:")
        print("  --validate              # Валидировать конфигурацию")
        print("  --export FORMAT         # Экспортировать конфигурацию")
        print("  --create-defaults       # Создать конфигурации по умолчанию")
        print("  --get KEY               # Получить значение")
        print("  --set KEY VALUE         # Установить значение")
        print("  --reload                # Перезагрузить конфигурацию")

if __name__ == "__main__":
    main()