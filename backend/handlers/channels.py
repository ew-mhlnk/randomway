import logging
import os

from aiogram import Router, Bot
from aiogram.types import (
    Message, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.filters.chat_member_updated import (
    ChatMemberUpdatedFilter, IS_NOT_MEMBER, ADMINISTRATOR
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import Channel, User

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")


class ChannelStates(StatesGroup):
    waiting_for_channel = State()


def _mini_app_kb(text: str = "🎲 Открыть приложение") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


def _add_channel_kb(bot_username: str) -> InlineKeyboardMarkup:
    """Кнопка нативного добавления бота в канал через меню Telegram"""
    native_link = f"https://t.me/{bot_username}?startchannel=true&admin=post_messages+edit_messages+delete_messages"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить через меню Telegram", url=native_link)],
        [InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))],
    ])


async def _save_channel(chat_id: int, owner_id: int, bot: Bot) -> Channel | None:
    """
    Получает информацию о канале через Bot API и сохраняет в БД.
    Возвращает объект канала или None если уже существует.
    """
    try:
        chat = await bot.get_chat(chat_id)
        members_count = await bot.get_chat_member_count(chat_id)

        # Аватарка — берём file_id последней маленькой фотки
        photo_file_id = None
        if chat.photo:
            photo_file_id = chat.photo.small_file_id

        async with AsyncSessionLocal() as db:
            existing = await db.scalar(
                select(Channel).where(Channel.telegram_id == chat.id)
            )
            if existing:
                # Обновляем данные если канал уже есть
                existing.members_count = members_count
                existing.photo_file_id = photo_file_id
                existing.title = chat.title
                existing.username = chat.username
                existing.is_active = True
                await db.commit()
                return None  # None = уже существовал

            new_channel = Channel(
                telegram_id=chat.id,
                owner_id=owner_id,
                title=chat.title,
                username=chat.username,
                members_count=members_count,
                photo_file_id=photo_file_id,
            )
            db.add(new_channel)
            await db.commit()
            return new_channel

    except Exception as e:
        logging.error(f"_save_channel error: {e}")
        return None


# ── 1. Автодобавление через нативное меню Telegram ──────────────────────────

@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR)
)
async def bot_added_as_admin(event: ChatMemberUpdated):
    """Срабатывает автоматически когда бот назначен администратором канала"""
    chat = event.chat
    user_id = event.from_user.id

    result = await _save_channel(chat.id, user_id, event.bot)

    subs = ""
    try:
        count = await event.bot.get_chat_member_count(chat.id)
        subs = f"\n👥 Подписчиков: <b>{count:,}</b>"
    except Exception:
        pass

    if result is None:
        msg = (
            f"🔄 Канал <b>{chat.title}</b> обновлён.{subs}\n"
            "Данные синхронизированы с приложением."
        )
    else:
        msg = (
            f"🎉 Канал <b>{chat.title}</b> добавлен успешно!{subs}\n\n"
            "Теперь вы можете добавлять его в розыгрыши.\n"
            "Можете добавить другие каналы 👉🏻 /newchannel"
        )

    try:
        await event.bot.send_message(
            chat_id=user_id,
            text=msg,
            reply_markup=_mini_app_kb("🎲 Открыть приложение"),
            parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"Cannot message user {user_id}: {e}")


# ── 2. Команда /newchannel — ручное добавление ───────────────────────────────

@router.message(Command("newchannel"))
@router.message(CommandStart(deep_link=True))
async def start_add_channel(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    # deep_link срабатывает на ?start=add_channel, команда /newchannel — напрямую
    is_deep = hasattr(command, 'args') and command.args == "add_channel"
    is_cmd = message.text and message.text.startswith("/newchannel")

    if not (is_deep or is_cmd):
        return  # Это другой deep link — пропускаем

    await state.set_state(ChannelStates.waiting_for_channel)

    bot_info = await bot.get_me()
    kb = _add_channel_kb(bot_info.username)

    await message.answer(
        "💬 <b>Добавление канала</b>\n\n"
        "Пришлите <b>@username</b> канала или <b>перешлите любое сообщение</b> из него.\n\n"
        "⚠️ Бот должен быть администратором с правами на публикацию.\n\n"
        "🔥 <b>Или используйте кнопку ниже</b> — Telegram сам предложит выбрать канал "
        "и выдаст боту нужные права 👇",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.message(ChannelStates.waiting_for_channel)
async def process_manual_channel(message: Message, state: FSMContext, bot: Bot):
    """Обработка @username или пересланного сообщения"""
    channel_id = None

    if message.forward_origin and hasattr(message.forward_origin, 'chat'):
        channel_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        channel_id = message.text.strip()

    if not channel_id:
        await message.answer(
            "❌ Отправьте <b>@username</b> канала или перешлите сообщение из него.",
            parse_mode="HTML",
        )
        return

    await message.answer("🔍 Проверяем канал...")

    try:
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=(await bot.get_me()).id)
        chat = await bot.get_chat(channel_id)

        if bot_member.status != "administrator":
            await message.answer(
                "❌ Бот не является администратором этого канала.\n"
                "Добавьте бота в канал и выдайте права на публикацию.",
                parse_mode="HTML",
            )
            return

        if not bot_member.can_post_messages:
            await message.answer(
                "❌ У бота нет прав на публикацию сообщений.\n"
                "Выдайте права и попробуйте снова.",
            )
            return

        await _save_channel(chat.id, message.from_user.id, bot)
        members_count = await bot.get_chat_member_count(chat.id)

        await state.clear()
        await message.answer(
            f"🎉 Канал <b>{chat.title}</b> добавлен успешно.\n"
            f"👥 Подписчиков: <b>{members_count:,}</b>\n\n"
            "Теперь вы можете добавлять его в розыгрыши!\n"
            "Добавить другие каналы 👉🏻 /newchannel",
            reply_markup=_mini_app_kb("🎲 Вернуться в приложение"),
            parse_mode="HTML",
        )

    except Exception as e:
        logging.error(f"process_manual_channel error: {e}")
        await message.answer(
            "❌ Не удалось найти канал. Убедитесь что:\n"
            "• Бот добавлен как администратор\n"
            "• Username написан верно (например @mychannel)",
        )


# ── 3. /cancel ───────────────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cancel_channel(message: Message, state: FSMContext):
    current = await state.get_state()
    if current == ChannelStates.waiting_for_channel:
        await state.clear()
        await message.answer(
            "❌ Добавление канала отменено.",
            reply_markup=_mini_app_kb(),
        )