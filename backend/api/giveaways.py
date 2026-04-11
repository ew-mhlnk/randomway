"""backend/api/giveaways.py — updated public endpoint"""
import csv
import io
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from aiogram.types import BufferedInputFile

from api.dependencies import get_user_id
from database import get_db
from schemas import GiveawayPublishSchema, DrawAdditionalRequest
from services.giveaway_service import giveaway_service
from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
from models import User, ChannelEvent, Participant

router = APIRouter(tags=["Giveaways"])


# 1. ПУБЛИЧНЫЙ ЭНДПОИНТ — возвращает mascot_id и end_date для таймера
@router.get("/giveaways/{giveaway_id}/public")
async def get_public_giveaway_info(giveaway_id: int, db: AsyncSession = Depends(get_db)):
    g = await giveaway_repo.get_by_id(db, giveaway_id)
    if not g:
        raise HTTPException(status_code=404, detail="Розыгрыш не найден")
    return {
        "id":          g.id,
        "title":       g.title,
        "status":      g.status,
        "use_captcha": g.use_captcha,
        "use_boosts":  g.use_boosts,
        "use_invites": g.use_invites,
        "mascot_id":   g.mascot_id,
        "end_date":    g.end_date.isoformat() if g.end_date else None,
    }


# 2. ПУБЛИКАЦИЯ
@router.post("/giveaways/publish")
async def publish_giveaway(
    data: GiveawayPublishSchema, request: Request, bg_tasks: BackgroundTasks,
    user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)
):
    bot = request.app.state.bot
    giveaway_id = await giveaway_service.publish_giveaway(
        db=db, bot=bot, user_id=user_id, data=data.model_dump(), bg_tasks=bg_tasks)
    return {"status": "success", "giveaway_id": giveaway_id}


# 3. СПИСОК
@router.get("/giveaways")
async def list_giveaways(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    giveaways = await giveaway_service.get_creator_giveaways(db, user_id)
    return {"giveaways": giveaways}


# 4. СТАТУС
@router.get("/giveaways/{giveaway_id}/status")
async def get_giveaway_status(
    giveaway_id: int, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)
):
    return await giveaway_service.get_giveaway_status(db, giveaway_id)


# 5. АНАЛИТИКА
@router.get("/giveaways/{giveaway_id}/analytics")
async def get_giveaway_analytics(
    giveaway_id: int, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)
):
    g = await giveaway_repo.get_by_id(db, giveaway_id)
    if not g or g.creator_id != user_id:
        raise HTTPException(status_code=404, detail="Не найдено")

    stats = await participant_repo.get_analytics_stats(db, giveaway_id)
    
    # Считаем виральность (сколько людей пришло по реферальным ссылкам)
    viral_joins = await db.scalar(
        select(func.count(Participant.id))
        .where(Participant.giveaway_id == giveaway_id, Participant.referred_by.isnot(None))
    )

    # Собираем данные по дням (для графиков)
    daily_data = {}

    # 1. Участники по дням
    parts_daily = await db.execute(
        select(func.date(Participant.joined_at).label("day"), func.count().label("count"))
        .where(Participant.giveaway_id == giveaway_id)
        .group_by("day")
    )
    for row in parts_daily.fetchall():
        day_str = row.day.isoformat()
        if day_str not in daily_data:
            daily_data[day_str] = {"date": day_str, "participants": 0, "joins": 0, "leaves": 0}
        daily_data[day_str]["participants"] += row.count

    # 2. Подписки/отписки по спонсорским каналам
    if g.sponsor_channel_ids:
        where_clauses = [ChannelEvent.channel_id.in_(g.sponsor_channel_ids)]
        # Если есть start_date, отсекаем старые события, иначе берем всё
        if g.start_date:
            where_clauses.append(ChannelEvent.created_at >= g.start_date)
            
        events_daily = await db.execute(
            select(
                func.date(ChannelEvent.created_at).label("day"),
                ChannelEvent.action,
                func.count().label("count")
            )
            .where(*where_clauses)
            .group_by("day", ChannelEvent.action)
        )
        for row in events_daily.fetchall():
            day_str = row.day.isoformat()
            if day_str not in daily_data:
                daily_data[day_str] = {"date": day_str, "participants": 0, "joins": 0, "leaves": 0}
            if row.action == "join":
                daily_data[day_str]["joins"] += row.count
            elif row.action == "leave":
                daily_data[day_str]["leaves"] += row.count

    # Сортируем дни по порядку
    chart_data = [daily_data[k] for k in sorted(daily_data.keys())]

    return {
        "total_participants": stats["total"],
        "cheaters_caught": stats["cheaters"],
        "total_boosts": stats["boosts"],
        "viral_joins": viral_joins or 0,
        "chart_data": chart_data
    }


# 6. ФИНАЛИЗАЦИЯ
@router.post("/giveaways/{giveaway_id}/finalize")
async def finalize_giveaway_endpoint(
    giveaway_id: int, request: Request, bg_tasks: BackgroundTasks,
    user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)
):
    return await giveaway_service.finalize_giveaway(db, request.app.state.bot, giveaway_id, user_id, bg_tasks)


# 7. ДОВЫБРАТЬ ПОБЕДИТЕЛЕЙ
@router.post("/giveaways/{giveaway_id}/draw-additional")
async def draw_additional_endpoint(
    giveaway_id: int, payload: DrawAdditionalRequest, request: Request,
    user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)
):
    return await giveaway_service.draw_additional_winners(
        db, request.app.state.bot, giveaway_id, payload.count, user_id)


# 8. ЭКСПОРТ CSV
@router.get("/giveaways/{giveaway_id}/export")
async def export_giveaway_csv(
    giveaway_id: int, request: Request,
    user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)
):
    g = await giveaway_repo.get_by_id(db, giveaway_id)
    if not g or g.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Нет прав")

    stmt = (
        select(participant_repo.model, User)
        .join(User, participant_repo.model.user_id == User.telegram_id)
        .where(participant_repo.model.giveaway_id == giveaway_id)
    )
    rows = (await db.execute(stmt)).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Telegram ID","Имя","Username","Дата","Друзья","Бусты","Отписался","Победитель"])

    for participant, user in rows:
        writer.writerow([
            user.telegram_id, user.first_name,
            f"@{user.username}" if user.username else "—",
            participant.joined_at.strftime("%Y-%m-%d %H:%M") if participant.joined_at else "—",
            participant.invite_count,
            getattr(participant, 'boost_count', 0),
            "Да" if not participant.is_active else "Нет",
            "ДА 🏆" if participant.is_winner else "Нет",
        ])

    csv_bytes = output.getvalue().encode('utf-8-sig')
    bot = request.app.state.bot
    try:
        await bot.send_document(
            chat_id=user_id,
            document=BufferedInputFile(csv_bytes, filename=f"giveaway_{giveaway_id}.csv"),
            caption=f"📊 Участники розыгрыша <b>{g.title}</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"CSV send error: {e}")
        raise HTTPException(status_code=400, detail="Бот не смог отправить файл. Напишите /start боту.")

    return {"status": "sent_to_pm"}