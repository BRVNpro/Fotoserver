# Используем официальный образ Python 3.12 slim в качестве этапа сборки (builder stage)
FROM python:3.12-slim AS builder

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл requirements.txt для установки зависимостей
COPY requirements.txt .

# Устанавливаем зависимости локально, чтобы минимизировать размер финального образа
RUN pip install --user -r requirements.txt


# Основной этап (production stage)
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем установленные зависимости из builder-этапа
COPY --from=builder /root/.local /root/.local

# Добавляем путь к пользовательским скриптам в системную PATH
ENV PATH=/root/.local/bin:$PATH

# Копируем остальной код приложения в контейнер
COPY . .

# Объявляем порт, на котором будет работать приложение
EXPOSE 8000

# Запускаем сервер Uvicorn с указанием файла main.py и объекта app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

