"""backend/handlers/callbacks.py

Обработчик inline-кнопок подтверждения/отмены розыгрыша.
Регистрируется в main.py через dp.include_router(callback_handlers.router)
"""

import logging
from aiogram import Router, Bot
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query(lambda c: c.data and c.data.startswith("confirm_gw_"))
async def on_confirm_giveaway(call: CallbackQuery, bot: Bot):
    giveaway_id = int(call.data.split("confirm_gw_")[1])
    user_id = call.from_user.id

    try:
        from services.giveaway_service import giveaway_service
        title = await giveaway_service.confirm_giveaway(giveaway_id, user_id)

        # Убираем кнопки с исходного сообщения
        await call.message.edit_reply_markup(reply_markup=None)

        await bot.send_message(
            chat_id=user_id,
            text=(
                f'✅ Ваш розыгрыш <b>"{title}"</b> создан!\n\n'
                f"Вы можете управлять им в приложении 👇🏻\n\n"
                f"Для вызова меню нажмите 👉🏻 /start"
            ),
            parse_mode="HTML",
        )
    except ValueError as e:
        await call.answer(str(e), show_alert=True)
    except Exception as e:
        logging.error(f"confirm_giveaway error: {e}")
        await call.answer("Ошибка при подтверждении", show_alert=True)

    await call.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("cancel_gw_"))
async def on_cancel_giveaway(call: CallbackQuery, bot: Bot):
    giveaway_id = int(call.data.split("cancel_gw_")[1])
    user_id = call.from_user.id

    try:
        from services.giveaway_service import giveaway_service
        title = await giveaway_service.cancel_giveaway_confirmation(giveaway_id, user_id)

        await call.message.edit_reply_markup(reply_markup=None)

        await bot.send_message(
            chat_id=user_id,
            text=f'❌ Розыгрыш <b>"{title}"</b> отменён.\n\nВы можете создать новый через приложение.',
            parse_mode="HTML",
        )
    except ValueError as e:
        await call.answer(str(e), show_alert=True)
    except Exception as e:
        logging.error(f"cancel_giveaway error: {e}")
        await call.answer("Ошибка", show_alert=True)

    await call.answer()