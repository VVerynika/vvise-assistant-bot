import os
import time
import json
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from problem_analyzer import Problem, ProblemAnalyzer
from google_sheets_manager import GoogleSheetsManager

class ClickUpIntegration:
    def __init__(self, token: str = None, workspace_id: str = None, analyzer: ProblemAnalyzer = None, sheets_manager: GoogleSheetsManager = None):
        self.token = token or os.getenv("CLICKUP_API_TOKEN")
        self.workspace_id = workspace_id or os.getenv("CLICKUP_WORKSPACE_ID")
        self.analyzer = analyzer
        self.sheets_manager = sheets_manager
        self.state_path = "/workspace/.clickup_state.json"
        self.base_url = "https://api.clickup.com/api/v2"
        self.headers = {"Authorization": self.token} if self.token else {}
        
    def _load_state(self) -> Dict:
        """Загружает состояние мониторинга ClickUp"""
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "last_updated_gt": None,
            "last_processed_task": None,
            "spaces_processed": set(),
            "folders_processed": set(),
            "lists_processed": set()
        }
    
    def _save_state(self, state: Dict):
        """Сохраняет состояние мониторинга ClickUp"""
        try:
            # Преобразуем set в list для JSON сериализации
            state_copy = state.copy()
            state_copy["spaces_processed"] = list(state_copy.get("spaces_processed", []))
            state_copy["folders_processed"] = list(state_copy.get("folders_processed", []))
            state_copy["lists_processed"] = list(state_copy.get("lists_processed", []))
            
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state_copy, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения состояния ClickUp: {e}")
    
    def get_workspaces(self) -> List[Dict]:
        """Получает все рабочие пространства"""
        if not self.token:
            return []
        
        try:
            response = requests.get(f"{self.base_url}/team", headers=self.headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get("teams", [])
            else:
                print(f"Ошибка получения рабочих пространств: {response.status_code}")
                return []
        except Exception as e:
            print(f"Ошибка запроса к ClickUp API: {e}")
            return []
    
    def get_spaces(self, workspace_id: str = None) -> List[Dict]:
        """Получает все пространства в рабочем пространстве"""
        workspace_id = workspace_id or self.workspace_id
        if not self.token or not workspace_id:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/team/{workspace_id}/space",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("spaces", [])
            else:
                print(f"Ошибка получения пространств: {response.status_code}")
                return []
        except Exception as e:
            print(f"Ошибка запроса к ClickUp API: {e}")
            return []
    
    def get_folders(self, space_id: str) -> List[Dict]:
        """Получает все папки в пространстве"""
        if not self.token:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/space/{space_id}/folder",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("folders", [])
            else:
                print(f"Ошибка получения папок: {response.status_code}")
                return []
        except Exception as e:
            print(f"Ошибка запроса к ClickUp API: {e}")
            return []
    
    def get_lists(self, space_id: str, folder_id: str = None) -> List[Dict]:
        """Получает все списки в пространстве или папке"""
        if not self.token:
            return []
        
        try:
            if folder_id:
                response = requests.get(
                    f"{self.base_url}/folder/{folder_id}/list",
                    headers=self.headers,
                    timeout=30
                )
            else:
                response = requests.get(
                    f"{self.base_url}/space/{space_id}/list",
                    headers=self.headers,
                    timeout=30
                )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("lists", [])
            else:
                print(f"Ошибка получения списков: {response.status_code}")
                return []
        except Exception as e:
            print(f"Ошибка запроса к ClickUp API: {e}")
            return []
    
    def get_tasks(self, list_id: str, include_closed: bool = True, subtasks: bool = True, page: int = 0) -> List[Dict]:
        """Получает задачи из списка"""
        if not self.token:
            return []
        
        try:
            params = {
                "page": page,
                "subtasks": subtasks,
                "include_closed": include_closed
            }
            
            response = requests.get(
                f"{self.base_url}/list/{list_id}/task",
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("tasks", [])
            else:
                print(f"Ошибка получения задач: {response.status_code}")
                return []
        except Exception as e:
            print(f"Ошибка запроса к ClickUp API: {e}")
            return []
    
    def get_task_details(self, task_id: str) -> Optional[Dict]:
        """Получает детальную информацию о задаче"""
        if not self.token:
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/task/{task_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка получения деталей задачи: {response.status_code}")
                return None
        except Exception as e:
            print(f"Ошибка запроса к ClickUp API: {e}")
            return None
    
    def analyze_clickup_task(self, task: Dict, list_info: Dict, space_info: Dict) -> Optional[Problem]:
        """Анализирует задачу ClickUp и создает объект проблемы"""
        try:
            task_name = task.get("name", "")
            task_description = task.get("description", "")
            
            if not task_name:
                return None
            
            # Анализируем текст задачи
            analysis = self.analyzer.analyze_text(f"{task_name} {task_description}") if self.analyzer else {}
            
            # Создаем ID проблемы
            problem_id = hashlib.md5(f"clickup_{task['id']}".encode()).hexdigest()
            
            # Определяем приоритет на основе ClickUp приоритета и анализа
            clickup_priority = task.get("priority", 3)
            if clickup_priority == 1:  # Urgent в ClickUp
                priority = 1
            elif clickup_priority == 2:  # High в ClickUp
                priority = 2
            elif clickup_priority == 3:  # Normal в ClickUp
                priority = 3
            elif clickup_priority == 4:  # Low в ClickUp
                priority = 4
            else:
                priority = analysis.get("priority", 3)
            
            # Определяем статус
            status_map = {
                "to do": "new",
                "in progress": "in_progress",
                "complete": "resolved",
                "closed": "resolved"
            }
            clickup_status = task.get("status", {}).get("status", "").lower()
            status = status_map.get(clickup_status, "new")
            
            # Получаем информацию о пользователе
            assignees = task.get("assignees", [])
            user_name = "Unassigned"
            if assignees:
                user_name = assignees[0].get("username", "Unknown")
            
            # Создаем объект проблемы
            problem = Problem(
                id=problem_id,
                title=task_name,
                description=task_description or task_name,
                source="clickup",
                source_id=task["id"],
                channel_task=f"{space_info.get('name', 'Unknown')} / {list_info.get('name', 'Unknown')}",
                user=user_name,
                timestamp=datetime.fromtimestamp(int(task.get("date_created", "0")) / 1000),
                priority=priority,
                status=status,
                category=analysis.get("category", "task"),
                tags=analysis.get("tags", []) + [clickup_status],
                related_problems=[],
                last_updated=datetime.fromtimestamp(int(task.get("date_updated", "0")) / 1000),
                progress_notes=[]
            )
            
            return problem
            
        except Exception as e:
            print(f"Ошибка анализа задачи ClickUp: {e}")
            return None
    
    def process_list_tasks(self, list_id: str, list_info: Dict, space_info: Dict) -> List[Problem]:
        """Обрабатывает все задачи в списке"""
        if not self.token:
            return []
        
        problems = []
        page = 0
        
        try:
            while True:
                tasks = self.get_tasks(list_id, page=page)
                if not tasks:
                    break
                
                for task in tasks:
                    problem = self.analyze_clickup_task(task, list_info, space_info)
                    if problem:
                        problems.append(problem)
                        
                        # Добавляем в базу данных
                        if self.analyzer:
                            self.analyzer.add_problem(problem)
                        
                        # Логируем в Google Sheets
                        if self.sheets_manager:
                            self.sheets_manager.log_message(
                                type("Message", (), {"text": problem.description, "from_user": type("User", (), {"username": problem.user})()}),
                                "clickup"
                            )
                
                page += 1
                time.sleep(0.1)  # Небольшая пауза между запросами
            
            print(f"Обработано {len(problems)} задач из списка {list_info.get('name', list_id)}")
            
        except Exception as e:
            print(f"Ошибка обработки задач списка {list_id}: {e}")
        
        return problems
    
    def process_space(self, space_id: str, space_info: Dict) -> List[Problem]:
        """Обрабатывает все задачи в пространстве"""
        if not self.token:
            return []
        
        all_problems = []
        
        try:
            # Получаем папки
            folders = self.get_folders(space_id)
            
            # Обрабатываем задачи в папках
            for folder in folders:
                lists = self.get_lists(space_id, folder["id"])
                for list_item in lists:
                    problems = self.process_list_tasks(list_item["id"], list_item, space_info)
                    all_problems.extend(problems)
            
            # Получаем списки без папок
            lists = self.get_lists(space_id)
            for list_item in lists:
                problems = self.process_list_tasks(list_item["id"], list_item, space_info)
                all_problems.extend(problems)
            
            print(f"Обработано {len(all_problems)} задач в пространстве {space_info.get('name', space_id)}")
            
        except Exception as e:
            print(f"Ошибка обработки пространства {space_id}: {e}")
        
        return all_problems
    
    def monitor_new_tasks(self, check_interval: int = 300):  # 5 минут
        """Мониторит новые задачи в ClickUp"""
        if not self.token:
            print("CLICKUP_API_TOKEN не задан")
            return
        
        state = self._load_state()
        last_updated_gt = state.get("last_updated_gt")
        
        print("Начинаю мониторинг новых задач ClickUp...")
        
        while True:
            try:
                if self.workspace_id:
                    spaces = self.get_spaces(self.workspace_id)
                else:
                    workspaces = self.get_workspaces()
                    if workspaces:
                        spaces = self.get_spaces(workspaces[0]["id"])
                    else:
                        spaces = []
                
                new_problems = []
                newest_update = last_updated_gt
                
                for space in spaces:
                    space_id = space["id"]
                    
                    # Получаем папки
                    folders = self.get_folders(space_id)
                    
                    # Обрабатываем задачи в папках
                    for folder in folders:
                        lists = self.get_lists(space_id, folder["id"])
                        for list_item in lists:
                            problems = self._get_new_tasks_from_list(
                                list_item["id"], 
                                list_item, 
                                space, 
                                last_updated_gt
                            )
                            new_problems.extend(problems)
                            
                            # Отслеживаем самое новое обновление
                            for problem in problems:
                                if problem.last_updated.timestamp() > (newest_update or 0):
                                    newest_update = problem.last_updated.timestamp()
                    
                    # Получаем списки без папок
                    lists = self.get_lists(space_id)
                    for list_item in lists:
                        problems = self._get_new_tasks_from_list(
                            list_item["id"], 
                            list_item, 
                            space, 
                            last_updated_gt
                        )
                        new_problems.extend(problems)
                        
                        # Отслеживаем самое новое обновление
                        for problem in problems:
                            if problem.last_updated.timestamp() > (newest_update or 0):
                                newest_update = problem.last_updated.timestamp()
                
                # Обновляем состояние
                if newest_update and newest_update != last_updated_gt:
                    last_updated_gt = newest_update
                    state["last_updated_gt"] = last_updated_gt
                    self._save_state(state)
                
                if new_problems:
                    print(f"Найдено {len(new_problems)} новых задач в ClickUp")
                    
                    # Уведомляем о критических задачах
                    critical_problems = [p for p in new_problems if p.priority <= 2]
                    if critical_problems:
                        self._notify_critical_tasks(critical_problems)
                    
                    # Обновляем дашборд
                    if self.sheets_manager and self.analyzer:
                        all_problems = self.analyzer.get_problems_by_status()
                        self.sheets_manager.sync_problems_to_sheets(all_problems)
                        self.sheets_manager.update_dashboard(self.analyzer)
                
                # Ждем следующей проверки
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"Ошибка мониторинга ClickUp: {e}")
                time.sleep(check_interval)
    
    def _get_new_tasks_from_list(self, list_id: str, list_info: Dict, space_info: Dict, last_updated_gt: float = None) -> List[Problem]:
        """Получает новые задачи из списка"""
        if not self.token:
            return []
        
        problems = []
        page = 0
        
        try:
            while True:
                tasks = self.get_tasks(list_id, page=page)
                if not tasks:
                    break
                
                for task in tasks:
                    # Проверяем, является ли задача новой
                    task_updated = int(task.get("date_updated", "0")) / 1000
                    if last_updated_gt and task_updated <= last_updated_gt:
                        continue
                    
                    problem = self.analyze_clickup_task(task, list_info, space_info)
                    if problem:
                        problems.append(problem)
                        
                        # Добавляем в базу данных
                        if self.analyzer:
                            self.analyzer.add_problem(problem)
                
                page += 1
                time.sleep(0.1)
            
        except Exception as e:
            print(f"Ошибка получения новых задач из списка {list_id}: {e}")
        
        return problems
    
    def _notify_critical_tasks(self, problems: List[Problem]):
        """Уведомляет о критических задачах"""
        if not problems:
            return
        
        try:
            for problem in problems:
                print(f"🚨 КРИТИЧЕСКАЯ ЗАДАЧА: {problem.title}")
                print(f"   Приоритет: {problem.priority}")
                print(f"   Пространство: {problem.channel_task}")
                print(f"   Назначена: {problem.user}")
                print(f"   Время: {problem.last_updated}")
                print("---")
        except Exception as e:
            print(f"Ошибка уведомления о критических задачах: {e}")
    
    def run_initial_analysis(self):
        """Запускает первоначальный анализ всех данных ClickUp"""
        if not self.token:
            print("CLICKUP_API_TOKEN не задан")
            return
        
        print("Начинаю первоначальный анализ данных ClickUp...")
        
        try:
            if self.workspace_id:
                spaces = self.get_spaces(self.workspace_id)
            else:
                workspaces = self.get_workspaces()
                if workspaces:
                    spaces = self.get_spaces(workspaces[0]["id"])
                else:
                    spaces = []
            
            total_problems = 0
            
            for space in spaces:
                print(f"Анализирую пространство: {space.get('name', space['id'])}")
                
                problems = self.process_space(space["id"], space)
                total_problems += len(problems)
                
                # Небольшая пауза между пространствами
                time.sleep(1)
            
            print(f"Первоначальный анализ завершен. Найдено {total_problems} задач.")
            
            # Обновляем дашборд
            if self.sheets_manager and self.analyzer:
                all_problems = self.analyzer.get_problems_by_status()
                self.sheets_manager.sync_problems_to_sheets(all_problems)
                self.sheets_manager.update_dashboard(self.analyzer)
                
        except Exception as e:
            print(f"Ошибка первоначального анализа ClickUp: {e}")
    
    def run(self):
        """Основной метод запуска интеграции с ClickUp"""
        if not self.token:
            print("CLICKUP_API_TOKEN не задан — ClickUp интеграция отключена")
            return
        
        print("ClickUp интеграция запущена")
        
        try:
            # Запускаем первоначальный анализ в отдельном потоке
            import threading
            initial_analysis_thread = threading.Thread(
                target=self.run_initial_analysis,
                daemon=True
            )
            initial_analysis_thread.start()
            
            # Запускаем мониторинг новых задач
            self.monitor_new_tasks()
            
        except KeyboardInterrupt:
            print("ClickUp интеграция остановлена")
        except Exception as e:
            print(f"Ошибка в ClickUp интеграции: {e}")