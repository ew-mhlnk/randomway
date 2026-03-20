from fastapi import APIRouter, HTTPException, Depends, Response
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


def get_user_id(init_data: str) -> int:
    user_data = validate_telegram_data(init_data)
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
    initData: str
    title: str
    type: str
    template_id: str
    winners_count: int


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/auth")
async def authenticate_user(request: AuthRequest, db: AsyncSession = Depends(get_db)):
    user_data = validate_telegram_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись Telegram")
    tg_id = user_data.get("id")
    result = await db.execute(select(User).where(User.telegram_id == tg_id))
    db_user = result.scalar_one_or_none()
    if db_user:
        db_user.first_name = user_data.get("first_name", "")
        db_user.username = user_data.get("username", "")
    else:
        db_user = User(telegram_id=tg_id, first_name=user_data.get("first_name",""), username=user_data.get("username",""))
        db.add(db_user)
    await db.commit()
    return {"status": "success", "user": user_data}


# ── Bot info — фронт получает username бота для deep link ────────────────────

@router.get("/bot-info")
async def bot_info(initData: str):
    """
    Возвращает username бота.
    Фронт использует его для ссылок: t.me/BOT?start=add_channel
    Username кешируется в os.environ при старте (см. main.py lifespan).
    """
    get_user_id(initData)  # только проверка авторизации
    username = os.environ.get("BOT_USERNAME", "")
    if not username:
        raise HTTPException(status_code=500, detail="BOT_USERNAME не инициализирован")
    return {"username": username}


# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/channels")
async def get_channels(initData: str, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(initData)
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
    user_id = get_user_id(initData)
    result = await db.execute(
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
async def delete_channel(channel_id: int, initData: str, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(initData)
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id)
    )
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="Канал не найден")
    ch.is_active = False
    await db.commit()
    return {"status": "success"}


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates")
async def get_templates(initData: str, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(initData)
    result = await db.execute(select(PostTemplate).where(PostTemplate.owner_id == user_id))
    templates = result.scalars().all()
    return {"templates": [
        {
            "id": t.id, "text": t.text, "media_type": t.media_type,
            "button_text": t.button_text, "button_color": t.button_color,
            "preview": t.text[:80] + ("..." if len(t.text) > 80 else ""),
        } for t in templates
    ]}


@router.get("/templates/{template_id}")
async def get_template(template_id: int, initData: str, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(initData)
    result = await db.execute(
        select(PostTemplate).where(PostTemplate.id == template_id, PostTemplate.owner_id == user_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404)
    return {"id": t.id, "text": t.text, "media_id": t.media_id,
            "media_type": t.media_type, "button_text": t.button_text, "button_color": t.button_color}


@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, initData: str, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(initData)
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
async def create_giveaway(request: GiveawayCreateRequest, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(request.initData)
    try:
        g = await giveaway_service.create_draft(db, user_id, request.model_dump())
        return {"status": "success", "giveaway_id": g.id}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))


@router.get("/giveaways")
async def get_giveaways(initData: str, db: AsyncSession = Depends(get_db)):
    from models import Giveaway
    user_id = get_user_id(initData)
    result = await db.execute(select(Giveaway).where(Giveaway.creator_id == user_id))
    giveaways = result.scalars().all()
    return {"giveaways": [
        {"id": g.id, "title": g.title, "type": g.giveaway_type,
         "winners_count": g.winners_count, "is_active": g.is_active,
         "start_date": g.start_date.isoformat() if g.start_date else None,
         "end_date": g.end_date.isoformat() if g.end_date else None}
        for g in giveaways
    ]}