import asyncio
import logging
import uvicorn
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.filters import CommandStart, CommandObject

from handlers.channels import router as channels_router, start_deep_link as channel_deep
from handlers.posts    import router as posts_router,   _show_prompt
from api import router as api_router

load_dotenv()

BOT_TOKEN  = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

# ── Единый обработчик всех deep links (/start PARAM) ─────────────────────────
# Mini App вызывает: openTelegramLink("https://t.me/BOT?start=add_channel")
# Telegram отправляет боту: /start add_channel
# command.args == "add_channel" или "add_post"

@dp.message(CommandStart(deep_link=True))
async def handle_deep_link(message: Message, command: CommandObject, state, bot: Bot):
    args = command.args
    if args == "add_channel":
        await channel_deep(message, command, state, bot)
    elif args == "add_post":
        await _show_prompt(message, state)


# ── Обычный /start без параметров ────────────────────────────────────────────

@dp.message(CommandStart())
async def start_default(message: Message):
    await message.answer(
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.\n\n"
        "Нажми кнопку ниже чтобы начать 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🎲 Открыть приложение", web_app=WebAppInfo(url=MINI_APP_URL))
        ]]),
    )


# ── Подключаем роутеры (без CommandStart — они уже обработаны выше) ───────────

dp.include_router(channels_router)
dp.include_router(posts_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        info = await bot.get_me()
        os.environ["BOT_USERNAME"] = info.username
        logging.info(f"Bot: @{info.username}")
    except Exception as e:
        logging.error(f"get_me failed: {e}")

    asyncio.create_task(dp.start_polling(bot))
    yield
    await bot.session.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://randomway.pro", "http://localhost:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/")
async def root():
    return {"status": "ok"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)