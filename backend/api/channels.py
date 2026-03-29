import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api.dependencies import get_user_id
from database import get_db
from models import Channel
from services.s3_service import upload_tg_avatar_to_s3

# 🚀 ДОЛЖНО БЫТЬ ИМЕННО ТАК (APIRouter от FastAPI)
router = APIRouter(tags=["Channels"])

def fmt(count: int | None) -> str:
    if count is None: return "—"
    if count >= 1_000_000: return f"{count/1_000_000:.1f}M"
    if count >= 1_000: return f"{count/1_000:.1f}K"
    return str(count)

@router.get("/channels")
async def get_channels(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.owner_id == user_id, Channel.is_active == True))
    channels = result.scalars().all()
    return {"channels":[{"id": ch.id, "title": ch.title, "username": ch.username, "telegram_id": ch.telegram_id, "members_count": ch.members_count, "members_formatted": fmt(ch.members_count), "has_photo": ch.photo_url is not None, "photo_url": ch.photo_url} for ch in channels]}

@router.post("/channels/{channel_id}/sync")
async def sync_channel(channel_id: int, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    bot = request.app.state.bot
    ch = await db.scalar(select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id))
    if not ch: raise HTTPException(status_code=404)
    try:
        chat = await bot.get_chat(ch.telegram_id)
        count = await bot.get_chat_member_count(ch.telegram_id)
        photo_id = chat.photo.small_file_id if chat.photo else None
        if photo_id and photo_id != ch.photo_file_id:
            new_url = await upload_tg_avatar_to_s3(photo_id, chat.id)
            if new_url: ch.photo_url = new_url
        ch.title, ch.members_count, ch.photo_file_id = chat.title, count, photo_id
        await db.commit()
    except Exception as e:
        logging.error(f"Sync error for channel {channel_id}: {e}")
        raise HTTPException(status_code=400, detail="Бот больше не администратор в этом канале")
    return {"status": "success"}

@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    ch = await db.scalar(select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id))
    if not ch: raise HTTPException(status_code=404)
    try: await request.app.state.bot.leave_chat(ch.telegram_id)
    except: pass
    await db.delete(ch)
    await db.commit()
    return {"status": "success"}