"""backend\handlers\channels.py"""

import logging
import os
import asyncio

from aiogram import Router, Bot, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat,
    ChatAdministratorRights, ReplyKeyboardRemove, ChatMemberUpdated
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import Channel

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")


class ChannelStates(StatesGroup):
    waiting_for_channel = State()


def _back_kb() -> InlineKeyboardMarkup:
    """Инлайн-кнопка для возврата в Mini App"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎲 Вернуться в приложение",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])


def _request_chat_kb() -> ReplyKeyboardMarkup:
    """
    Генерирует нижние кнопки (Reply Keyboard), которые вызывают нативный
    UI Телеграма для выбора канала/группы с заданными критериями прав.
    """
    # Права для канала (как на твоем скриншоте)
    channel_rights = ChatAdministratorRights(
        is_anonymous=False, 
        can_manage_chat=True, 
        can_post_messages=True,
        can_edit_messages=True, 
        can_delete_messages=True
    )
    
    # Права для группы
    group_rights = ChatAdministratorRights(
        is_anonymous=False, 
        can_manage_chat=True, 
        can_delete_messages=True,
        can_restrict_members=True,
        can_invite_users=True, 
        can_pin_messages=True
    )

    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📁 Добавить канал",
                request_chat=KeyboardButtonRequestChat(
                    request_id=1, 
                    chat_is_channel=True,
                    user_administrator_rights=channel_rights,
                    bot_administrator_rights=channel_rights
                )
            ),
            KeyboardButton(
                text="💬 Добавить группу",
                request_chat=KeyboardButtonRequestChat(
                    request_id=2, 
                    chat_is_channel=False,
                    user_administrator_rights=group_rights,
                    bot_administrator_rights=group_rights
                )
            )
        ]],
        resize_keyboard=True,
        is_persistent=True # Кнопки будут висеть, пока мы их принудительно не уберем
    )


async def _save_chat(chat_id: int, owner_id: int, bot: Bot) -> tuple[bool, str, int]:
    chat  = await bot.get_chat(chat_id)
    count = await bot.get_chat_member_count(chat_id)
    photo = chat.photo.small_file_id if chat.photo else None

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Channel).where(Channel.telegram_id == chat.id))
        if existing:
            existing.title         = chat.title
            existing.username      = getattr(chat, "username", None)
            existing.members_count = count
            existing.photo_file_id = photo
            existing.is_active     = True
            existing.owner_id      = owner_id
            await db.commit()
            return False, chat.title, count

        db.add(Channel(
            telegram_id=chat.id, owner_id=owner_id, title=chat.title,
            username=getattr(chat, "username", None),
            members_count=count, photo_file_id=photo,
        ))
        await db.commit()
        return True, chat.title, count


# ── /newchannel ───────────────────────────────────────────────────────────────
@router.message(Command("newchannel"))
async def cmd_new_channel(message: Message, state: FSMContext):
    await state.set_state(ChannelStates.waiting_for_channel)
    
    text = (
        "💬 Пришлите <b>username</b> канала в формате @durov или перешлите сообщение "
        "из канала (например приватного), который вы хотите добавить.\n\n"
        "⚠️ Бот должен быть админом канала с правами на публикацию и редактирование сообщений.\n\n"
        "Для отмены нажмите 👉🏻 /cancel\n\n"
        "🔥 Вы также можете добавить канал с помощью кнопки в меню "
        "(это удобно - бот сам добавится в админы с нужными правами) 👇🏻"
    )
    # Отправляем Reply-клавиатуру (кнопки внизу экрана)
    await message.answer(text, reply_markup=_request_chat_kb())


# ── ПОЛЬЗОВАТЕЛЬ ВЫБРАЛ КАНАЛ В НАТИВНОМ UI (chat_shared) ─────────────────────
@router.message(F.chat_shared)
async def on_chat_shared(message: Message, bot: Bot, state: FSMContext):
    """Срабатывает, когда пользователь выбрал канал через кнопку и назначил права"""
    chat_id = message.chat_shared.chat_id
    
    # 1. Убираем огромные кнопки добавления канала снизу экрана
    await message.answer("⏳ Сохраняем...", reply_markup=ReplyKeyboardRemove())
    
    # Даем Телеграму полсекунды на синхронизацию прав на их серверах
    await asyncio.sleep(0.5)

    try:
        chat = await bot.get_chat(chat_id)
        is_new, title, count = await _save_chat(chat.id, message.from_user.id, bot)
        kind = "Канал" if chat.type == "channel" else "Группа"
        
        await state.clear()
        
        # 2. Отправляем сообщение об успехе с инлайн-кнопкой для возврата
        await message.answer(
            f"🎉 {kind} <b>{title}</b> успешно добавлен!\n"
            f"👥 Участников: <b>{count:,}</b>\n\n"
            "Вернитесь в приложение — он уже в списке.",
            reply_markup=_back_kb()
        )
    except Exception as e:
        logging.error(f"Ошибка в chat_shared: {e}")
        await message.answer(
            "❌ Ошибка при добавлении. Возможно, вы не дали боту нужные права.\n"
            "Попробуйте снова.",
            reply_markup=_request_chat_kb() # Возвращаем кнопки обратно при ошибке
        )


# ── РЕЗЕРВНЫЙ ВАРИАНТ (Если юзер переслал сообщение или скинул @username) ──────
@router.message(ChannelStates.waiting_for_channel)
async def process_manual_channel(message: Message, state: FSMContext, bot: Bot):
    chat_id = None

    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        chat_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        chat_id = message.text.strip()

    if not chat_id:
        return

    # Убираем клавиатуру
    await message.answer("🔍 Проверяем права...", reply_markup=ReplyKeyboardRemove())

    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)

        if member.status != "administrator":
            await message.answer(
                "❌ Бот ещё не администратор в этом канале.\n"
                "Используйте кнопки меню ниже 👇",
                reply_markup=_request_chat_kb()
            )
            return

        is_new, title, count = await _save_chat(chat_id, message.from_user.id, bot)
        await state.clear()
        await message.answer(
            f"🎉 <b>{title}</b> успешно добавлен!\n"
            f"👥 Участников: <b>{count:,}</b>\n\n"
            "Вернитесь в приложение 👇",
            reply_markup=_back_kb()
        )
    except Exception as e:
        logging.error(f"process_manual error: {e}")
        await message.answer(
            "❌ Бот не имеет доступа к этому каналу.\n"
            "Используйте кнопки ниже 👇", 
            reply_markup=_request_chat_kb()
        )


# ── /cancel ───────────────────────────────────────────────────────────────────
@router.message(Command("cancel"), ChannelStates.waiting_for_channel)
async def cancel_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Добавление отменено.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Вы можете вернуться в приложение.", reply_markup=_back_kb())