import os

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import AsyncSessionLocal
from models import PostTemplate

router = Router()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")

MAX_TEXT_ONLY = 4096
MAX_WITH_MEDIA = 1024


class PostStates(StatesGroup):
    waiting_for_post = State()


def _mini_app_kb(text: str = "🎲 Открыть приложение") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


async def _show_post_prompt(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_post)
    await message.answer(
        "💬 <b>Создание шаблона поста</b>\n\n"
        "Отправьте текст вашего поста.\n"
        "✨ Можно прислать текст с картинкой, видео или GIF.\n\n"
        f"📏 Максимум символов:\n"
        f"• Только текст: <b>{MAX_TEXT_ONLY}</b>\n"
        f"• С медиафайлом: <b>{MAX_WITH_MEDIA}</b>\n\n"
        "🔥 Бот поддерживает кастомные эмодзи!\n\n"
        "Для отмены 👉🏻 /cancel",
        parse_mode="HTML",
    )


# ── /newpost — прямая команда (работает на мобильном без deep link) ───────────

@router.message(Command("newpost"))
async def cmd_newpost(message: Message, state: FSMContext):
    await _show_post_prompt(message, state)


# ── ?start=add_post — deep link из Mini App ───────────────────────────────────
# Используем F.text фильтр чтобы НЕ конфликтовать с channels.py

@router.message(CommandStart(deep_link=True), F.text.endswith("add_post"))
async def deep_add_post(message: Message, state: FSMContext):
    await _show_post_prompt(message, state)


# ── Приём поста ───────────────────────────────────────────────────────────────

@router.message(PostStates.waiting_for_post)
async def process_post(message: Message, state: FSMContext):
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

    max_len = MAX_WITH_MEDIA if media_id else MAX_TEXT_ONLY
    if len(text) > max_len:
        await message.answer(
            f"❌ Текст слишком длинный: <b>{len(text)}</b> символов.\n"
            f"Максимум {'с медиа' if media_id else 'без медиа'}: <b>{max_len}</b>.\n\n"
            "Сократите и отправьте снова.",
            parse_mode="HTML",
        )
        return

    if not text and not media_id:
        await message.answer("❌ Отправьте текст, фото, видео или GIF.")
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

    media_label = {"photo": "📸 Фото", "video": "🎥 Видео", "animation": "🎞 GIF"}.get(
        media_type, "📝 Текст"
    )
    await message.answer(
        f"🎉 Пост создан и сохранён!\n\n"
        f"{media_label} · {len(text)} символов\n\n"
        "Вернитесь в приложение 👇",
        reply_markup=_mini_app_kb("🎲 Вернуться к розыгрышу"),
        parse_mode="HTML",
    )


# ── /cancel ───────────────────────────────────────────────────────────────────

@router.message(Command("cancel"), PostStates.waiting_for_post)
async def cancel_post(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Создание поста отменено.", reply_markup=_mini_app_kb())