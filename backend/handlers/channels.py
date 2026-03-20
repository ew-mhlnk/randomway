import logging
import os

from aiogram import Router, Bot, F
from aiogram.types import (
    Message, ChatMemberUpdated,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.filters import Command
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

# %2B вместо + — иначе права не проставляются (+ читается как пробел)
CHANNEL_RIGHTS = "post_messages%2Bedit_messages%2Bdelete_messages"
GROUP_RIGHTS = "post_messages%2Bdelete_messages"


class ChannelStates(StatesGroup):
    waiting_for_channel = State()


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


def _native_add_kb(bot_username: str, chat_type: str = "channel") -> InlineKeyboardMarkup:
    """Кнопка нативного выбора канала/группы через диалог Telegram"""
    if chat_type == "group":
        url = f"https://t.me/{bot_username}?startgroup=true&admin={GROUP_RIGHTS}"
        label = "👥 Выбрать группу из списка"
    else:
        url = f"https://t.me/{bot_username}?startchannel=true&admin={CHANNEL_RIGHTS}"
        label = "📢 Выбрать канал из списка"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, url=url)],
        [InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))],
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


# ── Бот автоматически стал администратором ────────────────────────────────────

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
                f"👥 Участников: <b>{count:,}</b>\n\n"
                "Теперь можно использовать в розыгрышах."
            ),
            reply_markup=_back_kb(),
            parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"bot_added_as_admin: {e}")


# ── Кнопка «📢 Добавить канал» (Reply Keyboard) ───────────────────────────────

@router.message(F.text == "📢 Добавить канал")
async def btn_add_channel(message: Message, state: FSMContext, bot: Bot):
    await state.set_state(ChannelStates.waiting_for_channel)
    await state.update_data(chat_type="channel")
    bot_info = await bot.get_me()
    await message.answer(
        "💬 Пришлите <b>@username</b> канала или перешлите сообщение из него "
        "(работает и для приватных каналов).\n\n"
        "⚠️ Бот должен быть админом с правами на публикацию и редактирование сообщений.\n\n"
        "Для отмены 👉 /cancel\n\n"
        "🔥 <b>Или выберите канал кнопкой ниже</b> — права проставятся автоматически ✅",
        reply_markup=_native_add_kb(bot_info.username, "channel"),
        parse_mode="HTML",
    )


# ── Кнопка «👥 Добавить группу» (Reply Keyboard) ─────────────────────────────

@router.message(F.text == "👥 Добавить группу")
async def btn_add_group(message: Message, state: FSMContext, bot: Bot):
    await state.set_state(ChannelStates.waiting_for_channel)
    await state.update_data(chat_type="group")
    bot_info = await bot.get_me()
    await message.answer(
        "💬 Пришлите <b>@username</b> группы или перешлите сообщение из неё.\n\n"
        "⚠️ Бот должен быть админом с правами на публикацию сообщений.\n\n"
        "Для отмены 👉 /cancel\n\n"
        "🔥 <b>Или выберите группу кнопкой ниже</b> — права проставятся автоматически ✅",
        reply_markup=_native_add_kb(bot_info.username, "group"),
        parse_mode="HTML",
    )


# ── Ручное добавление через @username или пересылку ───────────────────────────

@router.message(ChannelStates.waiting_for_channel)
async def process_manual(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    chat_type = data.get("chat_type", "channel")

    chat_id = None
    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        chat_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        chat_id = message.text.strip()

    if not chat_id:
        await message.answer(
            "❌ Отправьте <b>@username</b> или перешлите сообщение.",
            parse_mode="HTML",
        )
        return

    await message.answer("🔍 Проверяем...")

    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)

        if member.status != "administrator":
            await message.answer(
                "❌ Бот ещё не администратор.\n"
                "Добавьте бота через кнопку ниже и попробуйте снова.",
                reply_markup=_native_add_kb(me.username, chat_type),
            )
            return

        chat = await bot.get_chat(chat_id)
        is_new, title, count = await _save_chat(chat.id, message.from_user.id, bot)

        await state.clear()
        await message.answer(
            f"🎉 <b>{title}</b> {'добавлен(а)' if is_new else 'обновлён(а)'} успешно!\n"
            f"👥 Участников: <b>{count:,}</b>",
            reply_markup=_back_kb(),
            parse_mode="HTML",
        )

    except Exception as e:
        logging.error(f"process_manual: {e}")
        await message.answer(
            "❌ Не удалось найти канал/группу.\n"
            "Проверьте что бот добавлен как администратор."
        )


# ── /cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), ChannelStates.waiting_for_channel)
async def cancel_channel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=_back_kb())