# backend\Dockerfile

FROM python:3.12-slim
WORKDIR /app

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# ГОВОРИМ COOLIFY, КАКОЙ ПОРТ ОТКРЫТ (Именно этого не хватало!)
EXPOSE 8000

# DevOps-подход: сначала накатываем миграции, затем запускаем сервер
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --forwarded-allow-ips="*"