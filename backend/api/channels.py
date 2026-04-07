import logging
import asyncio
import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.dependencies import get_user_id
from database import get_db
from models import Channel

router = APIRouter(tags=["Channels"])

@router.get("/channels")
async def get_channels(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.owner_id == user_id, Channel.is_active == True))
    channels = result.scalars().all()
    def fmt_count(n):
        if not n: return "—"
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000: return f"{n/1_000:.1f}K"
        return str(n)

    return {"channels": [{"id": c.id, "title": c.title, "members_formatted": fmt_count(c.members_count), "has_photo": bool(c.photo_url), "photo_url": c.photo_url} for c in channels]}

@router.post("/channels/prepared-request-chat")
async def prepared_request_chat(request: Request, user_id: int = Depends(get_user_id)):
    """Регистрирует кнопку в Telegram API и отдает ID для Mini App (Bot API 9.6)"""
    bot = request.app.state.bot
    
    # Полный список прав (Telegram требует передавать все ключи)
    rights = {
        "is_anonymous": False,
        "can_manage_chat": True,
        "can_delete_messages": True,
        "can_manage_video_chats": False,
        "can_restrict_members": False,
        "can_promote_members": False,
        "can_change_info": False,
        "can_invite_users": False,
        "can_post_messages": True,
        "can_edit_messages": True,
        "can_pin_messages": False,
        "can_manage_topics": False
    }
    
    url = f"https://api.telegram.org/bot{bot.token}/savePreparedKeyboardButton"
    params = {
        "user_id": user_id,
        "text": "Выбрать канал",  # <--- ВОТ ЭТОГО НЕ ХВАТАЛО! Telegram требует это поле.
        "request_chat": {
            "request_id": 1, 
            "chat_is_channel": True, 
            "user_administrator_rights": rights, 
            "bot_administrator_rights": rights, 
            "bot_is_member": True
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as resp:
            data = await resp.json()
            if data.get("ok"):
                return {"status": "success", "prepared_id": data["result"]["id"]}
            logging.error(f"TG API Error in prepared-request-chat: {data}")
            raise HTTPException(status_code=400, detail="Ошибка генерации кнопки в Telegram API")

@router.post("/channels/{channel_id}/sync")
async def sync_channel(channel_id: int, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    channel = await db.scalar(select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id))
    if not channel: raise HTTPException(status_code=404)
    try:
        chat = await request.app.state.bot.get_chat(channel.telegram_id)
        channel.members_count = await request.app.state.bot.get_chat_member_count(channel.telegram_id)
        channel.title = chat.title
        await db.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Бот больше не админ")
    return {"status": "success"}

@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    channel = await db.scalar(select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id))
    if channel:
        await db.delete(channel)
        await db.commit()
    return {"status": "success"}