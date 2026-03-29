import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.dependencies import get_user_id
from database import get_db
from models import Channel
from services.s3_service import upload_tg_avatar_to_s3

router = APIRouter(prefix="/channels", tags=["Channels"])


def _format_members(count: int | None) -> str:
    """Красиво форматирует число подписчиков."""
    if count is None:
        return "—"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def _serialize_channel(ch: Channel) -> dict:
    return {
        "id": ch.id,
        "title": ch.title,
        "username": ch.username,
        "members_count": ch.members_count,
        "members_formatted": _format_members(ch.members_count),
        "has_photo": bool(ch.photo_url),
        "photo_url": ch.photo_url,
        "is_active": ch.is_active,
    }


# ── GET /api/v1/channels ─────────────────────────────────────────────────────
@router.get("")
async def list_channels(
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Список каналов текущего пользователя."""
    result = await db.execute(
        select(Channel)
        .where(Channel.owner_id == user_id, Channel.is_active == True)
        .order_by(Channel.id.desc())
    )
    channels = result.scalars().all()
    return {"channels": [_serialize_channel(ch) for ch in channels]}


# ── POST /api/v1/channels/{id}/sync ──────────────────────────────────────────
@router.post("/{channel_id}/sync")
async def sync_channel(
    channel_id: int,
    request: Request,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Обновить данные канала из Telegram API (название, участники, аватар)."""
    channel = await db.scalar(
        select(Channel).where(
            Channel.id == channel_id,
            Channel.owner_id == user_id,
        )
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")

    bot = request.app.state.bot

    try:
        tg_chat = await asyncio.wait_for(
            bot.get_chat(channel.telegram_id), timeout=8.0
        )
        count = await asyncio.wait_for(
            bot.get_chat_member_count(channel.telegram_id), timeout=5.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503, detail="Telegram не отвечает, попробуйте позже"
        )
    except Exception as e:
        logging.error(f"sync_channel: Telegram API error: {e}")
        raise HTTPException(
            status_code=400, detail="Бот не имеет доступа к каналу"
        )

    # Обновляем поля
    channel.title = tg_chat.title
    channel.username = getattr(tg_chat, "username", None)
    channel.members_count = count
    channel.is_active = True

    new_photo_id = tg_chat.photo.small_file_id if tg_chat.photo else None

    # Если аватар сменился — загружаем в S3 асинхронно (не блокируем ответ)
    if new_photo_id and new_photo_id != channel.photo_file_id:
        channel.photo_file_id = new_photo_id
        asyncio.create_task(_update_photo_bg(channel.telegram_id, new_photo_id))

    await db.commit()
    await db.refresh(channel)
    return {"status": "success", "channel": _serialize_channel(channel)}


# ── DELETE /api/v1/channels/{id} ─────────────────────────────────────────────
@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    request: Request,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Мягкое удаление канала + бот выходит из него."""
    channel = await db.scalar(
        select(Channel).where(
            Channel.id == channel_id,
            Channel.owner_id == user_id,
        )
    )
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")

    # Помечаем как неактивный (soft delete)
    channel.is_active = False
    await db.commit()

    # Пытаемся выгнать бота из канала (не блокируем, если не получится)
    bot = request.app.state.bot
    try:
        await asyncio.wait_for(
            bot.leave_chat(channel.telegram_id), timeout=5.0
        )
    except Exception as e:
        logging.warning(f"delete_channel: bot couldn't leave {channel.telegram_id}: {e}")

    return {"status": "success"}


# ── Вспомогательная: фоновое обновление фото ─────────────────────────────────
async def _update_photo_bg(telegram_id: int, photo_file_id: str) -> None:
    """Загружает новый аватар в S3 и обновляет запись в БД."""
    from database import AsyncSessionLocal

    try:
        photo_url = await upload_tg_avatar_to_s3(photo_file_id, telegram_id)
        if not photo_url:
            return
        async with AsyncSessionLocal() as db:
            channel = await db.scalar(
                select(Channel).where(Channel.telegram_id == telegram_id)
            )
            if channel:
                channel.photo_url = photo_url
                await db.commit()
    except Exception as e:
        logging.error(f"_update_photo_bg failed for {telegram_id}: {e}")