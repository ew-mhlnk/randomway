import os

from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import AsyncSessionLocal
from models import PostTemplate

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")


class PostStates(StatesGroup):
    waiting_for_post = State()


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено. Возвращайтесь в приложение.")


@router.message(CommandStart(deep_link=True))
async def start_add_post(message: Message, command: CommandObject, state: FSMContext):
    if command.args == "add_post":
        await state.set_state(PostStates.waiting_for_post)
        await message.answer(
            "💬 Отправьте мне текст вашего поста.\n\n"
            "✨ Вы можете прислать текст с картинкой или видео (макс. 1024 символа).\n"
            "🔥 Бот поддерживает кастомные эмодзи!\n\n"
            "Для отмены нажмите 👉🏻 /cancel"
        )


@router.message(PostStates.waiting_for_post)
async def process_post_addition(message: Message, state: FSMContext):
    text = message.html_text or ""
    media_id = None
    media_type = None

    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"

    if not text and not media_id:
        await message.answer("❌ Пожалуйста, отправьте текст, фото или видео.")
        return

    async with AsyncSessionLocal() as db:
        new_post = PostTemplate(
            owner_id=message.from_user.id,
            text=text,
            media_id=media_id,
            media_type=media_type,
        )
        db.add(new_post)
        await db.commit()

    await state.clear()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Вернуться к розыгрышу", web_app=WebAppInfo(url=MINI_APP_URL))]
        ]
    )
    await message.answer("🎉 Пост создан и сохранен!\nМожете вернуться в приложение.", reply_markup=kb)