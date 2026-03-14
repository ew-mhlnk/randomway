# Этап 1: Установка зависимостей
FROM node:18-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
# Копируем только файлы конфигурации пакетов
COPY package.json package-lock.json* ./
RUN npm ci

# Этап 2: Сборка проекта
FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Собираем проект
RUN npm run build

# Этап 3: Запуск сервера (создаем микро-контейнер)
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV HOSTNAME "0.0.0.0"
ENV PORT 3000

# Копируем артефакты standalone-сборки
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

# ИСПРАВЛЕНА ОШИБКА ЗДЕСЬ (добавлен пробел после CMD)
CMD ["node", "server.js"]