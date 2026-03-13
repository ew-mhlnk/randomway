import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎲 Открыть RandomWay",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )]
    ])
    await message.answer(
        "👋 Привет! Я <b>RandomWay</b> — бот для честных розыгрышей.\n\n"
        "🎯 Организуй розыгрыш за пару минут\n"
        "🔗 Реф-ссылки для друзей\n"
        "⚡️ Автоматический выбор победителей\n\n"
        "Нажми кнопку ниже чтобы начать 👇",
        reply_markup=keyboard
    )

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
