import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from database import get_db
from models import User, Giveaway, Channel

router = APIRouter(prefix="/admin", tags=["Admin"])

# Данные из .env
ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "secret")
ADMIN_TOKEN = os.getenv("ADMIN_SECRET_TOKEN", "fallback-token-123")

# Говорим FastAPI, где находится эндпоинт для получения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/login")

@router.post("/login")
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Стандартный Web-логин (выдает токен)"""
    if form_data.username == ADMIN_USER and form_data.password == ADMIN_PASS:
        return {"access_token": ADMIN_TOKEN, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Неверный логин или пароль")

def verify_admin_token(token: str = Depends(oauth2_scheme)):
    """Защита эндпоинтов: пускаем только с правильным токеном"""
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return True

@router.get("/stats")
async def get_global_stats(is_admin: bool = Depends(verify_admin_token), db: AsyncSession = Depends(get_db)):
    """Статистика для Дашборда"""
    users_count = await db.scalar(select(func.count(User.telegram_id)))
    giveaways_count = await db.scalar(select(func.count(Giveaway.id)))
    active_gw = await db.scalar(select(func.count(Giveaway.id)).where(Giveaway.status == "active"))
    
    recent_gw = await db.scalars(select(Giveaway).order_by(Giveaway.id.desc()).limit(5))
    
    return {
        "total_users": users_count or 0,
        "total_giveaways": giveaways_count or 0,
        "active_giveaways": active_gw or 0,
        "recent_giveaways": [{"id": g.id, "title": g.title, "status": g.status} for g in recent_gw]
    }