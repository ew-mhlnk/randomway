import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎲 Открыть RandomWay", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])
    await message.answer(
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.\n\n"
        "🎯 Организуй розыгрыш за пару минут\n"
        "🔗 Реф-ссылки для друзей\n"
        "⚡️ Автоматический выбор победителей\n\n"
        "Нажми кнопку ниже чтобы начать 👇",
        reply_markup=keyboard
    )

# Lifespan - это сердце нашей архитектуры. Оно запускает бота ВМЕСТЕ с сервером API.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск бота в фоновом режиме
    asyncio.create_task(dp.start_polling(bot))
    yield
    # Отключение бота при перезагрузке сервера
    await bot.session.close()

# Инициализация FastAPI
app = FastAPI(lifespan=lifespan)

# CORS - разрешаем нашему сайту randomway.pro обращаться к этому API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://randomway.pro", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутер с нашими путями из api.py
from api import router as api_router
app.include_router(api_router)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Запускаем сервер Uvicorn на порту 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)