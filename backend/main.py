"""backend/main.py"""
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
from aiogram.fsm.storage.memory import MemoryStorage

from api import api_router

# ── Импортируем ВСЕ aiogram-handlers и регистрируем в dp ────────────────────
from handlers import channels as channel_handlers
from handlers import posts as post_handlers
from handlers import callbacks as callback_handlers
# from handlers import participants as participant_handlers  # раскомментить когда создашь

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
MINI_APP_URL   = os.getenv("MINI_APP_URL", "https://randomway.pro/")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", "https://api.randomway.pro")
WEBHOOK_PATH   = "/webhook"
WEBHOOK_SECRET = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]

# TODO (Этап 5): Заменить на RedisStorage — см. комментарий в конце файла
storage = MemoryStorage()

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=storage)

# ── Регистрируем роутеры aiogram ─────────────────────────────────────────────
# ВАЖНО: порядок имеет значение — более специфичные хендлеры первыми
dp.include_router(channel_handlers.router)
dp.include_router(post_handlers.router)
dp.include_router(callback_handlers.router)


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
        logging.info("✅ Webhook установлен")
    except Exception as e:
        logging.error(f"Webhook setup failed: {e}")

    app.state.bot = bot
    app.state.dp  = dp
    yield

    try:
        await bot.session.close()
    except Exception:
        pass


app = FastAPI(lifespan=lifespan)

# ── CORS: только наш фронтенд ─────────────────────────────────────────────────
# Mini App работает на randomway.pro, API на api.randomway.pro
# Блокировать браузерный доступ к самому приложению — задача TelegramProvider.tsx
# CORS здесь защищает API от запросов с чужих доменов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://randomway.pro"],  # ← ТОЛЬКО наш домен, не wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router)


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
    bg_tasks.add_task(process_update_safe, update)
    return JSONResponse({"ok": True})


@app.get("/health")
async def health():
    """Реальная проверка здоровья — пингует PostgreSQL и Redis."""
    from database import engine
    import redis.asyncio as aioredis

    errors = {}

    # Проверка PostgreSQL
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        errors["postgres"] = str(e)

    # Проверка Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = await aioredis.from_url(redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
    except Exception as e:
        errors["redis"] = str(e)

    if errors:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "errors": errors}
        )

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)