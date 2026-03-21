import os

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import AsyncSessionLocal
from models import PostTemplate

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")

MAX_TEXT = 4096
MAX_MEDIA = 1024


class PostStates(StatesGroup):
    waiting_for_post = State()


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


# ── 1. Ловим команду /newpost ИЛИ диплинк из Mini App ───────────────────────

@router.message(Command("newpost"))
@router.message(CommandStart(deep_link=True, magic=F.args == "newpost"))
async def cmd_new_post(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_post)
    await message.answer(
        "💬 Отправьте мне текст вашего поста\n\n"
        f"✨ Вы можете прислать текст с картинкой или видео, максимум символов без медиа: {MAX_TEXT}, c медиа: {MAX_MEDIA}.\n\n"
        "🔥 Бот поддерживает кастомные эмодзи!\n\n"
        "Для отмены нажмите 👉🏻 /cancel"
    )


# ── 2. Приём медиа/текста ───────────────────────────────────────────────────

@router.message(PostStates.waiting_for_post)
async def receive_post_content(message: Message, state: FSMContext):
    text = message.html_text or ""
    media_id = None
    media_type = None

    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"
    elif message.animation:
        media_id = message.animation.file_id
        media_type = "animation"

    limit = MAX_MEDIA if media_id else MAX_TEXT
    if len(text) > limit:
        await message.answer(f"❌ Текст слишком длинный: <b>{len(text)}</b> симв. (Лимит: {limit})\nСократите и отправьте снова.")
        return

    if not text and not media_id:
        await message.answer("❌ Пришлите текст, фото, видео или GIF.")
        return

    async with AsyncSessionLocal() as db:
        db.add(PostTemplate(
            owner_id=message.from_user.id,
            text=text,
            media_id=media_id,
            media_type=media_type,
        ))
        await db.commit()

    await state.clear()
    label = {"photo": "📸 Фото", "video": "🎥 Видео", "animation": "🎞 GIF"}.get(media_type, "📝 Текст")
    
    await message.answer(
        f"✅ Пост успешно сохранён!\n\n"
        f"{label} · {len(text)} симв.\n\n"
        "Вернитесь в приложение 👇",
        reply_markup=_back_kb()
    )


@router.message(Command("cancel"), PostStates.waiting_for_post)
async def cancel_post(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Создание поста отменено.", reply_markup=_back_kb())