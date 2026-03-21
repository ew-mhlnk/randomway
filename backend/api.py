"""backend\api.py"""

@router.post("/bot/request-channel")
async def bot_request_channel(request: Request, user_id: int = Depends(get_user_id)):
    """
    Отправляет инструкцию и вызывает нативный интерфейс добавления бота.
    """
    bot = request.app.state.bot
    dp = request.app.state.dp
    bot_id = request.app.state.bot_id

    # ИМПОРТИРУЕМ НУЖНУЮ КЛАВИАТУРУ ИЗ HANDLERS
    from handlers.channels import ChannelStates, _request_chat_kb

    text = (
        "💬 Пришлите <b>username</b> канала в формате @durov или перешлите сообщение "
        "из канала (например приватного), который вы хотите добавить.\n\n"
        "⚠️ Бот должен быть админом канала с правами на публикацию и редактирование сообщений.\n\n"
        "Для отмены нажмите 👉🏻 /cancel\n\n"
        "🔥 Вы также можете добавить канал с помощью кнопки в меню "
        "(это удобно - бот сам добавится в админы с нужными правами) 👇🏻"
    )

    try:
        # Отправляем сообщение с ReplyKeyboardMarkup (нижние кнопки)
        await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=_request_chat_kb()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось отправить сообщение: {e}")

    # Устанавливаем FSM-состояние
    key = StorageKey(bot_id=bot_id, chat_id=user_id, user_id=user_id)
    await dp.storage.set_state(key=key, state=ChannelStates.waiting_for_channel)

    return {"status": "ok"}