#!/bin/bash

# Скрипт для быстрого запуска системы бота-помощника

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Проверка наличия Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python 3 не найден. Установите Python 3.11+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log "Найден Python $PYTHON_VERSION"
}

# Проверка переменных окружения
check_env() {
    if [ ! -f .env ]; then
        error "Файл .env не найден. Создайте его на основе .env.example"
        exit 1
    fi
    
    # Проверяем основные переменные
    source .env
    
    if [ -z "$SLACK_TOKEN" ]; then
        warn "SLACK_TOKEN не настроен"
    fi
    
    if [ -z "$CLICKUP_API_TOKEN" ]; then
        warn "CLICKUP_API_TOKEN не настроен"
    fi
    
    if [ -z "$TELEGRAM_TOKEN" ]; then
        warn "TELEGRAM_TOKEN не настроен"
    fi
    
    if [ -z "$GOOGLE_SHEET_ID" ]; then
        warn "GOOGLE_SHEET_ID не настроен"
    fi
    
    log "Переменные окружения проверены"
}

# Установка зависимостей
install_dependencies() {
    log "Установка Python зависимостей..."
    
    if [ ! -f requirements.txt ]; then
        error "Файл requirements.txt не найден"
        exit 1
    fi
    
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
    
    log "Зависимости установлены"
}

# Создание необходимых директорий
create_directories() {
    log "Создание необходимых директорий..."
    
    mkdir -p logs data static
    
    log "Директории созданы"
}

# Проверка модулей
check_modules() {
    log "Проверка модулей..."
    
    python3 -c "
import sys
modules = ['problem_analyzer', 'google_sheets_manager', 'slack_integration', 'clickup_integration', 'telegram_bot']
missing = []

for module in modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except ImportError as e:
        print(f'❌ {module}: {e}')
        missing.append(module)

if missing:
    print(f'\\n❌ Отсутствуют модули: {', '.join(missing)}')
    sys.exit(1)
else:
    print('\\n✅ Все модули доступны')
"
    
    if [ $? -ne 0 ]; then
        error "Проверка модулей не пройдена"
        exit 1
    fi
}

# Запуск тестов
run_tests() {
    log "Запуск тестов системы..."
    
    if [ -f test_system.py ]; then
        python3 test_system.py
        if [ $? -eq 0 ]; then
            log "Тесты пройдены успешно"
        else
            warn "Тесты не пройдены, но продолжаем запуск"
        fi
    else
        warn "Файл test_system.py не найден, пропускаем тесты"
    fi
}

# Запуск системы
start_system() {
    log "Запуск системы..."
    
    if [ "$1" = "--foreground" ]; then
        log "Запуск в интерактивном режиме"
        python3 main.py
    else
        log "Запуск в фоновом режиме"
        python3 run_background.py &
        echo $! > bot.pid
        log "Система запущена в фоне (PID: $(cat bot.pid))"
    fi
}

# Проверка статуса
check_status() {
    if [ -f bot.pid ]; then
        PID=$(cat bot.pid)
        if ps -p $PID > /dev/null 2>&1; then
            log "Система работает (PID: $PID)"
            return 0
        else
            warn "Процесс не найден, удаляем PID файл"
            rm -f bot.pid
            return 1
        fi
    else
        return 1
    fi
}

# Остановка системы
stop_system() {
    if check_status; then
        PID=$(cat bot.pid)
        log "Остановка системы (PID: $PID)..."
        
        kill $PID
        
        # Ждем завершения
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # Принудительная остановка
        if ps -p $PID > /dev/null 2>&1; then
            warn "Принудительная остановка..."
            kill -9 $PID
        fi
        
        rm -f bot.pid
        log "Система остановлена"
    else
        log "Система не запущена"
    fi
}

# Основная функция
main() {
    case "${1:-start}" in
        "start")
            if check_status; then
                error "Система уже запущена"
                exit 1
            fi
            
            check_python
            check_env
            install_dependencies
            create_directories
            check_modules
            run_tests
            start_system "$2"
            ;;
        "stop")
            stop_system
            ;;
        "restart")
            stop_system
            sleep 2
            $0 start "$2"
            ;;
        "status")
            if check_status; then
                exit 0
            else
                exit 1
            fi
            ;;
        "test")
            check_python
            check_env
            install_dependencies
            create_directories
            check_modules
            run_tests
            ;;
        "install")
            check_python
            check_env
            install_dependencies
            create_directories
            check_modules
            ;;
        "help"|"-h"|"--help")
            echo "Использование: $0 [команда] [опции]"
            echo ""
            echo "Команды:"
            echo "  start [--foreground]  Запуск системы (по умолчанию в фоне)"
            echo "  stop                   Остановка системы"
            echo "  restart [--foreground] Перезапуск системы"
            echo "  status                 Проверка статуса"
            echo "  test                   Запуск тестов"
            echo "  install                Установка зависимостей"
            echo "  help                   Показать эту справку"
            echo ""
            echo "Опции:"
            echo "  --foreground          Запуск в интерактивном режиме"
            echo ""
            echo "Примеры:"
            echo "  $0 start              # Запуск в фоне"
            echo "  $0 start --foreground # Запуск в интерактивном режиме"
            echo "  $0 stop               # Остановка"
            echo "  $0 status             # Проверка статуса"
            ;;
        *)
            error "Неизвестная команда: $1"
            echo "Используйте '$0 help' для справки"
            exit 1
            ;;
    esac
}

# Обработка сигналов
trap 'log "Получен сигнал остановки"; exit 0' SIGINT SIGTERM

# Запуск основной функции
main "$@"