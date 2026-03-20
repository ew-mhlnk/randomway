import asyncio
import logging
import uvicorn
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ReplyKeyboardRemove
)
from aiogram.filters import CommandStart

from handlers.channels import router as channels_router
from handlers.posts import router as posts_router
from api import router as api_router

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

dp.include_router(channels_router)
dp.include_router(posts_router)


def _main_keyboard() -> ReplyKeyboardMarkup:
    """
    Постоянная клавиатура в боте.
    Пользователь видит эти кнопки всегда когда открывает бота.
    Именно так работают конкуренты — openTelegramLink открывает бот,
    пользователь видит кнопки и тапает нужную.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📢 Добавить канал"),
                KeyboardButton(text="👥 Добавить группу"),
            ],
            [
                KeyboardButton(text="💬 Создать пост"),
            ],
            [
                KeyboardButton(
                    text="🎲 Открыть приложение",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                ),
            ],
        ],
        resize_keyboard=True,       # компактный размер
        persistent=True,            # всегда видна, не скрывается
    )


@dp.message(CommandStart())
async def start_default(message: Message):
    await message.answer(
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.\n\n"
        "Используйте кнопки ниже 👇",
        reply_markup=_main_keyboard(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        bot_info = await bot.get_me()
        os.environ["BOT_USERNAME"] = bot_info.username
        logging.info(f"Bot: @{bot_info.username}")
    except Exception as e:
        logging.error(f"get_me failed: {e}")

    try:
        await bot.delete_my_commands()
    except Exception:
        pass

    asyncio.create_task(dp.start_polling(bot))
    yield
    await bot.session.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://randomway.pro", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "RandomWay 🚀"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)