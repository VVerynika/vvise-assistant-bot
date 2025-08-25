# 🚀 Инструкции по установке и запуску

## 📋 Быстрый старт

### 1. Автоматическая установка (рекомендуется)

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd bot-assistant

# Запустите автоматическую установку
python3 quick_start.py
```

### 2. Ручная установка

```bash
# Установите зависимости
pip install -r requirements.txt

# Создайте файл .env
cp .env.example .env

# Отредактируйте .env файл
nano .env

# Запустите тесты
python3 test_system.py

# Запустите систему
./start.sh start
```

## 🔧 Настройка переменных окружения

Создайте файл `.env` со следующими переменными:

```env
# Slack Integration
SLACK_TOKEN=xoxb-your-slack-bot-token-here

# ClickUp Integration
CLICKUP_API_TOKEN=your-clickup-api-token-here
CLICKUP_WORKSPACE_ID=your-workspace-id-here

# Telegram Bot
TELEGRAM_TOKEN=your-telegram-bot-token-here
TELEGRAM_AUTHORIZED_USERS=123456789,987654321

# Google Sheets
GOOGLE_SHEET_ID=your-google-sheet-id-here
SERVICE_ACCOUNT_JSON_PATH=/path/to/service-account.json

# Database (опционально)
POSTGRES_PASSWORD=your-postgres-password-here
```

## 🐳 Запуск через Docker

### 1. Сборка и запуск

```bash
# Сборка образов
docker-compose build

# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot-assistant
```

### 2. Остановка

```bash
# Остановка всех сервисов
docker-compose down

# Остановка с удалением данных
docker-compose down -v
```

## 📱 Настройка Telegram бота

### 1. Создание бота

1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям
4. Получите токен и добавьте его в `.env`

### 2. Авторизация пользователей

Добавьте ID пользователей в переменную `TELEGRAM_AUTHORIZED_USERS`:

```env
TELEGRAM_AUTHORIZED_USERS=123456789,987654321
```

## 📊 Настройка Google Sheets

### 1. Создание Service Account

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект
3. Включите Google Sheets API
4. Создайте Service Account
5. Скачайте JSON ключ

### 2. Предоставление доступа

1. Откройте Google Sheets
2. Нажмите "Настройки доступа"
3. Добавьте email из Service Account
4. Предоставьте права на редактирование

## 🔍 Проверка системы

### 1. Тестирование компонентов

```bash
# Полный тест системы
python3 test_system.py

# Тест уведомлений
python3 notifications.py --test

# Валидация конфигурации
python3 config.py --validate

# Мониторинг производительности
python3 monitor.py --status
```

### 2. Проверка статуса

```bash
# Статус системы
./start.sh status

# Логи системы
./start.sh logs

# Статус через Python
python3 manage.py status
```

## 🚨 Устранение неполадок

### Проблемы с API

1. **Slack API ошибки**
   - Проверьте токен в `.env`
   - Убедитесь, что бот добавлен в каналы
   - Проверьте права доступа

2. **ClickUp API ошибки**
   - Проверьте токен и workspace ID
   - Убедитесь в правах доступа к workspace
   - Проверьте лимиты API

3. **Google Sheets ошибки**
   - Проверьте ID таблицы
   - Убедитесь в правах Service Account
   - Проверьте квоты API

### Проблемы с базой данных

1. **SQLite ошибки**
   - Проверьте права на запись в директорию
   - Убедитесь в свободном месте на диске
   - Проверьте логи в `logs/`

2. **PostgreSQL ошибки**
   - Проверьте подключение к базе
   - Убедитесь в правильности учетных данных
   - Проверьте права пользователя

### Проблемы с уведомлениями

1. **Telegram ошибки**
   - Проверьте токен бота
   - Убедитесь, что пользователи авторизованы
   - Проверьте права бота

2. **Slack ошибки**
   - Проверьте токен и права
   - Убедитесь, что бот в каналах
   - Проверьте лимиты API

## 📈 Мониторинг и обслуживание

### 1. Автоматический мониторинг

```bash
# Запуск мониторинга производительности
python3 monitor.py --interval 30

# Мониторинг с экспортом метрик
python3 monitor.py --duration 60 --export
```

### 2. Очистка данных

```bash
# Очистка старых логов
./start.sh cleanup

# Очистка старых метрик
python3 monitor.py --cleanup

# Очистка базы данных
python3 problem_analyzer.py --cleanup
```

### 3. Резервное копирование

```bash
# Создание резервной копии
python3 manage.py backup

# Восстановление из резервной копии
python3 manage.py restore backup_file.tar.gz
```

## 🔄 Обновление системы

### 1. Обновление кода

```bash
# Получение обновлений
git pull origin main

# Установка новых зависимостей
pip install -r requirements.txt

# Перезапуск системы
./start.sh restart
```

### 2. Обновление Docker

```bash
# Остановка системы
docker-compose down

# Получение обновлений
git pull origin main

# Пересборка и запуск
docker-compose up -d --build
```

## 📚 Дополнительные возможности

### 1. Веб-интерфейс

Откройте `http://localhost:8000` для доступа к веб-интерфейсу мониторинга.

### 2. API endpoints

- `GET /health` - Проверка состояния
- `GET /status` - Статус системы
- `GET /logs` - Логи системы
- `POST /restart` - Перезапуск системы

### 3. Команды Telegram бота

- `/start` - Начало работы
- `/help` - Справка
- `/status` - Статус системы
- `/report` - Отчет
- `/problems` - Список проблем
- `/restart` - Перезапуск

## 🆘 Получение помощи

### 1. Логи и отладка

```bash
# Основные логи
tail -f logs/main.log

# Логи производительности
tail -f logs/performance.log

# Системные логи
./start.sh logs --follow
```

### 2. Диагностика

```bash
# Полная диагностика
python3 test_system.py

# Проверка конфигурации
python3 config.py --validate

# Тест уведомлений
python3 notifications.py --test
```

### 3. Контакты

- Создайте Issue в репозитории
- Проверьте документацию в `README.md`
- Изучите примеры в `examples/`

## 🎯 Следующие шаги

После успешной установки:

1. **Настройте интеграции** - убедитесь, что все API работают
2. **Протестируйте уведомления** - проверьте работу Telegram и Slack
3. **Настройте Google Sheets** - создайте таблицы для отчетов
4. **Запустите мониторинг** - настройте автоматическое отслеживание
5. **Изучите возможности** - изучите все функции системы

---

**Удачи с настройкой! 🚀**

Если у вас возникли вопросы, обратитесь к документации или создайте Issue.