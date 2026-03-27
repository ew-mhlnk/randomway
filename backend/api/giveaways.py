from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_user_id
from database import get_db
from schemas import GiveawayPublishSchema
from services.giveaway_service import giveaway_service

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