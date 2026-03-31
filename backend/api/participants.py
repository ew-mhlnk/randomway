from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from aiogram import Bot
from models import Channel, Giveaway
from api.dependencies import get_user_id
from database import get_db
from schemas import JoinGiveawayRequest
from services.participant_service import participant_service
from repositories.participant_repo import participant_repo

router = APIRouter(tags=["Participants"])

@router.post("/giveaways/{giveaway_id}/join")
async def join_giveaway(
    giveaway_id: int,
    request: Request,
    payload: JoinGiveawayRequest,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    bot = request.app.state.bot
    return await participant_service.join_giveaway(
        db=db, 
        bot=bot, 
        giveaway_id=giveaway_id, 
        user_id=user_id, 
        ref_code=payload.ref_code,
        payload=payload.model_dump() # 🚀 ВОТ ОНО! ПЕРЕДАЕМ ТОКЕН КАПЧИ
    )

@router.post("/giveaways/{giveaway_id}/check-boost")
async def check_boost_endpoint(
    giveaway_id: int,
    request: Request,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    bot: Bot = request.app.state.bot
    participant = await participant_repo.get_by_user_and_giveaway(db, user_id, giveaway_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
    
    if participant.has_boosted:
        return {"status": "success", "message": "Буст уже учтен"}
        
    giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
    if not giveaway or not giveaway.sponsor_channel_ids:
        raise HTTPException(status_code=400, detail="Нет каналов для буста")
        
    channels = await db.execute(select(Channel).where(Channel.id.in_(giveaway.sponsor_channel_ids)))
    channels = channels.scalars().all()
    
    has_boost = False
    for ch in channels:
        try:
            # Магия Telegram API: спрашиваем, есть ли бусты от этого юзера
            boosts = await bot.get_user_chat_boosts(chat_id=ch.telegram_id, user_id=user_id)
            if boosts and len(boosts.boosts) > 0:
                has_boost = True
                break
        except Exception as e:
            pass # Если бот не админ или прав не хватает, пропускаем
            
    if has_boost:
        participant.has_boosted = True
        await db.commit()
        return {"status": "success"}
        
    raise HTTPException(status_code=400, detail="Буст не найден. Попробуйте нажать еще раз через пару минут.")

@router.post("/giveaways/{giveaway_id}/story-shared")
async def story_shared_endpoint(
    giveaway_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    participant = await participant_repo.get_by_user_and_giveaway(db, user_id, giveaway_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
        
    if participant.story_clicks == 0:
        participant.story_clicks = 1 # Записываем факт репоста
        await db.commit()
        
    return {"status": "success"}