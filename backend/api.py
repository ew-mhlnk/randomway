"""backend\api.py"""

from fastapi import APIRouter, HTTPException, Depends, Response, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import urllib.parse
import hashlib
import hmac
import json
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat,
    ChatAdministratorRights,
)

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


# ── Keyboard builders (те же что в handlers/channels.py) ─────────────────────

def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎲 Вернуться в приложение",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])


def _request_chat_kb() -> ReplyKeyboardMarkup:
    channel_rights = ChatAdministratorRights(
        is_anonymous=False, can_manage_chat=True, can_post_messages=True,
        can_edit_messages=True, can_delete_messages=True,
        can_manage_video_chats=False, can_restrict_members=False,
        can_promote_members=False, can_change_info=False, can_invite_users=False,
    )
    group_rights = ChatAdministratorRights(
        is_anonymous=False, can_manage_chat=True, can_delete_messages=True,
        can_manage_video_chats=False, can_restrict_members=True,
        can_promote_members=False, can_change_info=False,
        can_invite_users=True, can_pin_messages=True, can_manage_topics=False,
    )
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📁 Добавить канал",
                request_chat=KeyboardButtonRequestChat(
                    request_id=1, chat_is_channel=True,
                    user_administrator_rights=channel_rights,
                    bot_administrator_rights=channel_rights,
                )
            ),
            KeyboardButton(
                text="💬 Добавить группу",
                request_chat=KeyboardButtonRequestChat(
                    request_id=2, chat_is_channel=False,
                    user_administrator_rights=group_rights,
                    bot_administrator_rights=group_rights,
                )
            ),
        ]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ── Bot Info ──────────────────────────────────────────────────────────────────

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

    tg_id  = user_data.get("id")
    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    db_user = result.scalar_one_or_none()

    if db_user:
        db_user.first_name = user_data.get("first_name", "")
        db_user.username   = user_data.get("username", "")
    else:
        db_user = User(
            telegram_id=tg_id,
            first_name=user_data.get("first_name", ""),
            username=user_data.get("username", ""),
        )
        db.add(db_user)

    await db.commit()
    return {"status": "success", "user": user_data}


# ── Bot triggers: бот шлёт сообщение пользователю, мини-апп закрывается ──────
#
# Это единственный надёжный способ запустить flow из Mini App:
#   1. Mini App вызывает этот endpoint (авторизован через initData)
#   2. Бот шлёт пользователю сообщение с нужной клавиатурой / инструкцией
#   3. Фронтенд вызывает tg.close() — Mini App закрывается
#   4. Пользователь видит сообщение бота уже в чате
#
# Почему НЕ deep link t.me/BOT?start=X:
#   start= срабатывает ТОЛЬКО при первом старте бота.
#   Если бот уже запущен — Telegram просто откроет чат молча, без команды.

@router.post("/bot/request-channel")
async def bot_request_channel(request: Request, user_id: int = Depends(get_user_id)):
    """
    Бот шлёт пользователю инструкцию + кнопки выбора канала/группы.
    Mini App после этого вызывает tg.close().
    """
    bot = request.app.state.bot
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "💬 Пришлите <b>@username</b> канала или перешлите любое сообщение "
                "из канала (в том числе приватного).\n\n"
                "⚠️ Бот должен быть администратором канала с правами на публикацию "
                "и редактирование сообщений.\n\n"
                "Для отмены — /cancel\n\n"
                "🔥 Или нажмите кнопку ниже — Telegram сам откроет список ваших "
                "каналов и автоматически добавит бота с нужными правами 👇"
            ),
            reply_markup=_request_chat_kb(),
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось отправить сообщение: {e}")


@router.post("/bot/request-post")
async def bot_request_post(request: Request, user_id: int = Depends(get_user_id)):
    """
    Бот шлёт пользователю инструкцию по созданию поста.
    Mini App после этого вызывает tg.close().
    """
    bot = request.app.state.bot
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "💬 Отправьте текст вашего поста.\n\n"
                "✨ Можно прислать текст с картинкой или видео.\n"
                "Лимит: <b>4096</b> симв. без медиа, <b>1024</b> симв. с медиа.\n\n"
                "🔥 Поддерживаются кастомные эмодзи!\n\n"
                "Для отмены — /cancel"
            ),
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось отправить сообщение: {e}")


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
        raise HTTPException(status_code=404, detail="Фото не найдено")

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
        raise HTTPException(status_code=404, detail="Канал не найден")

    bot = request.app.state.bot
    try:
        await bot.leave_chat(ch.telegram_id)
    except TelegramBadRequest:
        pass
    except Exception as e:
        print(f"Failed to leave chat: {e}")

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