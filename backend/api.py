from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import urllib.parse
import hashlib
import hmac
import json
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models import User, Channel, PostTemplate
from services.giveaway_service import giveaway_service

router = APIRouter()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")  # добавь BOT_USERNAME в .env


# ─── Утилиты ────────────────────────────────────────────────────────────────

def validate_telegram_data(init_data: str) -> dict | None:
    """Криптографическая проверка подписи Telegram"""
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


def get_user_id(init_data: str) -> int:
    """Достать user_id из initData или бросить 401"""
    user_data = validate_telegram_data(init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return user_data["id"]


# ─── Модели запросов ─────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    initData: str


class GiveawayCreateRequest(BaseModel):
    initData: str
    title: str
    type: str
    template_id: str
    winners_count: int


# ─── Auth ────────────────────────────────────────────────────────────────────

@router.post("/auth")
async def authenticate_user(request: AuthRequest, db: AsyncSession = Depends(get_db)):
    user_data = validate_telegram_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись Telegram")

    tg_id = user_data.get("id")
    first_name = user_data.get("first_name", "")
    username = user_data.get("username", "")

    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    db_user = result.scalar_one_or_none()

    if db_user:
        db_user.first_name = first_name
        db_user.username = username
    else:
        db_user = User(telegram_id=tg_id, first_name=first_name, username=username)
        db.add(db_user)

    await db.commit()
    return {"status": "success", "user": user_data}


# ─── Channels ────────────────────────────────────────────────────────────────

@router.get("/channels")
async def get_channels(initData: str, db: AsyncSession = Depends(get_db)):
    """Список каналов текущего пользователя"""
    user_id = get_user_id(initData)

    result = await db.execute(
        select(Channel).where(Channel.owner_id == user_id, Channel.is_active == True)
    )
    channels = result.scalars().all()

    return {
        "channels": [
            {
                "id": ch.id,
                "title": ch.title,
                "username": ch.username,
                "telegram_id": ch.telegram_id,
            }
            for ch in channels
        ]
    }


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, initData: str, db: AsyncSession = Depends(get_db)):
    """Удалить канал (мягкое удаление — is_active=False)"""
    user_id = get_user_id(initData)

    result = await db.execute(
        select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")

    # Мягкое удаление — канал остаётся в БД для истории розыгрышей
    channel.is_active = False
    await db.commit()

    return {"status": "success"}


@router.get("/channels/add-link")
async def get_add_channel_link(initData: str):
    """Возвращает ссылку для добавления бота в канал как админа"""
    get_user_id(initData)  # только проверка авторизации

    if not BOT_USERNAME:
        raise HTTPException(status_code=500, detail="BOT_USERNAME не задан в .env")

    link = f"https://t.me/{BOT_USERNAME}?startchannel=true&admin=post_messages+edit_messages"
    return {"link": link}


# ─── Templates (Посты) ───────────────────────────────────────────────────────

@router.get("/templates")
async def get_templates(initData: str, db: AsyncSession = Depends(get_db)):
    """Список шаблонов постов текущего пользователя"""
    user_id = get_user_id(initData)

    result = await db.execute(
        select(PostTemplate).where(PostTemplate.owner_id == user_id)
    )
    templates = result.scalars().all()

    return {
        "templates": [
            {
                "id": t.id,
                "text": t.text,
                "media_type": t.media_type,
                "button_text": t.button_text,
                "button_color": t.button_color,
                # Превью текста — первые 80 символов
                "preview": t.text[:80] + ("..." if len(t.text) > 80 else ""),
            }
            for t in templates
        ]
    }


@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, initData: str, db: AsyncSession = Depends(get_db)):
    """Удалить шаблон поста"""
    user_id = get_user_id(initData)

    result = await db.execute(
        select(PostTemplate).where(
            PostTemplate.id == template_id,
            PostTemplate.owner_id == user_id,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    await db.delete(template)
    await db.commit()

    return {"status": "success"}


@router.get("/templates/{template_id}")
async def get_template(template_id: int, initData: str, db: AsyncSession = Depends(get_db)):
    """Получить один шаблон по ID (для превью при создании розыгрыша)"""
    user_id = get_user_id(initData)

    result = await db.execute(
        select(PostTemplate).where(
            PostTemplate.id == template_id,
            PostTemplate.owner_id == user_id,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    return {
        "id": template.id,
        "text": template.text,
        "media_id": template.media_id,
        "media_type": template.media_type,
        "button_text": template.button_text,
        "button_color": template.button_color,
    }


# ─── Giveaways ───────────────────────────────────────────────────────────────

@router.post("/giveaways")
async def create_giveaway(request: GiveawayCreateRequest, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(request.initData)

    try:
        new_giveaway = await giveaway_service.create_draft(db, user_id, request.model_dump())
        return {
            "status": "success",
            "giveaway_id": new_giveaway.id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/giveaways")
async def get_giveaways(initData: str, db: AsyncSession = Depends(get_db)):
    """Список розыгрышей текущего пользователя"""
    from models import Giveaway
    user_id = get_user_id(initData)

    result = await db.execute(
        select(Giveaway).where(Giveaway.creator_id == user_id)
    )
    giveaways = result.scalars().all()

    return {
        "giveaways": [
            {
                "id": g.id,
                "title": g.title,
                "type": g.giveaway_type,
                "winners_count": g.winners_count,
                "is_active": g.is_active,
                "start_date": g.start_date.isoformat() if g.start_date else None,
                "end_date": g.end_date.isoformat() if g.end_date else None,
            }
            for g in giveaways
        ]
    }