"""backend\handlers\channels.py"""

import logging
import os

from aiogram import Router, Bot, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    ChatMemberUpdated
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
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎲 Вернуться в приложение",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])


def _add_chat_kb(bot_username: str) -> InlineKeyboardMarkup:
    # Генерируем Deep Links. Telegram сам откроет меню выбора канала и добавит бота!
    channel_url = f"https://t.me/{bot_username}?startchannel=true&admin=post_messages+edit_messages+delete_messages"
    group_url = f"https://t.me/{bot_username}?startgroup=true&admin=delete_messages+restrict_members+invite_users+pin_messages"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 Добавить канал", url=channel_url)],
        [InlineKeyboardButton(text="💬 Добавить группу", url=group_url)]
    ])


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
    bot_username = os.getenv("BOT_USERNAME", "")
    
    text = (
        "💬 Пришлите <b>username</b> канала в формате @durov или перешлите сообщение "
        "из канала (например приватного), который вы хотите добавить.\n\n"
        "⚠️ Бот должен быть админом канала с правами на публикацию и редактирование сообщений.\n\n"
        "Для отмены нажмите 👉🏻 /cancel\n\n"
        "🔥 Вы также можете добавить канал с помощью кнопки в меню "
        "(это удобно - бот сам добавится в админы с нужными правами) 👇🏻"
    )
    await message.answer(text, reply_markup=_add_chat_kb(bot_username))


# ── АВТОМАТИЧЕСКИЙ ПЕРЕХВАТ ДОБАВЛЕНИЯ БОТА (Deep Link Magic) ────────────────
@router.my_chat_member()
async def on_bot_added_to_chat(update: ChatMemberUpdated, bot: Bot, state: FSMContext):
    """Срабатывает мгновенно, когда юзер назначает бота админом через инлайн-кнопку"""
    
    # Нас интересует только когда бот становится админом
    if update.new_chat_member.status == "administrator":
        chat = update.chat
        owner_id = update.from_user.id  # ID человека, который добавил бота
        
        try:
            is_new, title, count = await _save_chat(chat.id, owner_id, bot)
            kind = "Канал" if chat.type == "channel" else "Группа"
            
            # Сбрасываем ожидание, если оно было
            await state.clear()
            
            # Отправляем юзеру в ЛИЧКУ сообщение об успехе
            await bot.send_message(
                chat_id=owner_id,
                text=f"🎉 {kind} <b>{title}</b> успешно добавлен!\n"
                     f"👥 Участников: <b>{count:,}</b>\n\n"
                     "Теперь он доступен в приложении 👇",
                reply_markup=_back_kb()
            )
        except Exception as e:
            logging.error(f"Ошибка при сохранении канала из my_chat_member: {e}")


# ── РУЧНОЙ ВВОД (Резервный вариант) ──────────────────────────────────────────
@router.message(ChannelStates.waiting_for_channel)
async def process_manual_channel(message: Message, state: FSMContext, bot: Bot):
    chat_id = None

    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        chat_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        chat_id = message.text.strip()

    if not chat_id:
        await message.answer(
            "❌ Не понял. Пришлите <b>@username</b> канала "
            "или перешлите любое сообщение из него."
        )
        return

    await message.answer("🔍 Проверяем права...")

    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)

        if member.status != "administrator":
            bot_username = os.getenv("BOT_USERNAME", "")
            await message.answer(
                "❌ Бот ещё не администратор в этом канале.\n"
                "Сделайте его админом или используйте кнопки ниже 👇",
                reply_markup=_add_chat_kb(bot_username)
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
    except TelegramBadRequest:
        bot_username = os.getenv("BOT_USERNAME", "")
        await message.answer(
            "❌ Бот не имеет доступа к этому каналу.\n"
            "Сначала добавьте его в администраторы с помощью кнопки ниже 👇",
            reply_markup=_add_chat_kb(bot_username)
        )
    except Exception as e:
        logging.error(f"process_manual error: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


# ── /cancel ───────────────────────────────────────────────────────────────────
@router.message(Command("cancel"), ChannelStates.waiting_for_channel)
async def cancel_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Добавление отменено.", reply_markup=_back_kb())