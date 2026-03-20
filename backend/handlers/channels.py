import logging
import os

from aiogram import Router, Bot, F
from aiogram.types import (
    Message, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.filters.chat_member_updated import (
    ChatMemberUpdatedFilter, IS_NOT_MEMBER, ADMINISTRATOR
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import Channel

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")

CHANNEL_RIGHTS = "post_messages%2Bedit_messages%2Bdelete_messages"
GROUP_RIGHTS   = "post_messages%2Bdelete_messages"


class ChannelStates(StatesGroup):
    waiting_for_channel = State()


def _back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


def _native_kb(bot_username: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📢 Выбрать канал из списка",
            url=f"https://t.me/{bot_username}?startchannel=true&admin={CHANNEL_RIGHTS}"
        )],
        [InlineKeyboardButton(
            text="👥 Выбрать группу из списка",
            url=f"https://t.me/{bot_username}?startgroup=true&admin={GROUP_RIGHTS}"
        )],
        [InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))],
    ])


async def _save_chat(chat_id, owner_id: int, bot: Bot):
    chat  = await bot.get_chat(chat_id)
    count = await bot.get_chat_member_count(chat_id)
    photo = chat.photo.small_file_id if chat.photo else None
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Channel).where(Channel.telegram_id == chat.id))
        if existing:
            existing.title = chat.title
            existing.username = getattr(chat, "username", None)
            existing.members_count = count
            existing.photo_file_id = photo
            existing.is_active = True
            await db.commit()
            return False, chat.title, count
        db.add(Channel(
            telegram_id=chat.id, owner_id=owner_id,
            title=chat.title, username=getattr(chat, "username", None),
            members_count=count, photo_file_id=photo,
        ))
        await db.commit()
        return True, chat.title, count


# ── /start add_channel — кнопка из Mini App вызывает именно это ──────────────
# Mini App делает: openTelegramLink("https://t.me/BOT?start=add_channel")
# Telegram отправляет боту: /start add_channel
# CommandObject.args == "add_channel"

@router.message(CommandStart(deep_link=True))
async def start_deep_link(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    args = command.args  # "add_channel" или "add_post"

    if args == "add_channel":
        await state.set_state(ChannelStates.waiting_for_channel)
        bot_info = await bot.get_me()
        await message.answer(
            "💬 Пришлите <b>@username</b> канала или перешлите сообщение из него.\n\n"
            "⚠️ Бот должен быть админом с правами на публикацию и редактирование сообщений.\n\n"
            "Для отмены 👉 /cancel\n\n"
            "🔥 <b>Или выберите через кнопку ниже</b> — права проставятся автоматически ✅",
            reply_markup=_native_kb(bot_info.username),
            parse_mode="HTML",
        )
    # add_post обрабатывается в posts.py — но туда deep_link=True не дойдёт
    # поэтому add_post тоже обрабатываем здесь и импортируем логику


# ── Автодобавление когда бот стал администратором ────────────────────────────

@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR)
)
async def bot_added_as_admin(event: ChatMemberUpdated):
    user_id = event.from_user.id
    try:
        is_new, title, count = await _save_chat(event.chat.id, user_id, event.bot)
        kind = "Канал" if event.chat.type == "channel" else "Группа"
        await event.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 {kind} <b>{title}</b> {'добавлен(а)' if is_new else 'обновлён(а)'}!\n"
                f"👥 Участников: <b>{count:,}</b>"
            ),
            reply_markup=_back_kb(),
            parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"bot_added_as_admin: {e}")


# ── Ручной ввод @username ─────────────────────────────────────────────────────

@router.message(ChannelStates.waiting_for_channel)
async def process_manual(message: Message, state: FSMContext, bot: Bot):
    chat_id = None
    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        chat_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        chat_id = message.text.strip()

    if not chat_id:
        await message.answer("❌ Отправьте <b>@username</b> или перешлите сообщение.", parse_mode="HTML")
        return

    await message.answer("🔍 Проверяем...")
    try:
        me     = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)
        if member.status != "administrator":
            await message.answer("❌ Бот не администратор этого канала.", reply_markup=_native_kb(me.username))
            return
        chat = await bot.get_chat(chat_id)
        is_new, title, count = await _save_chat(chat.id, message.from_user.id, bot)
        await state.clear()
        await message.answer(
            f"🎉 <b>{title}</b> {'добавлен(а)' if is_new else 'обновлён(а)'}!\n"
            f"👥 Участников: <b>{count:,}</b>",
            reply_markup=_back_kb(), parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"process_manual: {e}")
        await message.answer("❌ Не удалось найти канал. Проверьте @username и права бота.")


@router.message(Command("cancel"), ChannelStates.waiting_for_channel)
async def cancel_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=_back_kb())