import logging
from aiogram import Router
from aiogram.types import ChatMemberUpdated
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from database import AsyncSessionLocal
from models import ChannelEvent

router = Router()

# Ловим ПОДПИСКУ на канал
@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated):
    async with AsyncSessionLocal() as db:
        db.add(ChannelEvent(
            channel_id=event.chat.id,
            user_id=event.new_chat_member.user.id,
            action="join"
        ))
        await db.commit()

# Ловим ОТПИСКУ от канала
@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: ChatMemberUpdated):
    async with AsyncSessionLocal() as db:
        db.add(ChannelEvent(
            channel_id=event.chat.id,
            user_id=event.new_chat_member.user.id,
            action="leave"
        ))
        await db.commit()