import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update

from database import get_db
from models import User, Giveaway, Channel, Participant

router = APIRouter(prefix="/admin", tags=["Admin"])

ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "supersecret")
ADMIN_TOKEN = os.getenv("ADMIN_SECRET_TOKEN", "my-secure-dashboard-token-2026")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/login")

class SetWinnersRequest(BaseModel):
    winner_ids: List[int]

@router.post("/login")
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == ADMIN_USER and form_data.password == ADMIN_PASS:
        return {"access_token": ADMIN_TOKEN, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Неверный логин или пароль")

def verify_admin_token(token: str = Depends(oauth2_scheme)):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return True

@router.get("/stats")
async def get_global_stats(is_admin: bool = Depends(verify_admin_token), db: AsyncSession = Depends(get_db)):
    """Глобальная статистика и ВСЕ розыгрыши"""
    users_count = await db.scalar(select(func.count(User.telegram_id)))
    giveaways_count = await db.scalar(select(func.count(Giveaway.id)))
    active_gw = await db.scalar(select(func.count(Giveaway.id)).where(Giveaway.status == "active"))
    
    all_gw = await db.scalars(select(Giveaway).order_by(Giveaway.id.desc()))
    
    return {
        "total_users": users_count or 0,
        "total_giveaways": giveaways_count or 0,
        "active_giveaways": active_gw or 0,
        "giveaways":[{"id": g.id, "title": g.title, "status": g.status, "winners": g.winners_count} for g in all_gw]
    }

@router.get("/giveaways/{giveaway_id}")
async def get_giveaway_details(giveaway_id: int, is_admin: bool = Depends(verify_admin_token), db: AsyncSession = Depends(get_db)):
    """Детальная информация о розыгрыше и всех его участниках"""
    giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
    if not giveaway:
        raise HTTPException(status_code=404, detail="Розыгрыш не найден")
        
    stmt = (
        select(Participant, User)
        .join(User, Participant.user_id == User.telegram_id)
        .where(Participant.giveaway_id == giveaway_id)
    )
    res = await db.execute(stmt)
    participants = res.all()
    
    parts_data =[]
    for p, u in participants:
        parts_data.append({
            "user_id": u.telegram_id,
            "first_name": u.first_name,
            "username": u.username,
            "invite_count": p.invite_count,
            "has_boosted": p.has_boosted,
            "story_clicks": p.story_clicks,
            "is_active": p.is_active,
            "is_winner": p.is_winner
        })
        
    return {
        "info": {
            "id": giveaway.id,
            "title": giveaway.title,
            "status": giveaway.status,
            "winners_count": giveaway.winners_count,
            "use_boosts": giveaway.use_boosts,
            "use_invites": giveaway.use_invites,
            "use_stories": giveaway.use_stories,
            "use_captcha": giveaway.use_captcha
        },
        "participants": parts_data
    }

@router.post("/giveaways/{giveaway_id}/set-winners")
async def manual_set_winners(giveaway_id: int, payload: SetWinnersRequest, is_admin: bool = Depends(verify_admin_token), db: AsyncSession = Depends(get_db)):
    """Принудительное (ручное) назначение победителей суперадмином"""
    giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
    if not giveaway:
        raise HTTPException(status_code=404, detail="Розыгрыш не найден")
        
    # 1. Сбрасываем старых победителей (обнуляем всем)
    await db.execute(update(Participant).where(Participant.giveaway_id == giveaway_id).values(is_winner=False))
    
    # 2. Назначаем новых победителей
    if payload.winner_ids:
        await db.execute(
            update(Participant)
            .where(Participant.giveaway_id == giveaway_id, Participant.user_id.in_(payload.winner_ids))
            .values(is_winner=True)
        )
        
    # 3. Закрываем розыгрыш (если он еще висел активным)
    if giveaway.status in ["active", "pending", "draft", "finalizing"]:
        giveaway.status = "completed"
        
    await db.commit()
    return {"status": "success"}