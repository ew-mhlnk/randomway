import logging
import hashlib
import uvicorn
import os
import time
import asyncio
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

# Импорты хранилища (Redis)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

# Подключаем наш общий роутер из папки api/
from api import api_router

load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
MINI_APP_URL   = os.getenv("MINI_APP_URL", "https://randomway.pro/")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", "https://api.randomway.pro")
WEBHOOK_PATH   = "/webhook"
WEBHOOK_SECRET = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]

# 🚀 REDIS: С жестким тайм-аутом, чтобы не зависать
redis_url = os.getenv("REDIS_URL", "")
if redis_url and "localhost" not in redis_url:
    try:
        redis_client = Redis.from_url(redis_url, socket_connect_timeout=2.0)
        storage = RedisStorage(redis=redis_client)
    except Exception:
        storage = MemoryStorage()
else:
    storage = MemoryStorage()

bot = Bot(
    token=BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=storage)


@dp.message(CommandStart())
async def start_default(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎲 Открыть RandomWay", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    await message.answer(
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.\n\nОткрыть приложение 👇",
        reply_markup=kb
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Пингуем Telegram при старте
    try:
        info = await bot.get_me()
        os.environ["BOT_USERNAME"] = info.username
        app.state.bot_id = info.id
    except Exception:
        app.state.bot_id = 0

    # Ставим команды и вебхук
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
        await bot.session.close()
    except Exception:
        pass

# 🔥 ВОТ ОНА — ПЕРЕМЕННАЯ APP, КОТОРУЮ ИСКАЛ UVICORN!
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем все наши эндпоинты (каналы, шаблоны, розыгрыши)
app.include_router(api_router)


# Обертка для безопасности фоновых задач
async def process_update_safe(update: Update):
    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.error(f"❌ Ошибка при обработке вебхука: {e}", exc_info=True)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request, bg_tasks: BackgroundTasks):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    update_data = await request.json()
    update = Update.model_validate(update_data)

    # Fire-and-forget: отправляем в фон, отвечаем мгновенно
    bg_tasks.add_task(process_update_safe, update)
    return JSONResponse({"ok": True})


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)