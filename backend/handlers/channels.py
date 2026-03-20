import logging
import os
from urllib.parse import urlencode

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

# Права которые нужны боту для публикации постов
# Важно: используем %2B (URL-encoded +) а НЕ просто +
# Иначе Telegram читает + как пробел и права не проставляются
CHANNEL_ADMIN = "post_messages%2Bedit_messages%2Bdelete_messages"
GROUP_ADMIN = "post_messages%2Bdelete_messages"


class ChannelStates(StatesGroup):
    waiting_for_channel = State()


def _mini_app_kb(text: str = "🎲 Открыть приложение") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


def _add_menu_kb(bot_username: str) -> InlineKeyboardMarkup:
    """
    Меню добавления канала/группы через нативный диалог Telegram.
    %2B вместо + — иначе Telegram читает + как пробел и галочки не проставляются.
    """
    channel_url = f"https://t.me/{bot_username}?startchannel=true&admin={CHANNEL_ADMIN}"
    group_url = f"https://t.me/{bot_username}?startgroup=true&admin={GROUP_ADMIN}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Добавить канал", url=channel_url)],
        [InlineKeyboardButton(text="👥 Добавить группу/чат", url=group_url)],
        [InlineKeyboardButton(text="🎲 Открыть приложение", web_app=WebAppInfo(url=MINI_APP_URL))],
    ])


async def _save_chat(chat_id: int, owner_id: int, bot: Bot) -> tuple[bool, object]:
    """Сохраняет канал/группу. Возвращает (is_new, chat_object)."""
    try:
        chat = await bot.get_chat(chat_id)
        members_count = await bot.get_chat_member_count(chat_id)
        photo_file_id = chat.photo.small_file_id if chat.photo else None

        async with AsyncSessionLocal() as db:
            existing = await db.scalar(
                select(Channel).where(Channel.telegram_id == chat.id)
            )
            if existing:
                existing.members_count = members_count
                existing.photo_file_id = photo_file_id
                existing.title = chat.title
                existing.username = getattr(chat, "username", None)
                existing.is_active = True
                await db.commit()
                return False, chat

            db.add(Channel(
                telegram_id=chat.id,
                owner_id=owner_id,
                title=chat.title,
                username=getattr(chat, "username", None),
                members_count=members_count,
                photo_file_id=photo_file_id,
            ))
            await db.commit()
            return True, chat

    except Exception as e:
        logging.error(f"_save_chat error: {e}")
        raise


# ── 1. Бот автоматически добавлен администратором ────────────────────────────

@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR)
)
async def bot_added_as_admin(event: ChatMemberUpdated):
    chat = event.chat
    user_id = event.from_user.id

    try:
        is_new, chat_obj = await _save_chat(chat.id, user_id, event.bot)
        count = await event.bot.get_chat_member_count(chat.id)
        chat_type = "Канал" if chat.type == "channel" else "Группа"

        if is_new:
            text = (
                f"🎉 {chat_type} <b>{chat.title}</b> добавлен(а)!\n"
                f"👥 Участников: <b>{count:,}</b>\n\n"
                "Теперь его можно использовать в розыгрышах.\n\n"
                "Добавить ещё 👉 /newchannel"
            )
        else:
            text = (
                f"🔄 {chat_type} <b>{chat.title}</b> обновлён(а).\n"
                f"👥 Участников: <b>{count:,}</b>"
            )

        await event.bot.send_message(
            chat_id=user_id, text=text,
            reply_markup=_mini_app_kb(), parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"bot_added_as_admin error: {e}")


# ── 2. /newchannel — главная команда добавления ───────────────────────────────

@router.message(Command("newchannel"))
async def cmd_newchannel(message: Message, state: FSMContext, bot: Bot):
    await _show_add_menu(message, state, bot)


# deep link ?start=add_channel (из Mini App)
@router.message(CommandStart(deep_link=True), F.text.contains("add_channel"))
async def deep_add_channel(message: Message, state: FSMContext, bot: Bot):
    await _show_add_menu(message, state, bot)


async def _show_add_menu(message: Message, state: FSMContext, bot: Bot):
    await state.set_state(ChannelStates.waiting_for_channel)
    bot_info = await bot.get_me()

    await message.answer(
        "📢 <b>Добавление канала или группы</b>\n\n"
        "Нажмите нужную кнопку ниже — Telegram откроет список ваших каналов и групп.\n"
        "Галочки прав проставятся автоматически ✅\n\n"
        "Или пришлите <b>@username</b> / перешлите сообщение из канала вручную.\n\n"
        "<i>Примечание: в нативном диалоге Telegram показывает только каналы и группы "
        "где вы являетесь владельцем. Остальные добавьте через @username.</i>\n\n"
        "Для отмены 👉 /cancel",
        reply_markup=_add_menu_kb(bot_info.username),
        parse_mode="HTML",
    )


# ── 3. Ручное добавление через @username или пересылку ───────────────────────

@router.message(ChannelStates.waiting_for_channel)
async def process_manual(message: Message, state: FSMContext, bot: Bot):
    channel_id = None

    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        channel_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        channel_id = message.text.strip()

    if not channel_id:
        await message.answer(
            "❌ Отправьте <b>@username</b> или перешлите сообщение.",
            parse_mode="HTML",
        )
        return

    await message.answer("🔍 Проверяем...")

    try:
        me = await bot.get_me()
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=me.id)

        if bot_member.status != "administrator":
            await message.answer(
                "❌ Бот ещё не администратор этого канала.\n\n"
                "Добавьте бота через /newchannel — там можно выдать права в 2 клика."
            )
            return

        if not getattr(bot_member, "can_post_messages", True):
            await message.answer(
                "❌ Боту не выданы права на публикацию сообщений.\n"
                "Отредактируйте права администратора."
            )
            return

        is_new, chat_obj = await _save_chat(
            channel_id if isinstance(channel_id, int) else (await bot.get_chat(channel_id)).id,
            message.from_user.id,
            bot
        )
        count = await bot.get_chat_member_count(
            channel_id if isinstance(channel_id, int) else channel_id
        )

        await state.clear()
        await message.answer(
            f"🎉 <b>{chat_obj.title}</b> {'добавлен(а)' if is_new else 'обновлён(а)'}!\n"
            f"👥 Участников: <b>{count:,}</b>\n\n"
            "Добавить ещё 👉 /newchannel",
            reply_markup=_mini_app_kb("🎲 Вернуться в приложение"),
            parse_mode="HTML",
        )

    except Exception as e:
        logging.error(f"process_manual error: {e}")
        await message.answer(
            "❌ Не удалось получить данные канала.\n"
            "Проверьте что бот является администратором и @username написан верно."
        )


# ── 4. /cancel ────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), ChannelStates.waiting_for_channel)
async def cancel_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=_mini_app_kb())