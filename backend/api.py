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

from database import get_db
from models import User, Channel, PostTemplate
from services.giveaway_service import giveaway_service

router = APIRouter()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Настраиваем схему авторизации (Bearer Token)
security = HTTPBearer()


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


# ── Dependencies (Инъекции зависимостей) ──────────────────────────────────────

def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Извлекает ID пользователя из заголовка Authorization: Bearer <initData>"""
    init_data = credentials.credentials
    user_data = validate_telegram_data(init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись Telegram")
    return user_data["id"]

def get_user_id_from_query(initData: str) -> int:
    """Отдельно для тега <img>, так как браузер не умеет передавать заголовки в картинках"""
    user_data = validate_telegram_data(initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return user_data["id"]

def fmt(count: int | None) -> str:
    """Форматирует числа (1.5K, 2M)"""
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


# ── Bot Info ──────────────────────────────────────────────────────────────────

@router.get("/bot-info")
async def bot_info(user_id: int = Depends(get_user_id)):
    """Отдает фронтенду юзернейм бота, чтобы фронт мог генерировать ссылки t.me/BOTNAME"""
    username = os.environ.get("BOT_USERNAME", "")
    if not username:
        raise HTTPException(status_code=500, detail="BOT_USERNAME не инициализирован")
    return {"username": username}


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/auth")
async def authenticate_user(request: AuthRequest, db: AsyncSession = Depends(get_db)):
    """Регистрирует или обновляет данные пользователя в БД при входе в Mini App"""
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
        db_user = User(
            telegram_id=tg_id, 
            first_name=user_data.get("first_name",""), 
            username=user_data.get("username","")
        )
        db.add(db_user)
        
    await db.commit()
    return {"status": "success", "user": user_data}


# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/channels")
async def get_channels(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    """Возвращает список каналов пользователя"""
    result = await db.execute(
        select(Channel).where(Channel.owner_id == user_id, Channel.is_active == True)
    )
    channels = result.scalars().all()
    
    return {"channels":[
        {
            "id": ch.id, "title": ch.title, "username": ch.username,
            "telegram_id": ch.telegram_id, "members_count": ch.members_count,
            "members_formatted": fmt(ch.members_count),
            "has_photo": ch.photo_file_id is not None,
        } for ch in channels
    ]}


@router.get("/channels/{channel_id}/photo")
async def channel_photo(channel_id: int, initData: str, db: AsyncSession = Depends(get_db)):
    """Проксирует аватарку канала из Telegram API"""
    user_id = get_user_id_from_query(initData)
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id)
    )
    channel = result.scalar_one_or_none()
    if not channel or not channel.photo_file_id:
        raise HTTPException(status_code=404, detail="Фото не найдено")

    import aiohttp
    async with aiohttp.ClientSession() as session:
        # Получаем file_path по file_id
        async with session.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={channel.photo_file_id}"
        ) as r:
            data = await r.json()
            if not data.get("ok"):
                raise HTTPException(status_code=404)
            file_path = data["result"]["file_path"]
            
        # Скачиваем саму картинку
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
    db: AsyncSession = Depends(get_db)
):
    """Удаляет канал из БД и заставляет бота выйти из него"""
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id)
    )
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail="Канал не найден")
    
    bot = request.app.state.bot
    try:
        # Просим бота выйти из канала
        await bot.leave_chat(ch.telegram_id)
    except TelegramBadRequest:
        pass # Бот уже был кикнут из чата вручную
    except Exception as e:
        print(f"Failed to leave chat: {e}")

    await db.delete(ch)
    await db.commit()
    return {"status": "success"}


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates")
async def get_templates(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    """Возвращает шаблоны постов пользователя"""
    result = await db.execute(select(PostTemplate).where(PostTemplate.owner_id == user_id))
    templates = result.scalars().all()
    
    return {"templates":[
        {
            "id": t.id, "text": t.text, "media_type": t.media_type,
            "button_text": t.button_text, "button_color": t.button_color,
            "preview": t.text[:80] + ("..." if len(t.text) > 80 else ""),
        } for t in templates
    ]}


@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    """Удаляет шаблон поста"""
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
    db: AsyncSession = Depends(get_db)
):
    """Создает черновик розыгрыша"""
    try:
        g = await giveaway_service.create_draft(db, user_id, request_data.model_dump())
        return {"status": "success", "giveaway_id": g.id}
    except Exception as e: 
        raise HTTPException(status_code=400, detail=str(e))