import logging
import hashlib
import uvicorn
import os
import asyncio
import socket
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, BotCommand, Update
)
from aiogram.filters import CommandStart

# Импорты для сети и хранилища
import aiohttp
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from handlers.channels import router as channels_router
from handlers.posts import router as posts_router
from api import router as api_router

load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
MINI_APP_URL   = os.getenv("MINI_APP_URL", "https://randomway.pro/")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", "https://api.randomway.pro")
WEBHOOK_PATH   = "/webhook"
WEBHOOK_SECRET = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]

# 🚀 1. ФИКС СЕТИ: Принудительно используем IPv4, чтобы избежать зависаний Docker (IPv6 Blackhole)
connector = aiohttp.TCPConnector(family=socket.AF_INET)
session = AiohttpSession(connector=connector)

# 🚀 2. REDIS: С жестким тайм-аутом, чтобы не зависать
redis_url = os.getenv("REDIS_URL", "")
if redis_url and "localhost" not in redis_url:
    try:
        redis_client = Redis.from_url(redis_url, socket_connect_timeout=2.0)
        storage = RedisStorage(redis=redis_client)
    except Exception:
        storage = MemoryStorage()
else:
    storage = MemoryStorage()

# Подключаем кастомную сессию IPv4 к боту
bot = Bot(
    token=BOT_TOKEN, 
    session=session, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=storage)

dp.include_router(channels_router)
dp.include_router(posts_router)


@dp.message(CommandStart())
async def start_default(message: Message):
    # Замеряем, насколько быстро бот формирует ответ
    start_time = time.time()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎲 Открыть RandomWay", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    await message.answer(
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.\n\nОткрыть приложение 👇",
        reply_markup=kb
    )
    
    elapsed = time.time() - start_time
    logging.info(f"⚡ /start обработан и отправлен за {elapsed:.3f} секунд!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        info = await bot.get_me()
        os.environ["BOT_USERNAME"] = info.username
        app.state.bot_id = info.id
    except Exception:
        app.state.bot_id = 0

    try:
        await bot.set_my_commands([
            BotCommand(command="newchannel", description="Добавить канал или группу"),
            BotCommand(command="newpost",    description="Создать шаблон поста"),
            BotCommand(command="cancel",     description="Отменить текущее действие"),
        ])
        await bot.set_webhook(
            url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
            secret_token=WEBHOOK_SECRET,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
    except Exception as e:
        logging.error(f"Webhook setup failed: {e}")

    app.state.bot = bot
    app.state.dp  = dp
    yield
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# Обертка для замеров скорости
async def process_update_safe(update: Update):
    start_time = time.time()
    try:
        await dp.feed_update(bot, update)
        elapsed = time.time() - start_time
        logging.info(f"✅ Апдейт {update.update_id} полностью обработан за {elapsed:.3f} сек.")
    except Exception as e:
        logging.error(f"❌ Ошибка при обработке: {e}", exc_info=True)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request, bg_tasks: BackgroundTasks):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    update_data = await request.json()
    update = Update.model_validate(update_data)

    bg_tasks.add_task(process_update_safe, update)
    return JSONResponse({"ok": True})


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)