"""backend\handlers\channels.py"""

import logging
import os

from aiogram import Router, Bot, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat,
    ChatAdministratorRights, ReplyKeyboardRemove
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

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


def _request_chat_kb() -> ReplyKeyboardMarkup:
    channel_rights = ChatAdministratorRights(
        is_anonymous=False, can_manage_chat=True, can_post_messages=True,
        can_edit_messages=True, can_delete_messages=True,
        can_manage_video_chats=False, can_restrict_members=False,
        can_promote_members=False, can_change_info=False, can_invite_users=False,
    )
    group_rights = ChatAdministratorRights(
        is_anonymous=False, can_manage_chat=True, can_delete_messages=True,
        can_manage_video_chats=False, can_restrict_members=True,
        can_promote_members=False, can_change_info=False,
        can_invite_users=True, can_pin_messages=True, can_manage_topics=False,
    )
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(
                text="📁 Добавить канал",
                request_chat=KeyboardButtonRequestChat(
                    request_id=1, chat_is_channel=True,
                    user_administrator_rights=channel_rights,
                    bot_administrator_rights=channel_rights,
                )
            ),
            KeyboardButton(
                text="💬 Добавить группу",
                request_chat=KeyboardButtonRequestChat(
                    request_id=2, chat_is_channel=False,
                    user_administrator_rights=group_rights,
                    bot_administrator_rights=group_rights,
                )
            ),
        ]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _save_chat(chat_id: int, owner_id: int, bot: Bot) -> tuple[bool, str, int]:
    chat  = await bot.get_chat(chat_id)
    count = await bot.get_chat_member_count(chat_id)
    photo = chat.photo.small_file_id if chat.photo else None

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(
            select(Channel).where(Channel.telegram_id == chat.id)
        )
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
# Срабатывает когда пользователь пишет /newchannel прямо в боте.
# Из Mini App flow идёт через /bot/request-channel в api.py (FSM ставится там).

@router.message(Command("newchannel"))
async def cmd_new_channel(message: Message, state: FSMContext):
    await state.set_state(ChannelStates.waiting_for_channel)
    # Анимированный огонь — отдельным сообщением (Telegram рендерит его большим и анимированным)
    await message.answer("🔥")
    await message.answer(
        "💬 Пришлите <b>@username</b> канала или перешлите любое сообщение "
        "из канала (в том числе приватного).\n\n"
        "⚠️ Бот должен быть администратором канала с правами на публикацию "
        "и редактирование сообщений.\n\n"
        "Для отмены — /cancel\n\n"
        "Или нажмите кнопку ниже — Telegram откроет список ваших каналов "
        "и автоматически добавит бота с нужными правами 👇",
        reply_markup=_request_chat_kb(),
    )


# ── Пользователь выбрал канал через нативный пикер ───────────────────────────

@router.message(F.chat_shared)
async def on_chat_shared(message: Message, bot: Bot, state: FSMContext):
    chat_id = message.chat_shared.chat_id
    await message.answer("⏳ Добавляем...")

    try:
        chat = await bot.get_chat(chat_id)
        is_new, title, count = await _save_chat(chat.id, message.from_user.id, bot)
        kind = "Канал" if chat.type == "channel" else "Группа"
        await state.clear()
        await message.answer("✅", reply_markup=ReplyKeyboardRemove())
        # Анимированный фейерверк при успехе
        await message.answer("🎉")
        await message.answer(
            f"{kind} <b>{title}</b> успешно добавлен!\n"
            f"👥 Подписчиков: <b>{count:,}</b>\n\n"
            "Вернитесь в приложение — канал уже в списке.",
            reply_markup=_back_kb(),
        )
    except Exception as e:
        logging.error(f"chat_shared error: {e}")
        await message.answer(
            "❌ Ошибка при добавлении.\n"
            "Убедитесь, что бот получил права администратора, и попробуйте снова.",
            reply_markup=_request_chat_kb(),
        )


# ── Ручной ввод @username или пересылка ──────────────────────────────────────

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
        me     = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)

        if member.status != "administrator":
            await message.answer(
                "❌ Бот ещё не администратор в этом канале.\n"
                "Назначьте его вручную или воспользуйтесь кнопкой ниже 👇",
                reply_markup=_request_chat_kb(),
            )
            return

        is_new, title, count = await _save_chat(chat_id, message.from_user.id, bot)
        await state.clear()
        await message.answer("✅", reply_markup=ReplyKeyboardRemove())
        await message.answer("🎉")
        await message.answer(
            f"<b>{title}</b> успешно добавлен!\n"
            f"👥 Участников: <b>{count:,}</b>\n\n"
            "Вернитесь в приложение 👇",
            reply_markup=_back_kb(),
        )
    except Exception as e:
        logging.error(f"process_manual error: {e}")
        await message.answer(
            "❌ Не удалось найти канал. "
            "Убедитесь, что бот назначен администратором, и попробуйте снова."
        )


# ── /cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), ChannelStates.waiting_for_channel)
async def cancel_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Добавление отменено.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Вернуться в приложение:", reply_markup=_back_kb())