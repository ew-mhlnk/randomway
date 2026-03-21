import logging
import os

from aiogram import Router, Bot, F
from aiogram.types import (
    Message, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.filters import Command, CommandStart
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

# Используем %2B вместо +, чтобы ссылка корректно открывалась
CHANNEL_RIGHTS = "post_messages%2Bedit_messages%2Bdelete_messages"
GROUP_RIGHTS = "post_messages%2Bdelete_messages"


class ChannelStates(StatesGroup):
    waiting_for_channel = State()


def _back_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в мини-апп"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


def _add_chat_inline_kb(bot_username: str) -> InlineKeyboardMarkup:
    """Inline-кнопки с системным окном добавления бота в канал/группу"""
    channel_url = f"https://t.me/{bot_username}?startchannel=true&admin={CHANNEL_RIGHTS}"
    group_url = f"https://t.me/{bot_username}?startgroup=true&admin={GROUP_RIGHTS}"

    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 Добавить канал", url=channel_url)],[InlineKeyboardButton(text="👥 Добавить группу", url=group_url)],
    ])


async def _save_chat(chat_id, owner_id: int, bot: Bot) -> tuple[bool, str, int]:
    chat = await bot.get_chat(chat_id)
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
            existing.owner_id = owner_id
            await db.commit()
            return False, chat.title, count

        db.add(Channel(
            telegram_id=chat.id,
            owner_id=owner_id,
            title=chat.title,
            username=getattr(chat, "username", None),
            members_count=count,
            photo_file_id=photo,
        ))
        await db.commit()
        return True, chat.title, count


# ── 1. Юзер пришел из Мини-Аппа по ссылке ?start=add_channel ──────────────────

@router.message(CommandStart(deep_link=True, magic=F.args == "add_channel"))
async def cmd_add_channel_deep_link(message: Message, state: FSMContext, bot: Bot):
    await state.set_state(ChannelStates.waiting_for_channel)
    bot_me = await bot.get_me()
    
    text = (
        "💬 Пришлите username канала в формате @durov или перешлите сообщение "
        "из канала (например приватного), который вы хотите добавить.\n\n"
        "⚠️ Бот должен быть админом канала с правами на публикацию и редактирование сообщений.\n\n"
        "Для отмены нажмите 👉🏻 /cancel\n\n"
        "🔥 Вы также можете добавить канал с помощью кнопки в меню (это удобно - бот сам добавится в админы с нужными правами) 👇🏻"
    )
    
    await message.answer(text, reply_markup=_add_chat_inline_kb(bot_me.username))


# ── 2. Бот автоматически добавлен как админ (Сработала Inline кнопка) ─────────
# Когда юзер выбирает канал в нативном окне и дает права, Telegram присылает этот ивент

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR))
async def bot_added_as_admin(event: ChatMemberUpdated):
    user_id = event.from_user.id
    try:
        is_new, title, count = await _save_chat(event.chat.id, user_id, event.bot)
        kind = "Канал" if event.chat.type == "channel" else "Группа"
        
        await event.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ {kind} <b>{title}</b> успешно добавлен!\n"
                f"👥 Подписчиков: <b>{count:,}</b>\n\n"
                "Теперь вы можете вернуться в приложение."
            ),
            reply_markup=_back_kb(),
        )
    except Exception as e:
        logging.error(f"bot_added_as_admin error: {e}")


# ── 3. Ручное добавление через @username или пересылку сообщения ──────────────

@router.message(ChannelStates.waiting_for_channel)
async def process_manual(message: Message, state: FSMContext, bot: Bot):
    chat_id = None
    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        chat_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        chat_id = message.text.strip()

    if not chat_id:
        await message.answer("❌ Отправьте <b>@username</b> или перешлите сообщение.")
        return

    await message.answer("🔍 Проверяем права...")

    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)

        if member.status != "administrator":
            await message.answer(
                "❌ Бот ещё не администратор.\n"
                "Добавьте бота через кнопку ниже и попробуйте снова.",
                reply_markup=_add_chat_inline_kb(me.username)
            )
            return

        chat = await bot.get_chat(chat_id)
        is_new, title, count = await _save_chat(chat.id, message.from_user.id, bot)

        await state.clear()
        await message.answer(
            f"✅ <b>{title}</b> успешно добавлен!\n"
            f"👥 Участников: <b>{count:,}</b>\n\n"
            "Вернитесь в приложение 👇",
            reply_markup=_back_kb(),
        )

    except Exception as e:
        logging.error(f"process_manual: {e}")
        await message.answer("❌ Не удалось найти канал/группу. Убедитесь, что бот назначен администратором.")


# ── Отмена ────────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), ChannelStates.waiting_for_channel)
async def cancel_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Добавление отменено.", reply_markup=_back_kb())