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

MAX_TEXT  = 4096
MAX_MEDIA = 1024


class PostStates(StatesGroup):
    waiting_for_post = State()


def _back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎲 Вернуться в приложение", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


async def _show_prompt(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_post)
    await message.answer(
        "💬 Отправьте мне текст вашего поста.\n"
        "✨ Вы можете прислать текст с картинкой, видео или GIF.\n\n"
        f"📏 Максимум символов:\n"
        f"• Только текст: <b>{MAX_TEXT:,}</b>\n"
        f"• С медиафайлом: <b>{MAX_MEDIA:,}</b>\n\n"
        "🔥 Бот поддерживает кастомные эмодзи!\n\n"
        "Для отмены 👉 /cancel",
        parse_mode="HTML",
    )


# ── /start add_post — вызывается из Mini App ──────────────────────────────────
# Mini App: openTelegramLink("https://t.me/BOT?start=add_post")
# Telegram → бот получает: /start add_post
# CommandObject.args == "add_post"

@router.message(CommandStart(deep_link=True))
async def start_deep_link_post(message: Message, command: CommandObject, state: FSMContext):
    if command.args == "add_post":
        await _show_prompt(message, state)


# ── Приём поста ───────────────────────────────────────────────────────────────

@router.message(PostStates.waiting_for_post)
async def receive_post(message: Message, state: FSMContext):
    text     = message.html_text or ""
    media_id = None
    media_type = None

    if message.photo:
        media_id   = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_id   = message.video.file_id
        media_type = "video"
    elif message.animation:
        media_id   = message.animation.file_id
        media_type = "animation"

    limit = MAX_MEDIA if media_id else MAX_TEXT
    if len(text) > limit:
        await message.answer(
            f"❌ Текст слишком длинный: <b>{len(text)}</b> симв. (лимит {limit:,}).\n"
            "Сократите и отправьте снова.",
            parse_mode="HTML",
        )
        return

    if not text and not media_id:
        await message.answer("❌ Пришлите текст, фото, видео или GIF.")
        return

    async with AsyncSessionLocal() as db:
        db.add(PostTemplate(
            owner_id=message.from_user.id,
            text=text, media_id=media_id, media_type=media_type,
        ))
        await db.commit()

    await state.clear()
    label = {"photo": "📸 Фото", "video": "🎥 Видео", "animation": "🎞 GIF"}.get(media_type, "📝 Текст")
    await message.answer(
        f"🎉 Пост создан и сохранён!\n{label} · {len(text)} симв.\n\nВернитесь в приложение 👇",
        reply_markup=_back_kb(),
        parse_mode="HTML",
    )


@router.message(Command("cancel"), PostStates.waiting_for_post)
async def cancel_post(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=_back_kb())