import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from aiogram.fsm.storage.base import StorageKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api.dependencies import get_user_id
from database import get_db
from models import PostTemplate

router = APIRouter(tags=["Bot Triggers"])

@router.post("/bot/request-channel")
async def bot_request_channel(request: Request, user_id: int = Depends(get_user_id)):
    # 🚀 ФИКС: Берем жестко заданный bot_id из стейта приложения
    bot, dp, bot_id = request.app.state.bot, request.app.state.dp, request.app.state.bot_id
    from handlers.channels import ChannelStates, _request_chat_kb
    
    text = "💬 Пришлите <b>username</b> канала...\n\nДля отмены нажмите 👉🏻 /cancel\n🔥 Вы также можете добавить канал с помощью кнопки в меню 👇🏻"
    try:
        await bot.send_message(chat_id=user_id, text=text, reply_markup=_request_chat_kb())
        # Теперь бот точно будет ждать твоего ответа!
        await dp.storage.set_state(key=StorageKey(bot_id=bot_id, chat_id=user_id, user_id=user_id), state=ChannelStates.waiting_for_channel)
    except Exception as e:
        logging.error(f"request-channel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}

@router.post("/bot/request-post")
async def bot_request_post(request: Request, user_id: int = Depends(get_user_id)):
    bot, dp, bot_id = request.app.state.bot, request.app.state.dp, request.app.state.bot_id
    from handlers.posts import PostStates
    try:
        await bot.send_message(chat_id=user_id, text="💬 Отправьте текст вашего поста.\n✨ Можно с картинкой.\nОтмена — /cancel")
        await dp.storage.set_state(key=StorageKey(bot_id=bot_id, chat_id=user_id, user_id=user_id), state=PostStates.waiting_for_post)
    except Exception as e:
        logging.error(f"request-post error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}

@router.post("/bot/request-post-edit/{template_id}")
async def bot_request_post_edit(template_id: int, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    bot, dp, bot_id = request.app.state.bot, request.app.state.dp, request.app.state.bot_id
    from handlers.posts import PostStates
    
    template = await db.scalar(select(PostTemplate).where(PostTemplate.id == template_id, PostTemplate.owner_id == user_id))
    if not template:
        raise HTTPException(status_code=404, detail="Пост не найден")
        
    try:
        # 🚀 ФИКС: Присылаем юзеру его старый пост!
        await bot.send_message(chat_id=user_id, text=f"👇 Вот ваш текущий пост #{template_id}. Скопируйте его, измените и отправьте мне заново:")
        
        # Отправляем сам контент
        if template.media_type == "photo":
            await bot.send_photo(chat_id=user_id, photo=template.media_id, caption=template.text)
        elif template.media_type == "video":
            await bot.send_video(chat_id=user_id, video=template.media_id, caption=template.text)
        elif template.media_type == "animation":
            await bot.send_animation(chat_id=user_id, animation=template.media_id, caption=template.text)
        else:
            await bot.send_message(chat_id=user_id, text=template.text)
            
        await bot.send_message(chat_id=user_id, text="✍️ Жду новый вариант (или нажмите /cancel для отмены).")
        
        key = StorageKey(bot_id=bot_id, chat_id=user_id, user_id=user_id)
        await dp.storage.set_state(key=key, state=PostStates.waiting_for_edit)
        await dp.storage.update_data(key=key, data={"edit_template_id": template_id})
    except Exception as e:
        logging.error(f"edit-post error: {e}")
        pass
    return {"status": "ok"}