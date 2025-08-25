# 📚 Примеры использования Бот-Помощника

## 🚀 Быстрый старт

### 1. Первый запуск

```bash
# Клонирование репозитория
git clone https://github.com/your-username/bot-assistant.git
cd bot-assistant

# Автоматическая установка и настройка
python3 quick_start.py
```

### 2. Проверка системы

```bash
# Запуск тестов
python3 test_system.py

# Проверка статуса
./start.sh status

# Просмотр логов
./start.sh logs
```

## 🔧 Настройка интеграций

### Slack интеграция

1. **Создание Slack App**
   ```bash
   # Перейдите на https://api.slack.com/apps
   # Создайте новое приложение
   # Добавьте следующие OAuth Scopes:
   # - channels:read
   # - channels:history
   # - groups:read
   # - groups:history
   # - im:read
   # - im:history
   # - mpim:read
   # - mpim:history
   # - users:read
   ```

2. **Установка в workspace**
   ```bash
   # Установите приложение в ваш workspace
   # Скопируйте Bot User OAuth Token
   # Добавьте в .env файл:
   SLACK_TOKEN=xoxb-your-token-here
   ```

3. **Добавление бота в каналы**
   ```bash
   # Пригласите бота в нужные каналы
   # Бот автоматически начнет мониторинг
   ```

### ClickUp интеграция

1. **Получение API токена**
   ```bash
   # Перейдите в ClickUp Settings
   # Apps > API Token
   # Создайте новый токен
   # Добавьте в .env файл:
   CLICKUP_API_TOKEN=your-token-here
   ```

2. **Получение Workspace ID**
   ```bash
   # Workspace ID находится в URL
   # https://app.clickup.com/workspace/WORKSPACE_ID
   # Добавьте в .env файл:
   CLICKUP_WORKSPACE_ID=your-workspace-id
   ```

### Telegram бот

1. **Создание бота**
   ```bash
   # Найдите @BotFather в Telegram
   # Отправьте /newbot
   # Следуйте инструкциям
   # Получите токен
   # Добавьте в .env файл:
   TELEGRAM_TOKEN=your-bot-token-here
   ```

2. **Авторизация пользователей**
   ```bash
   # Получите ваш Telegram ID
   # Отправьте /start боту @userinfobot
   # Добавьте ID в .env файл:
   TELEGRAM_AUTHORIZED_USERS=123456789
   ```

### Google Sheets

1. **Создание Service Account**
   ```bash
   # Перейдите в Google Cloud Console
   # Создайте новый проект
   # Включите Google Sheets API
   # Создайте Service Account
   # Скачайте JSON ключ
   ```

2. **Настройка доступа**
   ```bash
   # Создайте Google Sheets таблицу
   # Скопируйте ID из URL
   # Добавьте в .env файл:
   GOOGLE_SHEET_ID=your-sheet-id
   SERVICE_ACCOUNT_JSON_PATH=/path/to/key.json
   ```

## 📊 Использование системы

### Мониторинг проблем

1. **Автоматический анализ**
   ```bash
   # Система автоматически:
   # - Анализирует сообщения Slack
   # - Мониторит задачи ClickUp
   # - Выявляет проблемы
   # - Классифицирует их
   # - Отправляет уведомления
   ```

2. **Просмотр проблем**
   ```bash
   # Через Telegram бота:
   /problems          # Список всех проблем
   /problems new      # Новые проблемы
   /problems urgent   # Срочные проблемы
   /report            # Сводный отчет
   ```

3. **Управление через веб-интерфейс**
   ```bash
   # Откройте http://localhost:8000
   # Просматривайте:
   # - Статистику проблем
   # - Статус компонентов
   # - Системные ресурсы
   # - Логи системы
   ```

### Настройка уведомлений

1. **Конфигурация уведомлений**
   ```bash
   # Редактируйте config/notifications.json
   {
     "telegram": {
       "enabled": true,
       "rate_limit": 60,
       "max_per_hour": 100
     },
     "slack": {
       "enabled": true,
       "channels": ["#general", "#support"],
       "rate_limit": 30
     }
   }
   ```

2. **Тестирование уведомлений**
   ```bash
   # Тест всех каналов
   python3 notifications.py --test

   # Тест конкретного канала
   python3 notifications.py --channel telegram -m "Тестовое сообщение"

   # Просмотр статистики
   python3 notifications.py --stats
   ```

### Мониторинг производительности

1. **Запуск мониторинга**
   ```bash
   # Мониторинг в реальном времени
   python3 monitor.py --interval 30

   # Мониторинг с экспортом
   python3 monitor.py --duration 60 --export

   # Просмотр текущего статуса
   python3 monitor.py --status
   ```

2. **Анализ метрик**
   ```bash
   # Метрики экспортируются в JSON
   # Анализируйте:
   # - Использование CPU/RAM
   # - Дисковые операции
   # - Сетевую активность
   # - Количество процессов
   ```

## 🔍 Анализ данных

### Просмотр проблем

1. **Через базу данных**
   ```bash
   # Подключение к SQLite
   sqlite3 data/problems.db

   # Просмотр проблем
   SELECT * FROM problems WHERE status = 'new';

   # Поиск дубликатов
   SELECT * FROM problems WHERE title LIKE '%error%';
   ```

2. **Через API**
   ```bash
   # Статус системы
   curl http://localhost:8000/status

   # Логи системы
   curl http://localhost:8000/logs

   # Статистика проблем
   curl http://localhost:8000/api/problems/stats
   ```

### Экспорт данных

1. **Экспорт в Google Sheets**
   ```bash
   # Автоматический экспорт
   # Система создает таблицы:
   # - Проблемы (основная таблица)
   # - Дашборд (статистика)
   # - Логи (операции)
   ```

2. **Экспорт метрик**
   ```bash
   # Экспорт метрик производительности
   python3 monitor.py --export

   # Файл сохраняется как:
   # metrics_YYYYMMDD_HHMMSS.json
   ```

## 🛠️ Управление системой

### Основные команды

```bash
# Запуск системы
./start.sh start

# Остановка системы
./start.sh stop

# Перезапуск системы
./start.sh restart

# Проверка статуса
./start.sh status

# Просмотр логов
./start.sh logs

# Запуск тестов
./start.sh test

# Очистка данных
./start.sh cleanup
```

### Управление через Python

```bash
# Статус системы
python3 manage.py status

# Управление конфигурацией
python3 config.py --validate
python3 config.py --export json
python3 config.py --create-defaults

# Тестирование компонентов
python3 test_system.py
```

### Docker управление

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot-assistant

# Остановка сервисов
docker-compose down

# Пересборка и запуск
docker-compose up -d --build
```

## 📈 Настройка отчетности

### Google Sheets дашборд

1. **Автоматическое создание**
   ```bash
   # Система автоматически создает:
   # - Таблицу "Проблемы" с данными
   # - Таблицу "Дашборд" со статистикой
   # - Таблицу "Логи" с операциями
   ```

2. **Настройка форматирования**
   ```bash
   # Условное форматирование:
   # - Красный: критические проблемы
   # - Оранжевый: срочные проблемы
   # - Желтый: обычные проблемы
   # - Зеленый: решенные проблемы
   ```

### Telegram отчеты

1. **Команды для отчетов**
   ```bash
   /report              # Общий отчет
   /problems            # Список проблем
   /forgotten           # Забытые проблемы
   /urgent              # Срочные проблемы
   /stats               # Статистика
   ```

2. **Настройка уведомлений**
   ```bash
   # Автоматические уведомления:
   # - Новые проблемы
   # - Критические проблемы
   # - Изменения статуса
   # - Ежедневные отчеты
   ```

## 🔧 Кастомизация

### Настройка анализа проблем

1. **Паттерны для выявления**
   ```python
   # В problem_analyzer.py
   problem_patterns = {
       'bug': [
           'ошибка', 'баг', 'не работает', 'сломалось',
           'error', 'bug', 'broken', 'failed'
       ],
       'feature_request': [
           'нужно', 'хочу', 'добавить', 'сделать',
           'need', 'want', 'add', 'implement'
       ]
   }
   ```

2. **Приоритизация**
   ```python
   # Настройка весов для приоритизации
   priority_weights = {
       'urgent_keywords': 5,
       'user_complaint': 4,
       'bug_report': 3,
       'feature_request': 2,
       'general_question': 1
   }
   ```

### Настройка уведомлений

1. **Шаблоны сообщений**
   ```python
   # В notifications.py
   message_templates = {
       'new_problem': """
       🚨 Новая проблема: {title}
       
       Описание: {description}
       Приоритет: {priority}
       Категория: {category}
       """,
       'critical_alert': """
       ⚠️ КРИТИЧЕСКАЯ ПРОБЛЕМА!
       
       {message}
       
       Требует немедленного внимания!
       """
   }
   ```

## 🚨 Устранение неполадок

### Частые проблемы

1. **Ошибки API**
   ```bash
   # Проверьте токены в .env
   # Убедитесь в правах доступа
   # Проверьте лимиты API
   # Просмотрите логи в logs/
   ```

2. **Проблемы с базой данных**
   ```bash
   # Проверьте права на запись
   # Убедитесь в свободном месте
   # Проверьте SQLite файл
   # Запустите тесты: python3 test_system.py
   ```

3. **Проблемы с уведомлениями**
   ```bash
   # Проверьте токены ботов
   # Убедитесь в авторизации
   # Проверьте права доступа
   # Тестируйте: python3 notifications.py --test
   ```

### Диагностика

```bash
# Полная диагностика системы
python3 test_system.py

# Проверка конфигурации
python3 config.py --validate

# Мониторинг производительности
python3 monitor.py --status

# Проверка логов
tail -f logs/main.log
tail -f logs/performance.log
```

## 📚 Дополнительные ресурсы

### Документация
- `README.md` - Основная документация
- `INSTALL.md` - Инструкции по установке
- `SYSTEM_INFO.md` - Информация о системе
- `EXAMPLE.md` - Примеры использования

### Скрипты
- `quick_start.py` - Автоматическая установка
- `start.sh` - Управление системой
- `manage.py` - Python управление
- `test_system.py` - Тестирование

### Конфигурация
- `.env` - Переменные окружения
- `config/` - Конфигурационные файлы
- `nginx.conf` - Веб-сервер
- `docker-compose.yml` - Docker сервисы

---

🚀 **Начните использовать систему уже сегодня!**

Система автоматически начнет анализировать данные и выявлять проблемы, помогая вашей команде работать более эффективно.