import os
import gspread
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from google.oauth2.service_account import Credentials
from problem_analyzer import Problem, ProblemAnalyzer

class GoogleSheetsManager:
    def __init__(self, sheet_id: str = None, service_account_path: str = None):
        self.sheet_id = sheet_id or os.getenv("GOOGLE_SHEET_ID")
        self.service_account_path = service_account_path or self._detect_service_account_path()
        self.gc = None
        self.sheet = None
        self.init_connection()
        
    def _detect_service_account_path(self) -> str:
        """Определяет путь к файлу сервисного аккаунта"""
        explicit_path = os.getenv("SERVICE_ACCOUNT_JSON_PATH")
        if explicit_path and os.path.isfile(explicit_path):
            return explicit_path
            
        common_paths = [
            os.getenv("RENDER_SECRET_FILE_SERVICE_ACCOUNT_JSON") or "",
            "/etc/secrets/service_account.json",
            "/etc/secrets/SERVICE_ACCOUNT_JSON",
            "/opt/render/project/src/service_account.json",
            "/workspace/service_account.json",
            "/app/service_account.json",
        ]
        
        for path in common_paths:
            if path and os.path.isfile(path):
                return path
        return ""
    
    def init_connection(self):
        """Инициализирует соединение с Google Sheets"""
        if not self.sheet_id:
            print("GOOGLE_SHEET_ID не найден")
            return
            
        if not self.service_account_path:
            print("Файл сервисного аккаунта не найден")
            return
            
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            
            creds = Credentials.from_service_account_file(
                self.service_account_path, 
                scopes=scopes
            )
            
            self.gc = gspread.authorize(creds)
            self.sheet = self.gc.open_by_key(self.sheet_id)
            print("Подключение к Google Sheets установлено")
            
        except Exception as e:
            print(f"Ошибка подключения к Google Sheets: {e}")
            self.gc = None
            self.sheet = None
    
    def create_problems_sheet(self, sheet_name: str = "Проблемы") -> bool:
        """Создает лист для отслеживания проблем"""
        if not self.sheet:
            return False
            
        try:
            # Создаем новый лист
            worksheet = self.sheet.add_worksheet(
                title=sheet_name,
                rows=1000,
                cols=20
            )
            
            # Заголовки
            headers = [
                "ID", "Название", "Описание", "Источник", "ID источника",
                "Канал/Задача", "Пользователь", "Дата создания", "Приоритет",
                "Статус", "Категория", "Теги", "Связанные проблемы",
                "Последнее обновление", "Заметки о прогрессе"
            ]
            
            worksheet.update('A1:P1', [headers])
            
            # Форматирование заголовков
            worksheet.format('A1:P1', {
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
            # Автоматическая ширина колонок
            for col in range(1, len(headers) + 1):
                worksheet.set_column_width(col, 15)
            
            return True
            
        except Exception as e:
            print(f"Ошибка создания листа: {e}")
            return False
    
    def get_or_create_problems_worksheet(self, sheet_name: str = "Проблемы"):
        """Получает существующий лист или создает новый"""
        if not self.sheet:
            return None
            
        try:
            worksheet = self.sheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            if self.create_problems_sheet(sheet_name):
                worksheet = self.sheet.worksheet(sheet_name)
            else:
                return None
                
        return worksheet
    
    def sync_problems_to_sheets(self, problems: List[Problem], sheet_name: str = "Проблемы"):
        """Синхронизирует проблемы в Google Sheets"""
        if not self.sheet:
            print("Google Sheets не подключен")
            return
            
        worksheet = self.get_or_create_problems_worksheet(sheet_name)
        if not worksheet:
            print("Не удалось получить или создать лист")
            return
            
        try:
            # Подготавливаем данные
            rows = []
            for problem in problems:
                row = [
                    problem.id,
                    problem.title,
                    problem.description,
                    problem.source,
                    problem.source_id,
                    problem.channel_task,
                    problem.user,
                    problem.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    problem.priority,
                    problem.status,
                    problem.category,
                    ', '.join(problem.tags),
                    ', '.join(problem.related_problems),
                    problem.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
                    '; '.join([note['note'] for note in problem.progress_notes])
                ]
                rows.append(row)
            
            # Очищаем существующие данные (кроме заголовков)
            if rows:
                worksheet.clear()
                worksheet.update('A1:P1', [worksheet.row_values(1)])  # Восстанавливаем заголовки
                worksheet.update(f'A2:P{len(rows)+1}', rows)
                
                # Применяем условное форматирование
                self._apply_conditional_formatting(worksheet, len(rows))
                
            print(f"Синхронизировано {len(problems)} проблем в Google Sheets")
            
        except Exception as e:
            print(f"Ошибка синхронизации в Google Sheets: {e}")
    
    def _apply_conditional_formatting(self, worksheet, row_count: int):
        """Применяет условное форматирование к листу"""
        try:
            # Форматирование по приоритету
            priority_ranges = {
                1: {'red': 1, 'green': 0.2, 'blue': 0.2},      # Красный для высшего приоритета
                2: {'red': 1, 'green': 0.5, 'blue': 0.2},      # Оранжевый
                3: {'red': 1, 'green': 1, 'blue': 0.2},        # Желтый
                4: {'red': 0.2, 'green': 0.8, 'blue': 0.2},    # Зеленый
                5: {'red': 0.8, 'green': 0.8, 'blue': 0.8}     # Серый для низкого приоритета
            }
            
            for priority, color in priority_ranges.items():
                worksheet.format(f'I2:I{row_count+1}', {
                    'backgroundColor': color
                })
            
            # Форматирование по статусу
            status_ranges = {
                'new': {'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 1}},
                'in_progress': {'backgroundColor': {'red': 1, 'green': 1, 'blue': 0.8}},
                'resolved': {'backgroundColor': {'red': 0.8, 'green': 1, 'blue': 0.8}},
                'duplicate': {'backgroundColor': {'red': 1, 'green': 0.8, 'blue': 0.8}},
                'related': {'backgroundColor': {'red': 1, 'green': 0.9, 'blue': 0.9}}
            }
            
            for status, format_rule in status_ranges.items():
                # Находим строки с нужным статусом
                status_col = worksheet.col_values(10)  # Колонка J - статус
                for i, cell_value in enumerate(status_col[1:], start=2):  # Пропускаем заголовок
                    if cell_value == status:
                        worksheet.format(f'A{i}:P{i}', format_rule)
                        
        except Exception as e:
            print(f"Ошибка применения форматирования: {e}")
    
    def create_dashboard_sheet(self, sheet_name: str = "Дашборд"):
        """Создает лист с дашбордом и статистикой"""
        if not self.sheet:
            return False
            
        try:
            worksheet = self.sheet.add_worksheet(
                title=sheet_name,
                rows=50,
                cols=10
            )
            
            # Заголовок
            worksheet.update('A1', 'Дашборд проблем и задач')
            worksheet.format('A1', {
                'textFormat': {'bold': True, 'fontSize': 16},
                'horizontalAlignment': 'CENTER'
            })
            
            # Статистика
            stats_headers = [
                "Метрика", "Значение", "Описание"
            ]
            
            stats_data = [
                ["Всего проблем", "=COUNT(Проблемы!A:A)-1", "Общее количество проблем"],
                ["Новые проблемы", "=COUNTIF(Проблемы!J:J,\"new\")", "Проблемы со статусом 'new'"],
                ["В работе", "=COUNTIF(Проблемы!J:J,\"in_progress\")", "Проблемы в разработке"],
                ["Решенные", "=COUNTIF(Проблемы!J:J,\"resolved\")", "Завершенные проблемы"],
                ["Дубликаты", "=COUNTIF(Проблемы!J:J,\"duplicate\")", "Найденные дубликаты"],
                ["Высокий приоритет", "=COUNTIF(Проблемы!I:I,\"1\")", "Проблемы с приоритетом 1"],
                ["Критичные", "=COUNTIF(Проблемы!I:I,\"2\")", "Проблемы с приоритетом 2"]
            ]
            
            worksheet.update('A3:C3', [stats_headers])
            worksheet.update('A4:C10', stats_data)
            
            # Форматирование
            worksheet.format('A3:C3', {
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
            # Автоматическая ширина колонок
            worksheet.set_column_width(1, 20)
            worksheet.set_column_width(2, 15)
            worksheet.set_column_width(3, 40)
            
            return True
            
        except Exception as e:
            print(f"Ошибка создания дашборда: {e}")
            return False
    
    def update_dashboard(self, analyzer: ProblemAnalyzer):
        """Обновляет дашборд актуальными данными"""
        if not self.sheet:
            return
            
        try:
            worksheet = self.sheet.worksheet("Дашборд")
        except gspread.WorksheetNotFound:
            if not self.create_dashboard_sheet():
                return
            worksheet = self.sheet.worksheet("Дашборд")
        
        try:
            # Получаем актуальную статистику
            report = analyzer.generate_report()
            
            # Обновляем данные
            update_data = [
                ["Последнее обновление", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Время последнего обновления"],
                ["Всего проблем", str(report['total_problems']), "Общее количество проблем"],
                ["Новые проблемы", str(report['by_status'].get('new', 0)), "Проблемы со статусом 'new'"],
                ["В работе", str(report['by_status'].get('in_progress', 0)), "Проблемы в разработке"],
                ["Решенные", str(report['by_status'].get('resolved', 0)), "Завершенные проблемы"],
                ["Дубликаты", str(report['by_status'].get('duplicate', 0)), "Найденные дубликаты"],
                ["Высокий приоритет", str(report['by_priority'].get(1, 0)), "Проблемы с приоритетом 1"],
                ["Критичные", str(report['by_priority'].get(2, 0)), "Проблемы с приоритетом 2"]
            ]
            
            worksheet.update('A4:C11', update_data)
            
        except Exception as e:
            print(f"Ошибка обновления дашборда: {e}")
    
    def log_message(self, message, source: str = "telegram"):
        """Логирует сообщение в Google Sheets"""
        if not self.sheet:
            return
            
        try:
            worksheet = self.sheet.worksheet("Логи")
        except gspread.WorksheetNotFound:
            # Создаем лист для логов
            worksheet = self.sheet.add_worksheet(
                title="Логи",
                rows=1000,
                cols=5
            )
            
            # Заголовки для логов
            log_headers = ["Время", "Источник", "Пользователь", "Тип", "Содержание"]
            worksheet.update('A1:E1', [log_headers])
            worksheet.format('A1:E1', {
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            user = "unknown"
            content = "unknown"
            msg_type = "text"
            
            if hasattr(message, 'from_user') and message.from_user:
                user = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
            
            if hasattr(message, 'text') and message.text:
                content = message.text
            elif hasattr(message, 'caption') and message.caption:
                content = message.caption
                msg_type = "caption"
            
            # Добавляем новую строку
            worksheet.append_row([timestamp, source, user, msg_type, content])
            
        except Exception as e:
            print(f"Ошибка логирования сообщения: {e}")
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Очищает старые логи"""
        if not self.sheet:
            return
            
        try:
            worksheet = self.sheet.worksheet("Логи")
            all_values = worksheet.get_all_values()
            
            if len(all_values) <= 1:  # Только заголовки
                return
                
            # Фильтруем строки по дате
            threshold_date = datetime.now() - timedelta(days=days_to_keep)
            filtered_rows = [all_values[0]]  # Сохраняем заголовки
            
            for row in all_values[1:]:
                try:
                    row_date = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                    if row_date >= threshold_date:
                        filtered_rows.append(row)
                except:
                    # Если не удалось распарсить дату, сохраняем строку
                    filtered_rows.append(row)
            
            # Обновляем лист
            if len(filtered_rows) < len(all_values):
                worksheet.clear()
                worksheet.update('A1:E1', [filtered_rows[0]])  # Заголовки
                if len(filtered_rows) > 1:
                    worksheet.update(f'A2:E{len(filtered_rows)}', filtered_rows[1:])
                    
                print(f"Очищено {len(all_values) - len(filtered_rows)} старых логов")
                
        except Exception as e:
            print(f"Ошибка очистки логов: {e}")