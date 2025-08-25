#!/usr/bin/env python3
"""
Скрипт для мониторинга производительности системы
"""

import os
import sys
import time
import psutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
import json

class PerformanceMonitor:
    def __init__(self, log_file="/workspace/logs/performance.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        self.monitoring = False
        self.monitor_thread = None
        self.start_time = datetime.now()
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'disk_usage': [],
            'network_io': [],
            'process_count': []
        }
        
    def start_monitoring(self, interval=30):
        """Запускает мониторинг"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self.monitor_thread.start()
        print(f"🚀 Мониторинг производительности запущен (интервал: {interval}с)")
        
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("🛑 Мониторинг производительности остановлен")
        
    def _monitor_loop(self, interval):
        """Основной цикл мониторинга"""
        while self.monitoring:
            try:
                self._collect_metrics()
                time.sleep(interval)
            except Exception as e:
                print(f"❌ Ошибка в мониторинге: {e}")
                time.sleep(interval)
                
    def _collect_metrics(self):
        """Собирает метрики производительности"""
        timestamp = datetime.now()
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics['cpu_usage'].append({
            'timestamp': timestamp.isoformat(),
            'value': cpu_percent
        })
        
        # Memory
        memory = psutil.virtual_memory()
        self.metrics['memory_usage'].append({
            'timestamp': timestamp.isoformat(),
            'value': memory.percent,
            'available': memory.available,
            'total': memory.total
        })
        
        # Disk
        disk = psutil.disk_usage('/')
        self.metrics['disk_usage'].append({
            'timestamp': timestamp.isoformat(),
            'value': disk.percent,
            'free': disk.free,
            'total': disk.total
        })
        
        # Network
        network = psutil.net_io_counters()
        self.metrics['network_io'].append({
            'timestamp': timestamp.isoformat(),
            'bytes_sent': network.bytes_sent,
            'bytes_recv': network.bytes_recv
        })
        
        # Process count
        process_count = len(psutil.pids())
        self.metrics['process_count'].append({
            'timestamp': timestamp.isoformat(),
            'value': process_count
        })
        
        # Ограничиваем количество записей
        max_records = 1000
        for key in self.metrics:
            if len(self.metrics[key]) > max_records:
                self.metrics[key] = self.metrics[key][-max_records:]
        
        # Логируем критические значения
        self._log_critical_values(timestamp, cpu_percent, memory.percent, disk.percent)
        
    def _log_critical_values(self, timestamp, cpu, memory, disk):
        """Логирует критические значения"""
        critical = False
        message = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
        
        if cpu > 80:
            message += f"⚠️ Высокое использование CPU: {cpu:.1f}% "
            critical = True
            
        if memory > 80:
            message += f"⚠️ Высокое использование RAM: {memory:.1f}% "
            critical = True
            
        if disk > 90:
            message += f"⚠️ Критическое использование диска: {disk:.1f}% "
            critical = True
            
        if critical:
            print(message)
            self._write_log(message)
            
    def _write_log(self, message):
        """Записывает сообщение в лог"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        except Exception as e:
            print(f"❌ Ошибка записи в лог: {e}")
            
    def get_current_status(self):
        """Получает текущий статус системы"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory
            memory = psutil.virtual_memory()
            
            # Disk
            disk = psutil.disk_usage('/')
            
            # Network
            network = psutil.net_io_counters()
            
            # Process info
            process_count = len(psutil.pids())
            
            # Uptime
            uptime = datetime.now() - self.start_time
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                    'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                },
                'memory': {
                    'percent': memory.percent,
                    'available': memory.available,
                    'total': memory.total,
                    'used': memory.used
                },
                'disk': {
                    'percent': disk.percent,
                    'free': disk.free,
                    'total': disk.total,
                    'used': disk.used
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'processes': {
                    'count': process_count,
                    'uptime': str(uptime)
                }
            }
        except Exception as e:
            return {'error': str(e)}
            
    def get_metrics_summary(self, hours=24):
        """Получает сводку метрик за указанное время"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        summary = {}
        for key, values in self.metrics.items():
            recent_values = [
                v for v in values 
                if datetime.fromisoformat(v['timestamp']) > cutoff_time
            ]
            
            if recent_values:
                if 'value' in recent_values[0]:
                    # Простые числовые значения
                    values_list = [v['value'] for v in recent_values]
                    summary[key] = {
                        'count': len(values_list),
                        'min': min(values_list),
                        'max': max(values_list),
                        'avg': sum(values_list) / len(values_list)
                    }
                else:
                    # Сложные значения (memory, disk, network)
                    summary[key] = {
                        'count': len(recent_values),
                        'latest': recent_values[-1]
                    }
                    
        return summary
        
    def export_metrics(self, filename=None):
        """Экспортирует метрики в JSON файл"""
        if filename is None:
            filename = f"/workspace/metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'monitoring_start': self.start_time.isoformat(),
                'current_status': self.get_current_status(),
                'metrics_summary': self.get_metrics_summary(),
                'raw_metrics': self.metrics
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Метрики экспортированы в {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            return None
            
    def cleanup_old_metrics(self, days_to_keep=7):
        """Очищает старые метрики"""
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        
        cleaned_count = 0
        for key, values in self.metrics.items():
            original_count = len(values)
            self.metrics[key] = [
                v for v in values 
                if datetime.fromisoformat(v['timestamp']) > cutoff_time
            ]
            cleaned_count += original_count - len(self.metrics[key])
            
        if cleaned_count > 0:
            print(f"🧹 Очищено {cleaned_count} старых записей метрик")
            
    def print_status(self):
        """Выводит текущий статус в консоль"""
        status = self.get_current_status()
        
        if 'error' in status:
            print(f"❌ Ошибка получения статуса: {status['error']}")
            return
            
        print("\n" + "="*60)
        print("📊 СТАТУС СИСТЕМЫ")
        print("="*60)
        
        # CPU
        print(f"🖥️  CPU: {status['cpu']['percent']:.1f}% "
              f"({status['cpu']['count']} ядер)")
        
        # Memory
        memory_mb = status['memory']['used'] / 1024 / 1024
        memory_total_mb = status['memory']['total'] / 1024 / 1024
        print(f"💾 RAM: {status['memory']['percent']:.1f}% "
              f"({memory_mb:.0f}MB / {memory_total_mb:.0f}MB)")
        
        # Disk
        disk_gb = status['disk']['used'] / 1024 / 1024 / 1024
        disk_total_gb = status['disk']['total'] / 1024 / 1024 / 1024
        print(f"💿 Диск: {status['disk']['percent']:.1f}% "
              f"({disk_gb:.1f}GB / {disk_total_gb:.1f}GB)")
        
        # Network
        network_mb = status['network']['bytes_sent'] / 1024 / 1024
        network_recv_mb = status['network']['bytes_recv'] / 1024 / 1024
        print(f"🌐 Сеть: Отправлено {network_mb:.1f}MB, "
              f"Получено {network_recv_mb:.1f}MB")
        
        # Processes
        print(f"⚙️  Процессы: {status['processes']['count']}")
        print(f"⏱️  Время работы: {status['processes']['uptime']}")
        
        print("="*60)

def main():
    """Основная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Мониторинг производительности системы")
    parser.add_argument("--interval", "-i", type=int, default=30,
                       help="Интервал мониторинга в секундах")
    parser.add_argument("--duration", "-d", type=int, default=0,
                       help="Длительность мониторинга в минутах (0 = бесконечно)")
    parser.add_argument("--export", "-e", action="store_true",
                       help="Экспортировать метрики при завершении")
    parser.add_argument("--status", "-s", action="store_true",
                       help="Показать текущий статус и завершить")
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor()
    
    if args.status:
        monitor.print_status()
        return
        
    try:
        print("🚀 Запуск мониторинга производительности...")
        monitor.start_monitoring(args.interval)
        
        if args.duration > 0:
            print(f"⏱️  Мониторинг будет работать {args.duration} минут")
            time.sleep(args.duration * 60)
        else:
            print("⏱️  Мониторинг работает бесконечно (Ctrl+C для остановки)")
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки")
    finally:
        monitor.stop_monitoring()
        
        if args.export:
            monitor.export_metrics()
            
        # Показываем финальный статус
        monitor.print_status()

if __name__ == "__main__":
    main()