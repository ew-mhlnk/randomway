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

# Лимиты Telegram
MAX_TEXT_ONLY = 4096
MAX_WITH_MEDIA = 1024


class PostStates(StatesGroup):
    waiting_for_post = State()


def _mini_app_kb(text: str = "🎲 Открыть приложение") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


@router.message(Command("cancel"))
async def cancel_post(message: Message, state: FSMContext):
    current = await state.get_state()
    if current == PostStates.waiting_for_post:
        await state.clear()
        await message.answer(
            "❌ Создание поста отменено.",
            reply_markup=_mini_app_kb(),
        )


@router.message(CommandStart(deep_link=True))
async def start_add_post(message: Message, command: CommandObject, state: FSMContext):
    if command.args != "add_post":
        return

    await state.set_state(PostStates.waiting_for_post)
    await message.answer(
        "💬 <b>Создание шаблона поста</b>\n\n"
        "Отправьте текст вашего поста — можно с фото, видео или GIF.\n\n"
        f"📏 Максимум символов:\n"
        f"• Только текст: <b>{MAX_TEXT_ONLY}</b>\n"
        f"• С медиафайлом: <b>{MAX_WITH_MEDIA}</b>\n\n"
        "🔥 Поддерживаются кастомные эмодзи Telegram!\n\n"
        "Для отмены 👉🏻 /cancel",
        parse_mode="HTML",
    )


@router.message(PostStates.waiting_for_post)
async def process_post(message: Message, state: FSMContext):
    text = message.html_text or ""
    media_id = None
    media_type = None

    # Определяем тип медиа
    if message.photo:
        media_id = message.photo[-1].file_id  # берём максимальное разрешение
        media_type = "photo"
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"
    elif message.animation:  # GIF
        media_id = message.animation.file_id
        media_type = "animation"

    # Проверяем лимиты
    max_len = MAX_WITH_MEDIA if media_id else MAX_TEXT_ONLY
    if len(text) > max_len:
        await message.answer(
            f"❌ Текст слишком длинный: <b>{len(text)}</b> символов.\n"
            f"Максимум {'с медиафайлом' if media_id else 'без медиа'}: <b>{max_len}</b>.\n\n"
            "Сократите текст и отправьте снова.",
            parse_mode="HTML",
        )
        return

    if not text and not media_id:
        await message.answer("❌ Отправьте текст, фото, видео или GIF.")
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

    media_label = {
        "photo": "📸 Фото",
        "video": "🎥 Видео",
        "animation": "🎞 GIF",
        None: "📝 Текст",
    }.get(media_type, "📝 Текст")

    await message.answer(
        f"🎉 Пост создан и сохранён!\n\n"
        f"Тип: {media_label}\n"
        f"Символов: <b>{len(text)}</b>\n\n"
        "Вернитесь в приложение чтобы продолжить 👇",
        reply_markup=_mini_app_kb("🎲 Вернуться к розыгрышу"),
        parse_mode="HTML",
    )