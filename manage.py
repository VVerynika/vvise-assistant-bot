#!/usr/bin/env python3
"""
Скрипт для управления системой бота-помощника
"""

import os
import sys
import time
import signal
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime

class SystemController:
    def __init__(self):
        self.workspace = Path("/workspace")
        self.pid_file = self.workspace / "bot.pid"
        self.log_dir = self.workspace / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
    def get_pid(self):
        """Получает PID процесса из файла"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                return pid
            except (ValueError, IOError):
                return None
        return None
    
    def save_pid(self, pid):
        """Сохраняет PID в файл"""
        with open(self.pid_file, 'w') as f:
            f.write(str(pid))
    
    def remove_pid(self):
        """Удаляет файл PID"""
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def is_running(self):
        """Проверяет, запущен ли процесс"""
        pid = self.get_pid()
        if pid is None:
            return False
        
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def start(self, background=True):
        """Запускает систему"""
        if self.is_running():
            print("❌ Система уже запущена")
            return False
        
        print("🚀 Запуск системы...")
        
        try:
            if background:
                # Запуск в фоновом режиме
                process = subprocess.Popen([
                    sys.executable, "run_background.py"
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Ждем немного для инициализации
                time.sleep(2)
                
                if process.poll() is None:
                    self.save_pid(process.pid)
                    print(f"✅ Система запущена в фоновом режиме (PID: {process.pid})")
                    return True
                else:
                    stdout, stderr = process.communicate()
                    print(f"❌ Ошибка запуска: {stderr.decode()}")
                    return False
            else:
                # Запуск в интерактивном режиме
                print("✅ Система запущена в интерактивном режиме")
                print("Нажмите Ctrl+C для остановки")
                
                process = subprocess.Popen([
                    sys.executable, "main.py"
                ])
                
                try:
                    process.wait()
                except KeyboardInterrupt:
                    process.terminate()
                    process.wait()
                    print("\n✅ Система остановлена")
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
            return False
    
    def stop(self):
        """Останавливает систему"""
        if not self.is_running():
            print("❌ Система не запущена")
            return False
        
        pid = self.get_pid()
        print(f"🛑 Остановка системы (PID: {pid})...")
        
        try:
            # Отправляем SIGTERM
            os.kill(pid, signal.SIGTERM)
            
            # Ждем завершения
            for i in range(10):
                time.sleep(1)
                if not self.is_running():
                    break
            
            # Если процесс не завершился, принудительно останавливаем
            if self.is_running():
                print("⚠️ Принудительная остановка...")
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
            
            if not self.is_running():
                self.remove_pid()
                print("✅ Система остановлена")
                return True
            else:
                print("❌ Не удалось остановить систему")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка остановки: {e}")
            return False
    
    def restart(self):
        """Перезапускает систему"""
        print("🔄 Перезапуск системы...")
        
        if self.stop():
            time.sleep(2)
            return self.start()
        else:
            print("❌ Не удалось остановить систему для перезапуска")
            return False
    
    def status(self):
        """Показывает статус системы"""
        if self.is_running():
            pid = self.get_pid()
            print(f"✅ Система запущена (PID: {pid})")
            
            # Показываем информацию о процессе
            try:
                import psutil
                process = psutil.Process(pid)
                print(f"   Время запуска: {datetime.fromtimestamp(process.create_time())}")
                print(f"   Использование CPU: {process.cpu_percent()}%")
                print(f"   Использование RAM: {process.memory_info().rss / 1024 / 1024:.1f} MB")
            except ImportError:
                print("   psutil не установлен для детальной информации")
        else:
            print("❌ Система не запущена")
        
        # Показываем логи
        if self.log_dir.exists():
            log_files = list(self.log_dir.glob("*.log"))
            if log_files:
                print(f"\n📁 Лог файлы:")
                for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True):
                    size = log_file.stat().st_size
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    print(f"   {log_file.name}: {size} bytes, изменен {mtime}")
    
    def logs(self, lines=50, follow=False):
        """Показывает логи"""
        main_log = self.log_dir / "main.log"
        
        if not main_log.exists():
            print("❌ Лог файл не найден")
            return
        
        if follow:
            print(f"📋 Отслеживание логов (Ctrl+C для остановки):")
            try:
                subprocess.run(["tail", "-f", str(main_log)])
            except KeyboardInterrupt:
                print("\n✅ Отслеживание логов остановлено")
        else:
            print(f"📋 Последние {lines} строк лога:")
            try:
                result = subprocess.run(
                    ["tail", "-n", str(lines), str(main_log)],
                    capture_output=True, text=True
                )
                print(result.stdout)
            except Exception as e:
                print(f"❌ Ошибка чтения логов: {e}")
    
    def test(self):
        """Запускает тесты системы"""
        print("🧪 Запуск тестов системы...")
        
        try:
            result = subprocess.run([
                sys.executable, "test_system.py"
            ], capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print("Ошибки:", result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Ошибка запуска тестов: {e}")
            return False
    
    def cleanup(self):
        """Очищает старые данные"""
        print("🧹 Очистка старых данных...")
        
        try:
            # Очистка старых логов
            if self.log_dir.exists():
                for log_file in self.log_dir.glob("*.log.*"):
                    if log_file.stat().st_size > 10 * 1024 * 1024:  # > 10MB
                        log_file.unlink()
                        print(f"   Удален большой лог: {log_file.name}")
            
            # Очистка временных файлов
            temp_files = list(self.workspace.glob("*.tmp"))
            for temp_file in temp_files:
                temp_file.unlink()
                print(f"   Удален временный файл: {temp_file.name}")
            
            print("✅ Очистка завершена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка очистки: {e}")
            return False

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Управление системой бота-помощника")
    parser.add_argument("command", choices=[
        "start", "stop", "restart", "status", "logs", "test", "cleanup"
    ], help="Команда для выполнения")
    
    parser.add_argument("--foreground", "-f", action="store_true",
                       help="Запуск в интерактивном режиме")
    parser.add_argument("--lines", "-n", type=int, default=50,
                       help="Количество строк лога для показа")
    parser.add_argument("--follow", "-F", action="store_true",
                       help="Отслеживание логов в реальном времени")
    
    args = parser.parse_args()
    
    controller = SystemController()
    
    if args.command == "start":
        controller.start(background=not args.foreground)
    elif args.command == "stop":
        controller.stop()
    elif args.command == "restart":
        controller.restart()
    elif args.command == "status":
        controller.status()
    elif args.command == "logs":
        controller.logs(lines=args.lines, follow=args.follow)
    elif args.command == "test":
        controller.test()
    elif args.command == "cleanup":
        controller.cleanup()

if __name__ == "__main__":
    main()