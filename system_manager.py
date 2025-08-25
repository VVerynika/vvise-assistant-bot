#!/usr/bin/env python3
"""
Системный менеджер для бота-помощника
Обеспечивает мониторинг, перезапуск и диагностику всех компонентов
"""

import os
import sys
import time
import signal
import psutil
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional
import json

class SystemManager:
    def __init__(self):
        self.processes = {}
        self.monitoring = False
        self.monitor_thread = None
        self.log_file = "/workspace/system.log"
        
    def start_component(self, component_name: str, command: str, env_vars: Dict = None) -> bool:
        """Запускает компонент системы"""
        try:
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            process = subprocess.Popen(
                command.split(),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[component_name] = {
                'process': process,
                'command': command,
                'start_time': datetime.now(),
                'restart_count': 0
            }
            
            self.log(f"Запущен компонент: {component_name} (PID: {process.pid})")
            return True
            
        except Exception as e:
            self.log(f"Ошибка запуска {component_name}: {e}")
            return False
    
    def stop_component(self, component_name: str) -> bool:
        """Останавливает компонент системы"""
        if component_name not in self.processes:
            return False
            
        try:
            process_info = self.processes[component_name]
            process = process_info['process']
            
            # Отправляем SIGTERM
            process.terminate()
            
            # Ждем завершения
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Принудительно завершаем
                process.kill()
                process.wait()
            
            self.log(f"Остановлен компонент: {component_name}")
            del self.processes[component_name]
            return True
            
        except Exception as e:
            self.log(f"Ошибка остановки {component_name}: {e}")
            return False
    
    def restart_component(self, component_name: str) -> bool:
        """Перезапускает компонент системы"""
        if component_name not in self.processes:
            return False
            
        try:
            process_info = self.processes[component_name]
            command = process_info['command']
            env_vars = {}
            
            # Останавливаем
            self.stop_component(component_name)
            
            # Запускаем заново
            time.sleep(2)
            return self.start_component(component_name, command, env_vars)
            
        except Exception as e:
            self.log(f"Ошибка перезапуска {component_name}: {e}")
            return False
    
    def get_component_status(self, component_name: str) -> Dict:
        """Получает статус компонента"""
        if component_name not in self.processes:
            return {'status': 'stopped', 'pid': None, 'uptime': None}
            
        process_info = self.processes[component_name]
        process = process_info['process']
        
        if process.poll() is None:
            # Процесс работает
            uptime = datetime.now() - process_info['start_time']
            return {
                'status': 'running',
                'pid': process.pid,
                'uptime': str(uptime),
                'restart_count': process_info['restart_count']
            }
        else:
            # Процесс завершился
            return {
                'status': 'stopped',
                'pid': None,
                'uptime': None,
                'exit_code': process.returncode
            }
    
    def get_system_status(self) -> Dict:
        """Получает общий статус системы"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'components': {},
            'system': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            }
        }
        
        for component_name in self.processes:
            status['components'][component_name] = self.get_component_status(component_name)
            
        return status
    
    def start_monitoring(self, interval: int = 30):
        """Запускает мониторинг системы"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self.monitor_thread.start()
        self.log("Запущен мониторинг системы")
    
    def stop_monitoring(self):
        """Останавливает мониторинг системы"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.log("Остановлен мониторинг системы")
    
    def _monitor_loop(self, interval: int):
        """Основной цикл мониторинга"""
        while self.monitoring:
            try:
                # Проверяем статус всех компонентов
                for component_name in list(self.processes.keys()):
                    status = self.get_component_status(component_name)
                    if status['status'] == 'stopped':
                        self.log(f"Компонент {component_name} остановился, перезапускаем...")
                        self.restart_component(component_name)
                
                # Логируем системную информацию
                system_status = self.get_system_status()
                if system_status['system']['cpu_percent'] > 80 or system_status['system']['memory_percent'] > 80:
                    self.log(f"Внимание! Высокая нагрузка: CPU {system_status['system']['cpu_percent']}%, RAM {system_status['system']['memory_percent']}%")
                
                time.sleep(interval)
                
            except Exception as e:
                self.log(f"Ошибка в мониторинге: {e}")
                time.sleep(interval)
    
    def log(self, message: str):
        """Логирует сообщения"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        print(log_entry)
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"Ошибка записи в лог: {e}")
    
    def cleanup(self):
        """Очищает ресурсы"""
        self.stop_monitoring()
        
        # Останавливаем все компоненты
        for component_name in list(self.processes.keys()):
            self.stop_component(component_name)
        
        self.log("Системный менеджер остановлен")

def main():
    """Основная функция для тестирования"""
    manager = SystemManager()
    
    try:
        # Запускаем мониторинг
        manager.start_monitoring(interval=10)
        
        # Тестируем запуск компонента
        success = manager.start_component(
            "test_component",
            "python3 -c 'import time; time.sleep(30)'"
        )
        
        if success:
            print("Тестовый компонент запущен")
            
            # Мониторим 1 минуту
            time.sleep(60)
            
            # Проверяем статус
            status = manager.get_component_status("test_component")
            print(f"Статус тестового компонента: {status}")
            
            # Останавливаем
            manager.stop_component("test_component")
        
        # Показываем системный статус
        system_status = manager.get_system_status()
        print(f"Системный статус: {json.dumps(system_status, indent=2, default=str)}")
        
    except KeyboardInterrupt:
        print("\nПолучен сигнал остановки")
    finally:
        manager.cleanup()

if __name__ == "__main__":
    main()
