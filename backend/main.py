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
from handlers import channels as channel_handlers
from handlers import posts as post_handlers
from handlers import callbacks as callback_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
MINI_APP_URL   = os.getenv("MINI_APP_URL", "https://randomway.pro/")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", "https://api.randomway.pro")
WEBHOOK_PATH   = "/webhook"
WEBHOOK_SECRET = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:32]

storage = MemoryStorage()
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=storage)
dp.include_router(channel_handlers.router)
dp.include_router(post_handlers.router)
dp.include_router(callback_handlers.router)


async def handle_check_results(message: Message, giveaway_id: int):
    """Отправляет подробные результаты розыгрыша в личку"""
    from database import AsyncSessionLocal
    from models import Giveaway, Participant, User
    from sqlalchemy.future import select
    from sqlalchemy import func

    async with AsyncSessionLocal() as db:
        giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
        if not giveaway:
            await message.answer("❌ Розыгрыш не найден.")
            return

        # Кол-во участников
        total = await db.scalar(
            select(func.count(Participant.id)).where(
                Participant.giveaway_id == giveaway_id,
                Participant.is_active == True
            )
        )

        # Победители с данными пользователей
        result = await db.execute(
            select(Participant, User)
            .join(User, Participant.user_id == User.telegram_id)
            .where(
                Participant.giveaway_id == giveaway_id,
                Participant.is_winner == True
            )
        )
        winners = result.all()

        # Дата завершения
        end_str = giveaway.end_date.strftime("%d.%m.%Y %H:%M") if giveaway.end_date else "—"

        # Формируем список победителей
        winners_lines = []
        for i, (p, u) in enumerate(winners, 1):
            uid = u.telegram_id
            if u.username:
                name_link = f'<a href="https://t.me/{u.username}">@{u.username}</a> ({uid})'
            else:
                name_link = f'<a href="tg://user?id={uid}">{u.first_name}</a> ({uid})'
            winners_lines.append(f"{i}. {name_link}")

        winners_text = "\n".join(winners_lines) if winners_lines else "Победители не определены"

        text = (
            f'🎁 Розыгрыш "<b>{giveaway.title}</b>"\n'
            f'👥 Кол-во участников: <b>{total or 0}</b>\n'
            f'🏆 Кол-во победителей: <b>{giveaway.winners_count}</b>\n'
            f'✅ Розыгрыш завершён: <b>{end_str}</b>\n\n'
            f'🎉 Результаты розыгрыша:\n'
            f'<b>Победители:</b>\n{winners_text}'
        )

        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@dp.message(CommandStart())
async def start_default(message: Message):
    # Извлекаем start параметр
    start_param = ""
    if message.text and " " in message.text:
        start_param = message.text.split(" ", 1)[1].strip()

    # Проверка результатов розыгрыша
    if start_param.startswith("checklot"):
        try:
            giveaway_id = int(start_param.replace("checklot", ""))
            await handle_check_results(message, giveaway_id)
        except (ValueError, Exception) as e:
            logging.error(f"checklot error: {e}")
            await message.answer("❌ Не удалось загрузить результаты.")
        return

    # Переход к розыгрышу через Mini App
    if start_param.startswith("gw_"):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🎲 Участвовать в розыгрыше",
                web_app=WebAppInfo(url=f"{MINI_APP_URL}")
            )
        ]])
        await message.answer(
            "🎁 Открываю розыгрыш для вас...",
            reply_markup=kb
        )
        return

    # Обычный старт
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://randomway.pro"],
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
    from database import engine
    import redis.asyncio as aioredis
    errors = {}
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        errors["postgres"] = str(e)
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