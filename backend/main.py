"""backend\main.py"""

import logging
import uvicorn
import os
import hashlib
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, BotCommand, Update, ReplyKeyboardRemove
)
from aiogram.filters import CommandStart, Command

from handlers.channels import router as channels_router
from handlers.posts import router as posts_router
from api import router as api_router

load_dotenv()

BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")
WEBHOOK_URL  = os.getenv("WEBHOOK_URL", "")  # e.g. https://api.randomway.pro

# Секрет для верификации вебхука — можно задать явно в .env,
# иначе автоматически выводится из токена бота (стабильно и не нужен доп. секрет).
WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]
)

WEBHOOK_PATH = "/webhook"

# ── Bot & Dispatcher ──────────────────────────────────────────────────────────

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()

dp.include_router(channels_router)
dp.include_router(posts_router)


# ── /start handler ────────────────────────────────────────────────────────────
# Больше нет постоянной Reply-клавиатуры — только приветствие + кнопка открыть приложение.
# Если пользователь пришёл с deep link (newchannel / newpost) — хэндлер
# уже зарегистрирован в channels_router / posts_router и перехватит раньше,
# потому что роутеры подключены до этого общего хэндлера.

@dp.message(CommandStart())
async def start_default(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎲 Открыть RandomWay",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])
    # На всякий случай убираем любую Reply-клавиатуру, которая могла остаться
    # от старой версии бота (с persistent=True).
    await message.answer(
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.\n\n"
        "Нажмите кнопку ниже, чтобы открыть приложение 👇",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        "Открыть приложение:",
        reply_markup=kb
    )


# ── Lifespan: регистрируем вебхук при старте, удаляем при остановке ──────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Получаем юзернейм бота
    try:
        bot_info = await bot.get_me()
        os.environ["BOT_USERNAME"] = bot_info.username
        logging.info(f"Bot: @{bot_info.username}")
    except Exception as e:
        logging.error(f"get_me failed: {e}")

    # 2. Регистрируем команды (синее меню в боте)
    try:
        await bot.set_my_commands([
            BotCommand(command="newchannel", description="Добавить канал или группу"),
            BotCommand(command="newpost",    description="Создать новый шаблон поста"),
            BotCommand(command="cancel",     description="Отменить текущее действие"),
        ])
    except Exception as e:
        logging.error(f"set_my_commands failed: {e}")

    # 3. Устанавливаем вебхук
    webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    try:
        await bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            # Говорим Telegram какие типы апдейтов нам нужны
            allowed_updates=dp.resolve_used_update_types(),
            # Дропаем накопившиеся апдейты (от старого polling режима)
            drop_pending_updates=True,
        )
        logging.info(f"Webhook set: {webhook_url}")
    except Exception as e:
        logging.error(f"set_webhook failed: {e}")

    app.state.bot = bot

    yield

    # Teardown: удаляем вебхук и закрываем сессию
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Webhook deleted")
    except Exception as e:
        logging.error(f"delete_webhook failed: {e}")

    await bot.session.close()


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://randomway.pro", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """
    Telegram шлёт сюда POST при каждом апдейте.
    Проверяем секретный токен → скармливаем апдейт диспетчеру.
    """
    # Верификация: Telegram добавляет заголовок X-Telegram-Bot-Api-Secret-Token
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    data   = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return JSONResponse({"ok": True})


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/health")
async def health():
    """Используется Coolify для проверки живости контейнера"""
    return {"status": "ok"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)