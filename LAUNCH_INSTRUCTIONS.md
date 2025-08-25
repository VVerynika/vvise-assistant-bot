# 🚀 ИНСТРУКЦИЯ ПО ЗАПУСКУ СИСТЕМЫ

## 📋 Что нужно сделать для запуска системы

### 🔑 **Шаг 1: Получение API токенов**

#### **1.1 Slack Bot Token:**
1. Перейдите на [https://api.slack.com/apps](https://api.slack.com/apps)
2. Создайте новое приложение (Create New App)
3. Выберите "From scratch"
4. Добавьте следующие OAuth Scopes:
   - `channels:read`
   - `channels:history`
   - `groups:read`
   - `groups:history`
   - `im:read`
   - `im:history`
   - `mpim:read`
   - `mpim:history`
   - `users:read`
5. Установите приложение в workspace
6. Скопируйте **Bot User OAuth Token** (начинается с `xoxb-`)

#### **1.2 ClickUp API Token:**
1. Перейдите в [ClickUp Settings](https://app.clickup.com/settings)
2. Выберите **Apps** → **API Token**
3. Создайте новый токен
4. Скопируйте токен

#### **1.3 ClickUp Workspace ID:**
1. Откройте ClickUp в браузере
2. URL будет выглядеть: `https://app.clickup.com/workspace/WORKSPACE_ID`
3. Скопируйте **WORKSPACE_ID** из URL

#### **1.4 Telegram Bot Token:**
1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям
4. Получите токен бота

#### **1.5 Telegram User ID:**
1. Найдите @userinfobot в Telegram
2. Отправьте `/start`
3. Получите ваш User ID

#### **1.6 Google Sheets (опционально):**
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект
3. Включите Google Sheets API
4. Создайте Service Account
5. Скачайте JSON ключ
6. Создайте Google Sheets таблицу
7. Скопируйте ID таблицы из URL

---

### ⚙️ **Шаг 2: Настройка переменных окружения**

#### **2.1 Отредактируйте файл .env:**
```bash
nano .env
```

#### **2.2 Замените placeholder значения на реальные:**
```env
# Slack Integration
SLACK_TOKEN=xoxb-REAL-SLACK-TOKEN-HERE

# ClickUp Integration
CLICKUP_API_TOKEN=REAL-CLICKUP-TOKEN-HERE
CLICKUP_WORKSPACE_ID=REAL-WORKSPACE-ID-HERE

# Telegram Bot
TELEGRAM_TOKEN=REAL-TELEGRAM-TOKEN-HERE
TELEGRAM_AUTHORIZED_USERS=YOUR-REAL-USER-ID-HERE

# Google Sheets (если используете)
GOOGLE_SHEET_ID=REAL-SHEET-ID-HERE
SERVICE_ACCOUNT_JSON_PATH=/path/to/real-service-account.json

# Остальные настройки оставьте как есть
```

---

### 🚀 **Шаг 3: Запуск системы**

#### **3.1 Автоматический запуск (рекомендуется):**
```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите автоматическую установку
python3 quick_start.py
```

#### **3.2 Ручной запуск:**
```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Установите зависимости (если еще не установлены)
pip install -r requirements.txt

# Запустите основную систему в фоне
python3 run_background.py &

# Запустите веб-сервер
python3 web_server.py &
```

#### **3.3 Через start.sh:**
```bash
# Сделайте скрипт исполняемым
chmod +x start.sh

# Запустите систему
./start.sh start
```

---

### 🌐 **Шаг 4: Проверка работы**

#### **4.1 Проверьте процессы:**
```bash
ps -ef | grep python
```

#### **4.2 Проверьте веб-интерфейс:**
Откройте в браузере: http://localhost:8000

#### **4.3 Проверьте API:**
```bash
# Health check
curl http://localhost:8000/health

# Статус системы
curl http://localhost:8000/api/status
```

#### **4.4 Проверьте Telegram бота:**
Отправьте боту команду `/start`

---

## 🎯 **Что запускать в первую очередь**

### **Для локального использования:**
1. **Настройте .env файл** с реальными токенами
2. **Запустите**: `python3 quick_start.py`
3. **Откройте**: http://localhost:8000

### **Для Render Background Worker:**
1. **Настройте .env файл** с реальными токенами
2. **Запустите развертывание** через Deploy Hook
3. **Или настройте в Render**:
   - Создайте Background Worker
   - Подключите репозиторий
   - Установите переменные окружения
   - Команда запуска: `python3 run_background.py`

---

## 🔧 **Минимальные требования для работы**

### **Обязательные переменные:**
```env
SLACK_TOKEN=xoxb-...
CLICKUP_API_TOKEN=...
CLICKUP_WORKSPACE_ID=...
TELEGRAM_TOKEN=...
TELEGRAM_AUTHORIZED_USERS=...
```

### **Опциональные переменные:**
```env
GOOGLE_SHEET_ID=...
SERVICE_ACCOUNT_JSON_PATH=...
```

---

## 🚨 **Частые проблемы и решения**

### **Проблема: "Module not found"**
```bash
# Решение: Активируйте виртуальное окружение
source venv/bin/activate
```

### **Проблема: "Permission denied"**
```bash
# Решение: Сделайте скрипты исполняемыми
chmod +x *.py *.sh
```

### **Проблема: "Port already in use"**
```bash
# Решение: Остановите процессы
pkill -f "python3.*web_server.py"
pkill -f "python3.*run_background.py"
```

### **Проблема: "API token invalid"**
```bash
# Решение: Проверьте токены в .env файле
cat .env | grep TOKEN
```

---

## 📱 **Проверка работы компонентов**

### **Slack Integration:**
- Проверьте логи: `tail -f logs/main.log`
- Ищите сообщения о подключении к Slack

### **ClickUp Integration:**
- Проверьте логи на ошибки API
- Убедитесь, что workspace ID правильный

### **Telegram Bot:**
- Отправьте `/start` боту
- Проверьте ответ

### **Веб-интерфейс:**
- Откройте http://localhost:8000
- Проверьте статус компонентов

---

## 🎉 **После успешного запуска**

### **Что должно работать:**
1. ✅ Веб-интерфейс на http://localhost:8000
2. ✅ Telegram бот отвечает на команды
3. ✅ Slack интеграция мониторит каналы
4. ✅ ClickUp интеграция анализирует задачи
5. ✅ Автоматические обновления каждые 5 минут
6. ✅ Логирование всех операций

### **Доступные команды Telegram:**
- `/start` - Начало работы
- `/status` - Статус системы
- `/report` - Сводный отчет
- `/problems` - Список проблем
- `/help` - Справка

---

## 🚀 **Быстрый старт (TL;DR)**

```bash
# 1. Настройте .env с реальными токенами
nano .env

# 2. Запустите систему
source venv/bin/activate
python3 quick_start.py

# 3. Откройте веб-интерфейс
# http://localhost:8000

# 4. Проверьте Telegram бота
# Отправьте /start
```

---

**🎯 Следуйте этим инструкциям, и система заработает!**

**Дата**: 25 августа 2025  
**Статус**: 🚀 ГОТОВО К ЗАПУСКУ