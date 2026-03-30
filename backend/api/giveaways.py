from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_user_id
from database import get_db
from schemas import GiveawayPublishSchema, DrawAdditionalRequest
from services.giveaway_service import giveaway_service
from repositories.participant_repo import participant_repo
from repositories.giveaway_repo import giveaway_repo

router = APIRouter(tags=["Giveaways"])

@router.post("/giveaways/publish")
async def publish_giveaway(
    data: GiveawayPublishSchema, 
    request: Request,
    bg_tasks: BackgroundTasks,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    bot = request.app.state.bot
    giveaway_id = await giveaway_service.publish_giveaway(
        db=db, bot=bot, user_id=user_id, data=data.model_dump(), bg_tasks=bg_tasks
    )
    return {"status": "success", "giveaway_id": giveaway_id}

# 🚀 НОВЫЙ ЭНДПОИНТ: Список розыгрышей
@router.get("/giveaways")
async def list_giveaways(
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    giveaways = await giveaway_service.get_creator_giveaways(db, user_id)
    return {"giveaways": giveaways}

# 🚀 ЗАПУСК ПОДВЕДЕНИЯ ИТОГОВ
@router.post("/giveaways/{giveaway_id}/finalize")
async def finalize_giveaway_endpoint(
    giveaway_id: int,
    request: Request,
    bg_tasks: BackgroundTasks,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    bot = request.app.state.bot
    return await giveaway_service.finalize_giveaway(db, bot, giveaway_id, user_id, bg_tasks)

# 🚀 ПРОВЕРКА СТАТУСА (ДЛЯ ПОЛЛИНГА)
@router.get("/giveaways/{giveaway_id}/status")
async def get_giveaway_status(
    giveaway_id: int,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    return await giveaway_service.get_giveaway_status(db, giveaway_id)

# 🚀 НОВЫЕ ЭНДПОИНТЫ (Аналитика и Дополнительные победители)

@router.get("/giveaways/{giveaway_id}/analytics")
async def get_giveaway_analytics(
    giveaway_id: int, 
    user_id: int = Depends(get_user_id), 
    db: AsyncSession = Depends(get_db)
):
    """Эндпоинт для отображения статистики в админке розыгрыша"""
    giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
    if not giveaway or giveaway.creator_id != user_id:
        raise HTTPException(status_code=404, detail="Розыгрыш не найден")

    total_participants = await participant_repo.count_by_giveaway(db, giveaway_id)
    
    # Пока отдаем базовую аналитику
    return {
        "total_participants": total_participants,
        "cheaters_caught": 0, 
        "total_boosts": 0     
    }

@router.post("/giveaways/{giveaway_id}/draw-additional")
async def draw_additional_endpoint(
    giveaway_id: int, 
    payload: DrawAdditionalRequest,
    request: Request,
    user_id: int = Depends(get_user_id), 
    db: AsyncSession = Depends(get_db)
):
    """Выбрать N дополнительных победителей"""
    bot = request.app.state.bot
    return await giveaway_service.draw_additional_winners(db, bot, giveaway_id, payload.count, user_id)