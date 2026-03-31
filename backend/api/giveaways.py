from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_user_id
from database import get_db
from schemas import GiveawayPublishSchema, DrawAdditionalRequest
from services.giveaway_service import giveaway_service
from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo

router = APIRouter(tags=["Giveaways"])

# 1. ПУБЛИЧНЫЙ ЭНДПОИНТ (Без авторизации, чтобы узнать про капчу)
@router.get("/giveaways/{giveaway_id}/public")
async def get_public_giveaway_info(giveaway_id: int, db: AsyncSession = Depends(get_db)):
    # Используем get_by_id вместо get_active_by_id для надежности
    giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
    if not giveaway:
        raise HTTPException(status_code=404, detail="Розыгрыш не найден")
    return {
        "id": giveaway.id,
        "title": giveaway.title,
        "use_captcha": giveaway.use_captcha,
        "use_boosts": giveaway.use_boosts,
        "use_invites": giveaway.use_invites,
        "use_stories": giveaway.use_stories
    }

# 2. ПУБЛИКАЦИЯ РОЗЫГРЫША
@router.post("/giveaways/publish")
async def publish_giveaway(data: GiveawayPublishSchema, request: Request, bg_tasks: BackgroundTasks, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    bot = request.app.state.bot
    giveaway_id = await giveaway_service.publish_giveaway(db=db, bot=bot, user_id=user_id, data=data.model_dump(), bg_tasks=bg_tasks)
    return {"status": "success", "giveaway_id": giveaway_id}

# 3. СПИСОК МОИХ РОЗЫГРЫШЕЙ
@router.get("/giveaways")
async def list_giveaways(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    giveaways = await giveaway_service.get_creator_giveaways(db, user_id)
    return {"giveaways": giveaways}

# 4. СТАТУС РОЗЫГРЫША
@router.get("/giveaways/{giveaway_id}/status")
async def get_giveaway_status(giveaway_id: int, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    return await giveaway_service.get_giveaway_status(db, giveaway_id)

# 5. АНАЛИТИКА РОЗЫГРЫША
@router.get("/giveaways/{giveaway_id}/analytics")
async def get_giveaway_analytics(giveaway_id: int, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
    if not giveaway or giveaway.creator_id != user_id:
        raise HTTPException(status_code=404, detail="Розыгрыш не найден")
    stats = await participant_repo.get_analytics_stats(db, giveaway_id)
    return {"total_participants": stats["total"], "cheaters_caught": stats["cheaters"], "total_boosts": stats["boosts"]}

# 6. ФИНАЛИЗАЦИЯ (ДОСРОЧНО)
@router.post("/giveaways/{giveaway_id}/finalize")
async def finalize_giveaway_endpoint(giveaway_id: int, request: Request, bg_tasks: BackgroundTasks, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    bot = request.app.state.bot
    return await giveaway_service.finalize_giveaway(db, bot, giveaway_id, user_id, bg_tasks)

# 7. ВЫБОР ДОП. ПОБЕДИТЕЛЕЙ (REROLL)
@router.post("/giveaways/{giveaway_id}/draw-additional")
async def draw_additional_endpoint(giveaway_id: int, payload: DrawAdditionalRequest, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    bot = request.app.state.bot
    return await giveaway_service.draw_additional_winners(db, bot, giveaway_id, payload.count, user_id)