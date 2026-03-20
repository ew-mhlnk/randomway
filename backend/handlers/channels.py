import logging
import os

from aiogram import Router, Bot, F
from aiogram.types import (
    Message, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.filters.chat_member_updated import (
    ChatMemberUpdatedFilter, IS_NOT_MEMBER, ADMINISTRATOR, MEMBER
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import Channel

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")


class ChannelStates(StatesGroup):
    waiting_for_channel = State()


def _mini_app_kb(text: str = "🎲 Открыть приложение") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


def _add_kb(bot_username: str) -> InlineKeyboardMarkup:
    """
    Две кнопки: нативный выбор канала + нативный выбор группы.

    Почему только 3 канала в списке:
    Telegram показывает в этом диалоге только каналы/группы где ты ВЛАДЕЛЕЦ
    (owner) или где у тебя есть право «Выбор администраторов».
    Если ты просто администратор без этого права — канал не попадёт в список.
    Это ограничение Telegram, не баг бота.
    Альтернатива — ручное добавление через @username.

    Права: post_messages + edit_messages + delete_messages = «Управление сообщениями 3/3»
    """
    channel_link = (
        f"https://t.me/{bot_username}"
        f"?startchannel=true"
        f"&admin=post_messages+edit_messages+delete_messages"
    )
    group_link = (
        f"https://t.me/{bot_username}"
        f"?startgroup=true"
        f"&admin=post_messages+edit_messages+delete_messages"
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Добавить канал", url=channel_link)],
        [InlineKeyboardButton(text="👥 Добавить группу", url=group_link)],
        [InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))],
    ])


async def _save_chat(chat_id: int, owner_id: int, bot: Bot) -> tuple[bool, str]:
    """
    Сохраняет канал или группу в БД.
    Возвращает (is_new, title).
    """
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
                return False, chat.title

            db.add(Channel(
                telegram_id=chat.id,
                owner_id=owner_id,
                title=chat.title,
                username=getattr(chat, "username", None),
                members_count=members_count,
                photo_file_id=photo_file_id,
            ))
            await db.commit()
            return True, chat.title

    except Exception as e:
        logging.error(f"_save_chat error: {e}")
        return False, "Неизвестно"


# ── Автодобавление: бот стал администратором (канал ИЛИ группа) ───────────────

@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR)
)
async def bot_added_as_admin(event: ChatMemberUpdated):
    chat = event.chat
    user_id = event.from_user.id

    is_new, title = await _save_chat(chat.id, user_id, event.bot)

    try:
        count = await event.bot.get_chat_member_count(chat.id)
        subs_line = f"\n👥 Участников: <b>{count:,}</b>"
    except Exception:
        subs_line = ""

    if is_new:
        text = (
            f"🎉 {'Канал' if chat.type == 'channel' else 'Группа'} "
            f"<b>{title}</b> добавлен(а) успешно!{subs_line}\n\n"
            "Теперь можно использовать в розыгрышах.\n"
            "Добавить ещё 👉🏻 /newchannel"
        )
    else:
        text = f"🔄 <b>{title}</b> обновлён(а).{subs_line}"

    try:
        await event.bot.send_message(
            chat_id=user_id, text=text,
            reply_markup=_mini_app_kb(), parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"Cannot notify user {user_id}: {e}")


# ── /newchannel и ?start=add_channel ─────────────────────────────────────────
# ВАЖНО: используем F.text фильтр вместо CommandStart(deep_link=True)
# чтобы не конфликтовать с posts.py

@router.message(Command("newchannel"))
async def cmd_newchannel(message: Message, state: FSMContext, bot: Bot):
    await _show_add_channel_menu(message, state, bot)


@router.message(CommandStart(deep_link=True), F.text.endswith("add_channel"))
async def deep_add_channel(message: Message, state: FSMContext, bot: Bot):
    await _show_add_channel_menu(message, state, bot)


async def _show_add_channel_menu(message: Message, state: FSMContext, bot: Bot):
    await state.set_state(ChannelStates.waiting_for_channel)
    bot_info = await bot.get_me()
    await message.answer(
        "💬 <b>Добавление канала или группы</b>\n\n"
        "Пришлите <b>@username</b> или перешлите сообщение из канала/группы.\n\n"
        "⚠️ Бот должен быть администратором с правами на публикацию.\n\n"
        "🔥 <b>Или выберите через кнопку ниже</b> — Telegram покажет список ваших каналов и групп 👇\n\n"
        "<i>Если нужного канала нет в списке — добавьте вручную через @username.\n"
        "Telegram показывает только каналы/группы, где вы владелец.</i>",
        reply_markup=_add_kb(bot_info.username),
        parse_mode="HTML",
    )


@router.message(ChannelStates.waiting_for_channel)
async def process_manual_channel(message: Message, state: FSMContext, bot: Bot):
    channel_id = None

    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        channel_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        channel_id = message.text.strip()

    if not channel_id:
        await message.answer(
            "❌ Отправьте <b>@username</b> или перешлите сообщение из канала/группы.",
            parse_mode="HTML",
        )
        return

    await message.answer("🔍 Проверяем...")

    try:
        me = await bot.get_me()
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=me.id)
        chat = await bot.get_chat(channel_id)

        if bot_member.status != "administrator":
            await message.answer(
                "❌ Бот не является администратором.\n"
                "Добавьте бота и выдайте права на публикацию сообщений."
            )
            return

        if not getattr(bot_member, "can_post_messages", False):
            await message.answer(
                "❌ У бота нет права публиковать сообщения.\n"
                "Отредактируйте права администратора и попробуйте снова."
            )
            return

        is_new, title = await _save_chat(chat.id, message.from_user.id, bot)
        count = await bot.get_chat_member_count(chat.id)

        await state.clear()
        await message.answer(
            f"🎉 <b>{title}</b> {'добавлен(а)' if is_new else 'обновлён(а)'} успешно.\n"
            f"👥 Участников: <b>{count:,}</b>\n\n"
            "Добавить ещё 👉🏻 /newchannel",
            reply_markup=_mini_app_kb("🎲 Вернуться в приложение"),
            parse_mode="HTML",
        )

    except Exception as e:
        logging.error(f"process_manual_channel: {e}")
        await message.answer(
            "❌ Не удалось найти канал/группу.\n"
            "Проверьте что бот добавлен администратором и @username указан верно."
        )


# ── /cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), ChannelStates.waiting_for_channel)
async def cancel_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=_mini_app_kb())