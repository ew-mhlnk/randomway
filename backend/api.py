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
from models import User, Channel
from services.giveaway_service import giveaway_service

router = APIRouter()
BOT_TOKEN = os.getenv("BOT_TOKEN")


class AuthRequest(BaseModel):
    initData: str


class GiveawayCreateRequest(BaseModel):
    initData: str
    title: str
    type: str
    template_id: str
    winners_count: int


def validate_telegram_data(init_data: str) -> dict | None:
    """Криптографическая проверка подписи Телеграма"""
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


def get_current_user_id(init_data: str) -> int:
    """Достаём ID пользователя из initData (синхронно — crypto не требует async)"""
    user_data = validate_telegram_data(init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return user_data.get("id")


@router.post("/auth")
async def authenticate_user(request: AuthRequest, db: AsyncSession = Depends(get_db)):
    user_data = validate_telegram_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись Telegram")

    tg_id = user_data.get("id")
    first_name = user_data.get("first_name", "")
    username = user_data.get("username", "")

    stmt = select(User).where(User.telegram_id == tg_id)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()

    if db_user:
        db_user.first_name = first_name
        db_user.username = username
    else:
        db_user = User(telegram_id=tg_id, first_name=first_name, username=username)
        db.add(db_user)

    await db.commit()
    return {"status": "success", "user": user_data}


@router.get("/channels")
async def get_channels(initData: str, db: AsyncSession = Depends(get_db)):
    """Возвращает каналы текущего пользователя"""
    user_id = get_current_user_id(initData)

    stmt = select(Channel).where(
        Channel.owner_id == user_id,
        Channel.is_active == True
    )
    result = await db.execute(stmt)
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


@router.post("/giveaways")
async def create_giveaway(request: GiveawayCreateRequest, db: AsyncSession = Depends(get_db)):
    user_id = get_current_user_id(request.initData)

    try:
        new_giveaway = await giveaway_service.create_draft(db, user_id, request.model_dump())
        return {
            "status": "success",
            "message": "Розыгрыш создан",
            "giveaway_id": new_giveaway.id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))