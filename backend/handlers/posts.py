import os
from aiogram import Router
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, ReplyKeyboardRemove
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import AsyncSessionLocal
from models import PostTemplate
from sqlalchemy.future import select

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")

MAX_TEXT  = 4096
MAX_MEDIA = 1024


class PostStates(StatesGroup):
    waiting_for_post = State()
    waiting_for_edit = State()  # Состояние редактирования


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎲 Вернуться в приложение",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])

@router.message(Command("newpost"))
async def cmd_new_post(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_post)
    await message.answer(
        "💬 Отправьте текст вашего поста.\n✨ Можно прислать текст с картинкой или видео.\nДля отмены — /cancel",
        reply_markup=ReplyKeyboardRemove(),
    )

# --- Приём НОВОГО поста ---
@router.message(PostStates.waiting_for_post)
async def receive_post_content(message: Message, state: FSMContext):
    text = message.html_text or ""
    media_id, media_type = None, None

    if message.photo: media_id, media_type = message.photo[-1].file_id, "photo"
    elif message.video: media_id, media_type = message.video.file_id, "video"
    elif message.animation: media_id, media_type = message.animation.file_id, "animation"

    limit = MAX_MEDIA if media_id else MAX_TEXT
    if len(text) > limit:
        await message.answer(f"❌ Текст слишком длинный: <b>{len(text)}</b> симв. (лимит: {limit}).\nСократите.")
        return
    if not text and not media_id:
        await message.answer("❌ Пришлите текст, фото, видео или GIF.")
        return

    async with AsyncSessionLocal() as db:
        db.add(PostTemplate(owner_id=message.from_user.id, text=text, media_id=media_id, media_type=media_type))
        await db.commit()

    await state.clear()
    await message.answer("✅ Пост сохранён!\nВернитесь в приложение 👇", reply_markup=_back_kb())


# --- Приём ОБНОВЛЕНИЯ существующего поста ---
@router.message(PostStates.waiting_for_edit)
async def edit_post_content(message: Message, state: FSMContext):
    data = await state.get_data()
    template_id = data.get("edit_template_id")
    
    text = message.html_text or ""
    media_id, media_type = None, None

    if message.photo: media_id, media_type = message.photo[-1].file_id, "photo"
    elif message.video: media_id, media_type = message.video.file_id, "video"
    elif message.animation: media_id, media_type = message.animation.file_id, "animation"

    if not text and not media_id:
        await message.answer("❌ Пришлите текст, фото, видео или GIF.")
        return

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(PostTemplate).where(PostTemplate.id == template_id))
        if existing:
            existing.text = text
            existing.media_id = media_id
            existing.media_type = media_type
            await db.commit()

    await state.clear()
    await message.answer(f"✅ Шаблон #{template_id} успешно обновлён!\nВернитесь в приложение 👇", reply_markup=_back_kb())


@router.message(Command("cancel"))
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=_back_kb())