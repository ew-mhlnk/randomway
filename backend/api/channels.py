import logging
import os
import asyncio

from aiogram import Router, Bot, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat,
    ChatAdministratorRights, ReplyKeyboardRemove
)
# 🚀 ДОБАВИЛИ StateFilter
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import Channel
from services.s3_service import upload_tg_avatar_to_s3

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")

class ChannelStates(StatesGroup):
    waiting_for_channel = State()

def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])

def _request_chat_kb() -> ReplyKeyboardMarkup:
    rights = ChatAdministratorRights(
        is_anonymous=False, can_manage_chat=True, can_post_messages=True,
        can_edit_messages=True, can_delete_messages=True, can_manage_video_chats=False,
        can_restrict_members=False, can_promote_members=False, can_change_info=False,
        can_invite_users=False, can_post_stories=False, can_edit_stories=False, can_delete_stories=False
    )
    group_rights = ChatAdministratorRights(
        is_anonymous=False, can_manage_chat=True, can_delete_messages=True,
        can_restrict_members=True, can_invite_users=True, can_pin_messages=True,
        can_manage_video_chats=False, can_promote_members=False, can_change_info=False,
        can_post_stories=False, can_edit_stories=False, can_delete_stories=False
    )
    return ReplyKeyboardMarkup(keyboard=[[
        KeyboardButton(text="📁 Добавить канал", request_chat=KeyboardButtonRequestChat(request_id=1, chat_is_channel=True, user_administrator_rights=rights, bot_administrator_rights=rights)),
        KeyboardButton(text="💬 Добавить группу", request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=False, user_administrator_rights=group_rights, bot_administrator_rights=group_rights))
    ]], resize_keyboard=True, is_persistent=True)

async def _save_chat(chat_id: int, owner_id: int, bot: Bot) -> tuple[bool, str, int]:
    chat = await asyncio.wait_for(bot.get_chat(chat_id), timeout=5.0)
    count = await asyncio.wait_for(bot.get_chat_member_count(chat_id), timeout=5.0)
    photo_id = chat.photo.small_file_id if chat.photo else None
    
    photo_url = None
    if photo_id:
        photo_url = await upload_tg_avatar_to_s3(photo_id, chat.id)
        
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Channel).where(Channel.telegram_id == chat.id))
        if existing:
            existing.title = chat.title
            existing.username = getattr(chat, "username", None)
            existing.members_count = count
            existing.photo_file_id = photo_id
            if photo_url: existing.photo_url = photo_url
            existing.is_active = True
            existing.owner_id = owner_id
            await db.commit()
            return False, chat.title, count

        db.add(Channel(
            telegram_id=chat.id, owner_id=owner_id, title=chat.title,
            username=getattr(chat, "username", None),
            members_count=count, photo_file_id=photo_id, photo_url=photo_url
        ))
        await db.commit()
        return True, chat.title, count

# 🚀 ФИКС: StateFilter("*") ГАРАНТИРУЕТ, ЧТО БОТ ПОЙМАЕТ ЭТО СОБЫТИЕ!
@router.message(F.chat_shared, StateFilter("*"))
async def on_chat_shared(message: Message, bot: Bot, state: FSMContext):
    chat_id = message.chat_shared.chat_id
    await message.answer("⏳ Сохраняем канал...", reply_markup=ReplyKeyboardRemove())
    
    try:
        is_new, title, count = await _save_chat(chat_id, message.from_user.id, bot)
        await state.clear()
        await message.answer(f"🎉 <b>{title}</b> успешно добавлен!\n👥 Участников: {count:,}\n\nВернитесь в приложение 👇", reply_markup=_back_kb())
    except asyncio.TimeoutError:
        await message.answer("❌ Сервер Telegram не отвечает. Попробуйте еще раз.", reply_markup=_request_chat_kb())
    except Exception as e:
        logging.error(f"❌ Ошибка в chat_shared: {e}", exc_info=True)
        await message.answer("❌ Ошибка при добавлении. Проверьте права бота.", reply_markup=_request_chat_kb())

@router.message(ChannelStates.waiting_for_channel)
async def process_manual_channel(message: Message, state: FSMContext, bot: Bot):
    chat_id = None
    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        chat_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        chat_id = message.text.strip()
    
    if not chat_id: 
        # Добавили ответ, чтобы бот не молчал, если прислали ерунду!
        await message.answer("❌ Пожалуйста, выберите канал кнопкой ниже или пришлите @username.", reply_markup=_request_chat_kb())
        return

    await message.answer("🔍 Проверяем права...", reply_markup=ReplyKeyboardRemove())
    try:
        me = await asyncio.wait_for(bot.get_me(), timeout=5.0)
        member = await asyncio.wait_for(bot.get_chat_member(chat_id=chat_id, user_id=me.id), timeout=5.0)
        if member.status != "administrator":
            await message.answer("❌ Бот ещё не администратор в этом канале.", reply_markup=_request_chat_kb())
            return
        is_new, title, count = await _save_chat(chat_id, message.from_user.id, bot)
        await state.clear()
        await message.answer(f"🎉 <b>{title}</b> успешно добавлен!\n👥 Участников: {count:,}", reply_markup=_back_kb())
    except asyncio.TimeoutError:
        await message.answer("❌ Сервер Telegram не отвечает. Попробуйте еще раз.")
    except Exception as e:
        logging.error(f"❌ process_manual error: {e}")
        await message.answer("❌ Бот не имеет доступа к этому каналу.", reply_markup=_request_chat_kb())

@router.message(Command("cancel"), StateFilter("*"))
async def cancel_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Добавление отменено.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Вы можете вернуться в приложение.", reply_markup=_back_kb())