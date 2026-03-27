import logging
import hashlib
import uvicorn
import os
import socket
import time
import aiohttp
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, BotCommand, Update
)
from aiogram.filters import CommandStart
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from handlers.channels import router as channels_router
from handlers.posts import router as posts_router
from api import api_router

load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
MINI_APP_URL   = os.getenv("MINI_APP_URL", "https://randomway.pro/")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", "https://api.randomway.pro")
WEBHOOK_PATH   = "/webhook"
WEBHOOK_SECRET = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]


# 🔥 FIX 1: IPv6 Black Hole — Docker пытается IPv6, висит 15-30 сек, потом падает.
# Подкласс работает на всех версиях aiogram 3.x (в отличие от connector= kwarg).
class IPv4AiohttpSession(AiohttpSession):
    async def create_connector(self, app=None) -> aiohttp.TCPConnector:
        return aiohttp.TCPConnector(family=socket.AF_INET)


# 🔥 FIX 2: Redis с жёсткими таймаутами — без них зависание на 30 сек если Redis недоступен
redis_client = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    socket_connect_timeout=2,
    socket_timeout=2,
)
storage = RedisStorage(redis=redis_client)

bot = Bot(
    token=BOT_TOKEN,
    session=IPv4AiohttpSession(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=storage)

dp.include_router(channels_router)
dp.include_router(posts_router)


@dp.message(CommandStart())
async def start_default(message: Message):
    t = time.monotonic()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎲 Открыть RandomWay",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])
    await message.answer(
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.\n\nОткрыть приложение 👇",
        reply_markup=kb
    )
    logging.info(f"⚡ /start отправлен за {(time.monotonic() - t) * 1000:.0f}ms")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("🚀 Запуск приложения...")

    try:
        info = await bot.get_me()
        os.environ["BOT_USERNAME"] = info.username
        app.state.bot_id = info.id
        logging.info(f"✅ Бот подключён: @{info.username}")
    except Exception as e:
        logging.error(f"❌ Ошибка подключения к Telegram API: {e}")
        app.state.bot_id = 0

    try:
        await bot.set_my_commands([
            BotCommand(command="newchannel", description="Добавить канал или группу"),
            BotCommand(command="newpost",    description="Создать шаблон поста"),
            BotCommand(command="cancel",     description="Отменить текущее действие"),
        ])
        webhook_target = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
        await bot.set_webhook(
            url=webhook_target,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        logging.info(f"✅ Вебхук установлен: {webhook_target}")
    except Exception as e:
        logging.error