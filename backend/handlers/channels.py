import logging
import os

from aiogram import Router, Bot
from aiogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, CommandObject
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, IS_NOT_MEMBER, ADMINISTRATOR
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import Channel

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")


class ChannelStates(StatesGroup):
    waiting_for_channel = State()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR))
async def bot_added_as_admin(event: ChatMemberUpdated):
    """Срабатывает автоматически, когда бот добавлен в канал как админ"""
    chat = event.chat
    user_id = event.from_user.id

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Channel).where(Channel.telegram_id == chat.id))
        if not existing:
            new_channel = Channel(
                telegram_id=chat.id,
                owner_id=user_id,
                title=chat.title,
                username=chat.username,
            )
            db.add(new_channel)
            await db.commit()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Открыть приложение", web_app=WebAppInfo(url=MINI_APP_URL))]
        ]
    )
    try:
        await event.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Канал <b>{chat.title}</b> добавлен успешно!\nТеперь вы можете добавлять его в розыгрыши.",
            reply_markup=kb,
            parse_mode="HTML",
        )
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение юзеру: {e}")


@router.message(CommandStart(deep_link=True))
async def add_channel_fallback(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    if command.args == "add_channel":
        await state.set_state(ChannelStates.waiting_for_channel)

        bot_info = await bot.get_me()
        native_link = f"https://t.me/{bot_info.username}?startchannel=true&admin=post_messages+edit_messages"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить канал", url=native_link)]
            ]
        )
        await message.answer(
            "💬 Пришлите <b>username</b> канала в формате @durov или <b>перешлите сообщение</b> из канала.\n\n"
            "⚠️ Бот должен быть админом канала с правами на публикацию.\n\n"
            "Для отмены нажмите 👉🏻 /cancel\n\n"
            "🔥 <b>Или добавьте канал кнопкой ниже 👇🏻</b>",
            reply_markup=kb,
        )


@router.message(ChannelStates.waiting_for_channel)
async def process_manual_channel(message: Message, state: FSMContext, bot: Bot):
    channel_id = None
    if message.forward_origin and message.forward_origin.type == "channel":
        channel_id = message.forward_origin.chat.id
    elif message.text and message.text.startswith("@"):
        channel_id = message.text

    if not channel_id:
        await message.answer("❌ Перешлите сообщение из канала или отправьте @username.")
        return

    try:
        bot_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        chat = await bot.get_chat(channel_id)

        if bot_member.status != "administrator" or not bot_member.can_post_messages:
            await message.answer("❌ Бот не администратор! Выдайте права и попробуйте снова.")
            return

        async with AsyncSessionLocal() as db:
            existing = await db.scalar(select(Channel).where(Channel.telegram_id == chat.id))
            if not existing:
                db.add(
                    Channel(
                        telegram_id=chat.id,
                        owner_id=message.from_user.id,
                        title=chat.title,
                        username=chat.username,
                    )
                )
                await db.commit()

        await state.clear()
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎲 Открыть приложение", web_app=WebAppInfo(url=MINI_APP_URL))]
            ]
        )
        await message.answer(f"🎉 Канал <b>{chat.title}</b> добавлен успешно!", reply_markup=kb)
    except Exception:
        await message.answer("❌ Ошибка. Убедитесь, что бот в канале и вы ввели верный @username.")