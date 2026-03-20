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
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
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


@dp.message(CommandStart())
async def start_default(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🎲 Открыть RandomWay", web_app=WebAppInfo(url=MINI_APP_URL))
        ]]
    )
    await message.answer(
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.\n\n"
        "Нажми кнопку ниже чтобы начать 👇",
        reply_markup=keyboard,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Получаем username бота один раз при старте и кешируем в os.environ
    # Это убирает необходимость хардкодить BOT_USERNAME в .env
    try:
        bot_info = await bot.get_me()
        os.environ["BOT_USERNAME"] = bot_info.username
        logging.info(f"Bot username cached: @{bot_info.username}")
    except Exception as e:
        logging.error(f"Failed to get bot info: {e}")

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
    return {"status": "ok", "message": "Бэкенд RandomWay работает! 🚀"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)