"""backend/api/channels.py"""
import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from api.dependencies import get_user_id
from database import get_db
from models import Channel
from services.s3_service import upload_tg_avatar_to_s3

router = APIRouter(tags=["Channels"])


class AddByIdRequest(BaseModel):
    chat_id: int


async def _save_channel_by_id(chat_id: int, owner_id: int, bot, db: AsyncSession) -> dict:
    """Сохраняет канал в БД по telegram_id. Используется для WebApp.requestChat."""
    try:
        chat = await bot.get_chat(chat_id)
        count = await bot.get_chat_member_count(chat_id)
    except Exception as e:
        logging.error(f"get_chat error for {chat_id}: {e}")
        raise HTTPException(status_code=400, detail="Бот не имеет доступа к этому каналу. Убедитесь, что бот добавлен как администратор.")

    # Проверяем, что бот является администратором
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)
        if member.status != "administrator":
            raise HTTPException(status_code=400, detail="Бот ещё не администратор в этом канале. Добавьте бота как админа и попробуйте снова.")
    except HTTPException:
        raise
    except Exception as e:
        logging.warning(f"check admin error for {chat_id}: {e}")

    photo_id = chat.photo.small_file_id if chat.photo else None

    existing = await db.scalar(select(Channel).where(Channel.telegram_id == chat.id))
    if existing:
        existing.title = chat.title
        existing.username = getattr(chat, "username", None)
        existing.members_count = count
        existing.photo_file_id = photo_id
        existing.is_active = True
        existing.owner_id = owner_id
        await db.commit()
        is_new = False
    else:
        db.add(Channel(
            telegram_id=chat.id,
            owner_id=owner_id,
            title=chat.title,
            username=getattr(chat, "username", None),
            members_count=count,
            photo_file_id=photo_id,
        ))
        await db.commit()
        is_new = True

    # Загружаем фото в фоне
    if photo_id:
        asyncio.create_task(_update_photo_bg(chat.id, photo_id))

    return {"is_new": is_new, "title": chat.title, "count": count}


async def _update_photo_bg(channel_telegram_id: int, photo_id: str) -> None:
    from database import AsyncSessionLocal
    try:
        photo_url = await upload_tg_avatar_to_s3(photo_id, channel_telegram_id)
        if not photo_url:
            return
        async with AsyncSessionLocal() as db:
            channel = await db.scalar(select(Channel).where(Channel.telegram_id == channel_telegram_id))
            if channel:
                channel.photo_url = photo_url
                await db.commit()
    except Exception as e:
        logging.error(f"Background photo update failed for {channel_telegram_id}: {e}")


@router.get("/channels")
async def get_channels(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.owner_id == user_id, Channel.is_active == True))
    channels = result.scalars().all()

    def fmt_count(n):
        if n is None:
            return "—"
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)

    return {
        "channels": [
            {
                "id": ch.id,
                "title": ch.title,
                "username": ch.username,
                "members_formatted": fmt_count(ch.members_count),
                "has_photo": bool(ch.photo_url),
                "photo_url": ch.photo_url,
            }
            for ch in channels
        ]
    }


@router.post("/channels/add-by-id")
async def add_channel_by_id(
    payload: AddByIdRequest,
    request: Request,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Добавляет канал по telegram_id — вызывается после WebApp.requestChat (Bot API 9.6).
    Фронтенд получает chat_id из колбека requestChat и передаёт сюда.
    """
    bot = request.app.state.bot
    result = await _save_channel_by_id(payload.chat_id, user_id, bot, db)
    return {"status": "success", **result}


@router.post("/channels/{channel_id}/sync")
async def sync_channel(
    channel_id: int,
    request: Request,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    channel = await db.scalar(select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id))
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")

    bot = request.app.state.bot
    try:
        count = await bot.get_chat_member_count(channel.telegram_id)
        chat = await bot.get_chat(channel.telegram_id)
        channel.members_count = count
        channel.title = chat.title
        channel.username = getattr(chat, "username", None)
        channel.is_active = True
        await db.commit()
    except Exception as e:
        logging.error(f"sync_channel error: {e}")
        raise HTTPException(status_code=400, detail="Бот больше не администратор в этом канале")

    return {"status": "success"}


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    request: Request,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    channel = await db.scalar(select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id))
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")

    bot = request.app.state.bot
    try:
        await bot.leave_chat(channel.telegram_id)
    except Exception as e:
        logging.warning(f"leave_chat error (non-critical): {e}")

    await db.delete(channel)
    await db.commit()
    return {"status": "success"}