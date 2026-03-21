"""backend\api.py"""

from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import urllib.parse
import hashlib
import hmac
import json
import os
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert  # Для правильного UPSERT в Postgres
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.base import StorageKey

from database import get_db
from models import User, Channel, PostTemplate
from services.giveaway_service import giveaway_service

router = APIRouter()
BOT_TOKEN    = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")

security = HTTPBearer()

# ── Auth helpers ──────────────────────────────────────────────────────────────

def validate_telegram_data(init_data: str) -> dict | None:
    parsed_data = dict(urllib.parse.parse_qsl(init_data))
    if "hash" not in parsed_data:
        return None
        
    hash_val = parsed_data.pop("hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if calculated_hash == hash_val:
        # Проверяем на Replay Attack (чтобы initData не жил вечно)
        auth_date = int(parsed_data.get("auth_date", 0))
        if time.time() - auth_date > 86400:  # 24 часа
            return None
        return json.loads(parsed_data.get("user", "{}"))
        
    return None

def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    user_data = validate_telegram_data(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись Telegram")
    return user_data["id"]

def get_user_id_from_query(initData: str) -> int:
    user_data = validate_telegram_data(initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return user_data["id"]

def fmt(count: int | None) -> str:
    if count is None: return "—"
    if count >= 1_000_000: return f"{count/1_000_000:.1f}M"
    if count >= 1_000: return f"{count/1_000:.1f}K"
    return str(count)

# ── Pydantic models ───────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    initData: str

class GiveawayCreateRequest(BaseModel):
    title: str
    type: str
    template_id: str
    winners_count: int

# ── Bot info ──────────────────────────────────────────────────────────────────

@router.get("/bot-info")
async def bot_info(user_id: int = Depends(get_user_id)):
    username = os.environ.get("BOT_USERNAME", "")
    if not username:
        raise HTTPException(status_code=500, detail="BOT_USERNAME не инициализирован")
    return {"username": username}

# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/auth")
async def authenticate_user(request: AuthRequest, db: AsyncSession = Depends(get_db)):
    user_data = validate_telegram_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись Telegram")

    tg_id = user_data.get("id")
    first_name = user_data.get("first_name", "")
    username = user_data.get("username", "")

    # PostgreSQL UPSERT: Защита от Race Condition при двойном быстром клике
    stmt = insert(User).values(
        telegram_id=tg_id,
        first_name=first_name,
        username=username,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["telegram_id"],
        set_=dict(first_name=stmt.excluded.first_name, username=stmt.excluded.username)
    )
    
    await db.execute(stmt)
    await db.commit()
    
    return {"status": "success", "user": user_data}

# ── Bot triggers ──────────────────────────────────────────────────────────────

@router.post("/bot/request-channel")
async def bot_request_channel(request: Request, user_id: int = Depends(get_user_id)):
    """
    Отправляет инструкцию и инлайн-кнопки (Deep Links) в личку.
    """
    bot = request.app.state.bot
    dp = request.app.state.dp
    bot_id = request.app.state.bot_id
    bot_username = os.getenv("BOT_USERNAME", "")

    # Импортируем из хендлера нужные зависимости
    from handlers.channels import ChannelStates, _add_chat_kb

    text = (
        "💬 Пришлите <b>username</b> канала в формате @durov или перешлите сообщение "
        "из канала (например приватного), который вы хотите добавить.\n\n"
        "⚠️ Бот должен быть админом канала с правами на публикацию и редактирование сообщений.\n\n"
        "Для отмены нажмите 👉🏻 /cancel\n\n"
        "🔥 Вы также можете добавить канал с помощью кнопки в меню "
        "(это удобно - бот сам добавится в админы с нужными правами) 👇🏻"
    )

    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=_add_chat_kb(bot_username)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось отправить сообщение: {e}")

    # Устанавливаем FSM-состояние
    key = StorageKey(bot_id=bot_id, chat_id=user_id, user_id=user_id)
    await dp.storage.set_state(key=key, state=ChannelStates.waiting_for_channel)

    return {"status": "ok"}


@router.post("/bot/request-post")
async def bot_request_post(request: Request, user_id: int = Depends(get_user_id)):
    bot    = request.app.state.bot
    dp     = request.app.state.dp
    bot_id = request.app.state.bot_id

    from handlers.posts import PostStates

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "💬 Отправьте текст вашего поста.\n\n"
                "✨ Можно прислать текст с картинкой или видео.\n"
                "Лимит: <b>4096</b> симв. без медиа, <b>1024</b> симв. с медиа.\n\n"
                "Поддерживаются кастомные эмодзи!\n\n"
                "Для отмены — /cancel"
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"send_message failed: {e}")

    key = StorageKey(bot_id=bot_id, chat_id=user_id, user_id=user_id)
    await dp.storage.set_state(key=key, state=PostStates.waiting_for_post)

    return {"status": "ok"}

# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/channels")
async def get_channels(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Channel).where(Channel.owner_id == user_id, Channel.is_active == True)
    )
    channels = result.scalars().all()
    return {"channels": [
        {
            "id": ch.id, "title": ch.title, "username": ch.username,
            "telegram_id": ch.telegram_id, "members_count": ch.members_count,
            "members_formatted": fmt(ch.members_count),
            "has_photo": ch.photo_file_id is not None,
        } for ch in channels
    ]}


@router.get("/channels/{channel_id}/photo")
async def channel_photo(channel_id: int, initData: str, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_query(initData)
    result  = await db.execute(
        select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id)
    )
    channel = result.scalar_one_or_none()
    if not channel or not channel.photo_file_id:
        raise HTTPException(status_code=404)

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={channel.photo_file_id}"
        ) as r:
            data = await r.json()
            if not data.get("ok"):
                raise HTTPException(status_code=404)
            file_path = data["result"]["file_path"]
        async with session.get(
            f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        ) as r:
            content = await r.read()
            ct = r.headers.get("Content-Type", "image/jpeg")

    return Response(content=content, media_type=ct)


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    request: Request,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id)
    )
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404)

    bot = request.app.state.bot
    try:
        await bot.leave_chat(ch.telegram_id)
    except TelegramBadRequest:
        pass
    except Exception as e:
        print(f"leave_chat failed: {e}")

    await db.delete(ch)
    await db.commit()
    return {"status": "success"}

# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates")
async def get_templates(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PostTemplate).where(PostTemplate.owner_id == user_id))
    templates = result.scalars().all()
    return {"templates": [
        {
            "id": t.id, "text": t.text, "media_type": t.media_type,
            "button_text": t.button_text, "button_color": t.button_color,
            "preview": t.text[:80] + ("..." if len(t.text) > 80 else ""),
        } for t in templates
    ]}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PostTemplate).where(PostTemplate.id == template_id, PostTemplate.owner_id == user_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404)
    await db.delete(t)
    await db.commit()
    return {"status": "success"}

# ── Giveaways ─────────────────────────────────────────────────────────────────

@router.post("/giveaways")
async def create_giveaway(
    request_data: GiveawayCreateRequest,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        g = await giveaway_service.create_draft(db, user_id, request_data.model_dump())
        return {"status": "success", "giveaway_id": g.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))