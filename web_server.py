#!/usr/bin/env python3
"""
Простой веб-сервер для веб-интерфейса Бот-Помощника
"""

import os
import json
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

# Импортируем наши модули
try:
    from problem_analyzer import ProblemAnalyzer
    from monitor import PerformanceMonitor
    from config import ConfigManager
except ImportError as e:
    print(f"⚠️ Ошибка импорта: {e}")
    print("Запускаем веб-сервер без модулей анализа")

class BotAssistantHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для веб-интерфейса"""
    
    def __init__(self, *args, **kwargs):
        self.analyzer = None
        self.monitor = None
        self.config = None
        super().__init__(*args, **kwargs)
    
    def initialize_components(self):
        """Инициализирует компоненты системы"""
        try:
            if not self.analyzer:
                self.analyzer = ProblemAnalyzer()
            if not self.monitor:
                self.monitor = PerformanceMonitor()
            if not self.config:
                self.config = ConfigManager()
        except Exception as e:
            print(f"⚠️ Ошибка инициализации компонентов: {e}")
    
    def do_GET(self):
        """Обрабатывает GET запросы"""
        try:
            self.initialize_components()
            
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            
            if path == '/':
                self.serve_index()
            elif path == '/health':
                self.serve_health()
            elif path == '/status':
                self.serve_status()
            elif path == '/api/status':
                self.serve_api_status()
            elif path == '/api/metrics':
                self.serve_api_metrics()
            elif path == '/api/problems':
                self.serve_api_problems()
            elif path.startswith('/static/'):
                self.serve_static_file(path)
            else:
                self.serve_404()
                
        except Exception as e:
            self.send_error(500, f"Внутренняя ошибка сервера: {e}")
    
    def serve_index(self):
        """Отдает главную страницу"""
        try:
            with open('static/index.html', 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.serve_simple_index()
    
    def serve_simple_index(self):
        """Отдает простую главную страницу если index.html не найден"""
        html = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Бот-Помощник - Мониторинг</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { text-align: center; margin-bottom: 30px; }
                .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
                .status-card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff; }
                .status-card h3 { margin-top: 0; color: #007bff; }
                .metric { display: flex; justify-content: space-between; margin: 10px 0; }
                .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
                .btn:hover { background: #0056b3; }
                .btn-danger { background: #dc3545; }
                .btn-warning { background: #ffc107; color: black; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 Бот-Помощник</h1>
                    <p>Система мониторинга и анализа проблем</p>
                </div>
                
                <div class="status-grid">
                    <div class="status-card">
                        <h3>📊 Статус системы</h3>
                        <div id="system-status">Загрузка...</div>
                    </div>
                    
                    <div class="status-card">
                        <h3>💻 Ресурсы системы</h3>
                        <div id="system-resources">Загрузка...</div>
                    </div>
                    
                    <div class="status-card">
                        <h3>🔍 Компоненты</h3>
                        <div id="components-status">Загрузка...</div>
                    </div>
                </div>
                
                <div style="text-align: center;">
                    <button class="btn" onclick="refreshData()">🔄 Обновить</button>
                    <button class="btn btn-warning" onclick="restartSystem()">🔄 Перезапуск</button>
                    <button class="btn btn-danger" onclick="stopSystem()">🛑 Остановить</button>
                </div>
                
                <div id="logs" style="margin-top: 30px; background: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h3>📋 Логи системы</h3>
                    <div id="log-content">Загрузка логов...</div>
                </div>
            </div>
            
            <script>
                function refreshData() {
                    fetch('/api/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('system-status').innerHTML = `
                                <div class="metric"><span>Статус:</span> <strong>${data.status}</strong></div>
                                <div class="metric"><span>Время работы:</span> <strong>${data.uptime}</strong></div>
                                <div class="metric"><span>Версия:</span> <strong>${data.version}</strong></div>
                            `;
                            
                            document.getElementById('system-resources').innerHTML = `
                                <div class="metric"><span>CPU:</span> <strong>${data.metrics.cpu}%</strong></div>
                                <div class="metric"><span>RAM:</span> <strong>${data.metrics.memory}%</strong></div>
                                <div class="metric"><span>Диск:</span> <strong>${data.metrics.disk}%</strong></div>
                            `;
                            
                            document.getElementById('components-status').innerHTML = `
                                <div class="metric"><span>Slack:</span> <strong>${data.components.slack}</strong></div>
                                <div class="metric"><span>ClickUp:</span> <strong>${data.components.clickup}</strong></div>
                                <div class="metric"><span>Telegram:</span> <strong>${data.components.telegram}</strong></div>
                            `;
                        });
                    
                    fetch('/api/metrics')
                        .then(response => response.json())
                        .then(data => {
                            // Обновляем логи
                            let logContent = '';
                            if (data.recent_logs) {
                                data.recent_logs.forEach(log => {
                                    logContent += `<div style="margin: 5px 0; padding: 5px; background: white; border-radius: 3px;">${log}</div>`;
                                });
                            }
                            document.getElementById('log-content').innerHTML = logContent || 'Логи не найдены';
                        });
                }
                
                function restartSystem() {
                    if (confirm('Перезапустить систему?')) {
                        fetch('/api/restart', {method: 'POST'})
                            .then(() => {
                                alert('Система перезапускается...');
                                setTimeout(refreshData, 5000);
                            });
                    }
                }
                
                function stopSystem() {
                    if (confirm('Остановить систему?')) {
                        fetch('/api/stop', {method: 'POST'})
                            .then(() => {
                                alert('Система останавливается...');
                            });
                    }
                }
                
                // Автоматическое обновление каждые 30 секунд
                setInterval(refreshData, 30000);
                
                // Загрузка данных при загрузке страницы
                document.addEventListener('DOMContentLoaded', refreshData);
            </script>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_health(self):
        """Отдает статус здоровья системы"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"healthy\n")
    
    def serve_status(self):
        """Отдает HTML страницу статуса"""
        self.serve_index()
    
    def serve_api_status(self):
        """Отдает JSON статус системы"""
        try:
            status_data = {
                "status": "running",
                "uptime": "0:00:00",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "cpu": 0,
                    "memory": 0,
                    "disk": 0
                },
                "components": {
                    "slack": "unknown",
                    "clickup": "unknown",
                    "telegram": "unknown"
                }
            }
            
            # Получаем реальные метрики если возможно
            if self.monitor:
                try:
                    current_status = self.monitor.get_current_status()
                    status_data["metrics"]["cpu"] = current_status.get('cpu_usage', 0)
                    status_data["metrics"]["memory"] = current_status.get('memory_usage', 0)
                    status_data["metrics"]["disk"] = current_status.get('disk_usage', 0)
                except:
                    pass
            
            # Получаем статус компонентов если возможно
            if self.analyzer:
                try:
                    status_data["components"]["slack"] = "active" if hasattr(self.analyzer, 'slack_integration') else "inactive"
                    status_data["components"]["clickup"] = "active" if hasattr(self.analyzer, 'clickup_integration') else "inactive"
                    status_data["components"]["telegram"] = "active" if hasattr(self.analyzer, 'telegram_bot') else "inactive"
                except:
                    pass
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(status_data, ensure_ascii=False, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Ошибка получения статуса: {e}")
    
    def serve_api_metrics(self):
        """Отдает метрики системы"""
        try:
            metrics_data = {
                "timestamp": datetime.now().isoformat(),
                "recent_logs": []
            }
            
            # Читаем последние логи
            try:
                if os.path.exists('logs/main.log'):
                    with open('logs/main.log', 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        # Последние 10 строк
                        recent_lines = lines[-10:] if len(lines) > 10 else lines
                        metrics_data["recent_logs"] = [line.strip() for line in recent_lines]
            except:
                pass
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(metrics_data, ensure_ascii=False, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Ошибка получения метрик: {e}")
    
    def serve_api_problems(self):
        """Отдает список проблем"""
        try:
            problems_data = {
                "total": 0,
                "problems": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Получаем проблемы если возможно
            if self.analyzer:
                try:
                    # Здесь должна быть логика получения проблем
                    pass
                except:
                    pass
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(problems_data, ensure_ascii=False, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Ошибка получения проблем: {e}")
    
    def serve_static_file(self, path):
        """Отдает статические файлы"""
        try:
            file_path = path[1:]  # Убираем /static/
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # Определяем MIME тип
                if file_path.endswith('.css'):
                    content_type = 'text/css'
                elif file_path.endswith('.js'):
                    content_type = 'application/javascript'
                elif file_path.endswith('.png'):
                    content_type = 'image/png'
                elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                    content_type = 'image/jpeg'
                else:
                    content_type = 'text/plain'
                
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.end_headers()
                self.wfile.write(content)
            else:
                self.serve_404()
        except Exception as e:
            self.send_error(500, f"Ошибка чтения файла: {e}")
    
    def serve_404(self):
        """Отдает 404 ошибку"""
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>404 - Страница не найдена</title></head>
        <body>
            <h1>404 - Страница не найдена</h1>
            <p>Запрашиваемая страница не существует.</p>
            <a href="/">Вернуться на главную</a>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Переопределяем логирование для тишины"""
        pass

def run_web_server(port=8000):
    """Запускает веб-сервер"""
    try:
        server = HTTPServer(('', port), BotAssistantHandler)
        print(f"🌐 Веб-сервер запущен на порту {port}")
        print(f"📱 Откройте в браузере: http://localhost:{port}")
        print("🛑 Для остановки нажмите Ctrl+C")
        
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Веб-сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска веб-сервера: {e}")

if __name__ == "__main__":
    import sys
    
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("⚠️ Неверный порт, используем 8000")
    
    run_web_server(port)