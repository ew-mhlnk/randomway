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
    bot, dp = request.app.state.bot, request.app.state.dp
    from handlers.channels import ChannelStates, _request_chat_kb
    
    text = "💬 Пришлите <b>username</b> канала...\n\nДля отмены нажмите 👉🏻 /cancel\n🔥 Вы также можете добавить канал с помощью кнопки в меню 👇🏻"
    try:
        await bot.send_message(chat_id=user_id, text=text, reply_markup=_request_chat_kb())
        await dp.storage.set_state(key=StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id), state=ChannelStates.waiting_for_channel)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}

@router.post("/bot/request-post")
async def bot_request_post(request: Request, user_id: int = Depends(get_user_id)):
    bot, dp = request.app.state.bot, request.app.state.dp
    from handlers.posts import PostStates
    try:
        await bot.send_message(chat_id=user_id, text="💬 Отправьте текст вашего поста.\n✨ Можно с картинкой.\nОтмена — /cancel")
        await dp.storage.set_state(key=StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id), state=PostStates.waiting_for_post)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}

@router.post("/bot/request-post-edit/{template_id}")
async def bot_request_post_edit(template_id: int, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    bot, dp = request.app.state.bot, request.app.state.dp
    from handlers.posts import PostStates
    
    if not (await db.scalar(select(PostTemplate).where(PostTemplate.id == template_id, PostTemplate.owner_id == user_id))):
        raise HTTPException(status_code=404, detail="Пост не найден")
    try:
        await bot.send_message(chat_id=user_id, text=f"✍️ Отправьте новый текст для Поста #{template_id}.\nОтмена — /cancel")
        key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
        await dp.storage.set_state(key=key, state=PostStates.waiting_for_edit)
        await dp.storage.update_data(key=key, data={"edit_template_id": template_id})
    except Exception: pass
    return {"status": "ok"}