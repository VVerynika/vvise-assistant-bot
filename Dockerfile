# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /workspace

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скачиваем модели для spaCy
RUN python -m spacy download en_core_web_sm

# Скачиваем данные для NLTK
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"

# Копируем исходный код
COPY . .

# Создаем необходимые директории
RUN mkdir -p /workspace/logs /workspace/data

# Устанавливаем права на выполнение
RUN chmod +x *.py

# Создаем пользователя для безопасности
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /workspace

# Переключаемся на пользователя
USER botuser

# Открываем порт для веб-интерфейса (если понадобится)
EXPOSE 8000

# Команда по умолчанию
CMD ["python3", "main.py"]