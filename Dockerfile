FROM python:3.10-slim  # Используем slim версию для уменьшения размера образа

# Устанавливаем системные зависимости для pandas/numpy
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала копируем requirements.txt для кэширования слоя
COPY requirements.txt .

# Устанавливаем pip и зависимости
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY . .

CMD ["python", "bot.py"]