"""backend\main.py"""

import logging
import hashlib
import uvicorn
import os
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
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.channels import router as channels_router
from handlers.posts import router as posts_router
from api import router as api_router

load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
MINI_APP_URL   = os.getenv("MINI_APP_URL", "https://randomway.pro/")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", "https://api.randomway.pro")
WEBHOOK_PATH   = "/webhook"
WEBHOOK_SECRET = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]

# Для production в будущем рекомендуется заменить MemoryStorage на RedisStorage,
# чтобы стейты не сбрасывались при перезапуске контейнера.
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher(storage=storage)

# Подключаем роутеры
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
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer("Открыть приложение 👇", reply_markup=kb)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Кешируем bot_id и username при старте
    try:
        info = await bot.get_me()
        os.environ["BOT_USERNAME"] = info.username
        app.state.bot_id = info.id
        logging.info(f"Bot: @{info.username} (id={info.id})")
    except Exception as e:
        logging.error(f"get_me failed: {e}")
        app.state.bot_id = 0

    try:
        await bot.set_my_commands([
            BotCommand(command="newchannel", description="Добавить канал или группу"),
            BotCommand(command="newpost",    description="Создать шаблон поста"),
            BotCommand(command="cancel",     description="Отменить текущее действие"),
        ])
    except Exception as e:
        logging.error(f"set_my_commands failed: {e}")

    try:
        await bot.set_webhook(
            url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
            secret_token=WEBHOOK_SECRET,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        logging.info(f"Webhook: {WEBHOOK_URL}{WEBHOOK_PATH}")
    except Exception as e:
        logging.error(f"set_webhook failed: {e}")

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
    allow_origins=["https://randomway.pro", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    update_data = await request.json()
    update = Update.model_validate(update_data)
    
    # 🔥 ГЛАВНЫЙ ФИКС СПАМА: Оборачиваем в try-except. 
    # Теперь Telegram всегда будет получать "ok": True и не будет слать апдейты по кругу
    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.error(f"Ошибка при обработке апдейта {update.update_id}: {e}")
        
    return JSONResponse({"ok": True})


@app.get("/")
@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)