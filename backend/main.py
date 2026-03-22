import logging
import hashlib
import uvicorn
import os
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

# 🔥 ЖЕСТКИЕ ТАЙМАУТЫ НА REDIS (Fail Fast)
# Если Coolify не может достучаться до Redis - он упадет через 2 секунды, а не через 30.
redis_client = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    socket_connect_timeout=2.0,
    socket_timeout=5.0
)
storage = RedisStorage(redis=redis_client)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher(storage=storage)

dp.include_router(channels_router)
dp.include_router(posts_router)


@dp.message(CommandStart())
async def start_default(message: Message):
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Пингуем Redis при старте сервера. Если он лежит - мы узнаем это сразу в логах деплоя Coolify
    try:
        await redis_client.ping()
        logging.info("✅ Redis connection established!")
    except Exception as e:
        logging.error(f"❌ Redis is DOWN or unreachable: {e}")

    try:
        info = await bot.get_me()
        os.environ["BOT_USERNAME"] = info.username
        app.state.bot_id = info.id
    except Exception as e:
        logging.error(f"get_me failed: {e}")
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
        logging.error(f"Telegram API setup failed: {e}")

    app.state.bot = bot
    app.state.dp  = dp
    yield
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    await bot.session.close()
    await redis_client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# Обертка для фоновых задач, чтобы ошибки не пропадали
async def process_update_safe(update: Update):
    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.error(f"Ошибка при обработке вебхука: {e}", exc_info=True)


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