from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import urllib.parse
import hashlib
import hmac
import json
import os

# Импорты для работы с базой данных
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models import User

router = APIRouter()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Модель для приема данных от Next.js
class AuthRequest(BaseModel):
    initData: str

class GiveawayCreate(BaseModel):
    initData: str
    title: str
    type: str
    template_id: int
    winners_count: int = 1
    start_date: str | None = None
    end_date: str | None = None

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
# Импортируем наш новый сервис бизнес-логики
from services.giveaway_service import giveaway_service

# Функция-помощник для расшифровки ID юзера из initData
async def get_current_user_id(initData: str) -> int:
    user_data = validate_telegram_data(initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return user_data.get("id")

@router.post("/giveaways")
async def create_giveaway(request: GiveawayCreate, db: AsyncSession = Depends(get_db)):
    user_id = await get_current_user_id(request.initData)
    
    # request.model_dump() превращает данные от фронта в обычный Python-словарь
    new_giveaway = await giveaway_service.create_draft(db, user_id, request.model_dump())
    
    return {"status": "success", "id": new_giveaway.id}

@router.post("/auth")
async def authenticate_user(request: AuthRequest, db: AsyncSession = Depends(get_db)):
    # 1. Проверяем подлинность данных
    user_data = validate_telegram_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Хакерская атака: неверная подпись Telegram")
    
    # 2. Достаем данные юзера
    tg_id = user_data.get("id")
    first_name = user_data.get("first_name", "")
    username = user_data.get("username", "")

    # 3. Ищем юзера в нашей базе данных
    stmt = select(User).where(User.telegram_id == tg_id)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()

    if db_user:
        # Если юзер уже есть в базе, просто обновляем его имя (вдруг изменил)
        db_user.first_name = first_name
        db_user.username = username
    else:
        # Если юзер новый, регистрируем его!
        db_user = User(
            telegram_id=tg_id,
            first_name=first_name,
            username=username
        )
        db.add(db_user)
    
    # 4. Фиксируем изменения (Сохраняем в PostgreSQL)
    await db.commit()
    
    return {"status": "success", "user": user_data}

# --- ДОБАВЛЕНИЯ ДЛЯ СОЗДАНИЯ РОЗЫГРЫША ---
from services.giveaway_service import giveaway_service

# Модель того, что мы ждем от React (Zustand)
class GiveawayCreateRequest(BaseModel):
    initData: str
    title: str
    type: str
    template_id: str
    winners_count: int
    # Позже добавим сюда каналы, даты и бонусы

@router.post("/giveaways")
async def create_giveaway(request: GiveawayCreateRequest, db: AsyncSession = Depends(get_db)):
    # 1. Проверяем криптографию и получаем ID юзера
    user_id = await get_current_user_id(request.initData)
    
    # 2. Превращаем Pydantic модель в обычный словарь
    data = request.model_dump()
    
    # 3. Передаем в наш ООП Сервис
    try:
        new_giveaway = await giveaway_service.create_draft(db, user_id, data)
        return {"status": "success", "message": "Розыгрыш успешно создан!", "giveaway_id": new_giveaway.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))