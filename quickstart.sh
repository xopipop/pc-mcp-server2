#!/bin/bash

echo "========================================"
echo "PC Control MCP Server - Быстрый запуск"
echo "========================================"
echo

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log_info() {
    echo -e "[INFO] $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_error() {
    echo -e "${RED}[ОШИБКА]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[ПРЕДУПРЕЖДЕНИЕ]${NC} $1"
}

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    log_error "Python не найден. Пожалуйста, установите Python 3.8+"
    echo "Установка:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  macOS: brew install python3"
    echo "  Или скачайте с: https://www.python.org/downloads/"
    exit 1
fi

# Проверка версии Python
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    log_error "Требуется Python $required_version или выше. Установлен: $python_version"
    exit 1
fi

log_success "Python $python_version найден"

# Проверка наличия виртуального окружения
if [ ! -d "venv" ]; then
    log_info "Создание виртуального окружения..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        log_error "Не удалось создать виртуальное окружение"
        exit 1
    fi
    log_success "Виртуальное окружение создано"
fi

# Активация виртуального окружения
log_info "Активация виртуального окружения..."
source venv/bin/activate

# Обновление pip
pip install --upgrade pip > /dev/null 2>&1

# Проверка и установка зависимостей
log_info "Проверка зависимостей..."
if ! pip show mcp > /dev/null 2>&1; then
    log_info "Установка зависимостей..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        log_error "Не удалось установить зависимости"
        exit 1
    fi
    log_success "Зависимости установлены"
else
    log_success "Зависимости уже установлены"
fi

# Проверка конфигурации
if [ ! -f "config/local.yaml" ]; then
    log_info "Создание локальной конфигурации..."
    if [ -f "config/default.yaml" ]; then
        cp config/default.yaml config/local.yaml
        log_success "Локальная конфигурация создана"
    fi
fi

# Проверка прав суперпользователя
if [ "$EUID" -ne 0 ]; then 
    echo
    log_warning "Сервер запущен БЕЗ прав суперпользователя"
    echo "Некоторые функции могут быть недоступны:"
    echo "- Управление службами"
    echo "- Некоторые системные операции"
    echo "- Низкоуровневые сетевые операции"
    echo
    echo "Для полного функционала запустите с sudo"
    echo
fi

# Определение ОС
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
fi

log_info "Обнаружена ОС: $OS"

# Запуск сервера
echo
log_info "Запуск PC Control MCP Server..."
echo "========================================"
echo

# Установка переменных окружения для отключения безопасности в dev режиме
export PC_CONTROL_SECURITY__ENABLED=false
export PC_CONTROL_LOGGING__LEVEL=INFO

# Обработка сигналов для корректного завершения
trap 'echo; log_info "Остановка сервера..."; deactivate; exit' INT TERM

# Запуск
python3 main.py

# Обработка завершения
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo
    log_error "Сервер завершился с ошибкой (код: $exit_code)"
fi

deactivate