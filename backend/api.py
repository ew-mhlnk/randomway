"""backend\api.py"""

from fastapi import APIRouter, HTTPException, Depends, Response, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import urllib.parse
import hashlib
import hmac
import json
import os
import time
import re
import asyncio
from datetime import datetime
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from aiogram.exceptions import TelegramBadRequest
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.storage.base import StorageKey

from database import get_db, AsyncSessionLocal
from models import User, Channel, PostTemplate, Giveaway
from services.giveaway_service import giveaway_service

router = APIRouter()

BOT_TOKEN    = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://randomway.pro/")
security = HTTPBearer()

# ── Auth helpers ──────────────────────────────────────────────────────────────

def validate_telegram_data(init_data: str) -> dict | None:
    parsed_data = dict(urllib.parse.parse_qsl(init_data))
    if "hash" not in parsed_data:
        return None

    hash_val = parsed_data.pop("hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calculated_hash == hash_val:
        auth_date = int(parsed_data.get("auth_date", 0))
        if time.time() - auth_date > 86400:
            return None
        return json.loads(parsed_data.get("user", "{}"))
    return None

def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    user_data = validate_telegram_data(credentials.credentials)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись Telegram")
    return user_data["id"]

def get_user_id_from_query(initData: str) -> int:
    user_data = validate_telegram_data(initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return user_data["id"]

def fmt(count: int | None) -> str:
    if count is None: return "—"
    if count >= 1_000_000: return f"{count/1_000_000:.1f}M"
    if count >= 1_000: return f"{count/1_000:.1f}K"
    return str(count)

def strip_html_tags(text: str) -> str:
    if not text: return ""
    text = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text

# ── Pydantic models ───────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    initData: str

class GiveawayPublishSchema(BaseModel):
    title: str
    template_id: int
    button_text: str
    button_emoji: str
    sponsor_channels: List[int]
    publish_channels: List[int]
    result_channels: List[int]
    start_immediately: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    winners_count: int
    use_boosts: bool
    use_invites: bool
    max_invites: int
    use_stories: bool
    use_captcha: bool

# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/auth")
async def authenticate_user(request: AuthRequest, db: AsyncSession = Depends(get_db)):
    user_data = validate_telegram_data(request.initData)
    if not user_data:
        raise HTTPException(status_code=401, detail="Неверная подпись Telegram")

    stmt = insert(User).values(
        telegram_id=user_data.get("id"),
        first_name=user_data.get("first_name", ""),
        username=user_data.get("username", ""),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["telegram_id"],
        set_=dict(first_name=stmt.excluded.first_name, username=stmt.excluded.username)
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "success", "user": user_data}

# ── Bot triggers ──────────────────────────────────────────────────────────────

@router.post("/bot/request-channel")
async def bot_request_channel(request: Request, user_id: int = Depends(get_user_id)):
    bot = request.app.state.bot
    dp = request.app.state.dp
    from handlers.channels import ChannelStates, _request_chat_kb

    text = (
        "💬 Пришлите <b>username</b> канала в формате @durov или перешлите сообщение...\n\n"
        "Для отмены нажмите 👉🏻 /cancel\n\n"
        "🔥 Вы также можете добавить канал с помощью кнопки в меню 👇🏻"
    )
    try:
        await bot.send_message(chat_id=user_id, text=text, reply_markup=_request_chat_kb())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    await dp.storage.set_state(key=StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id), state=ChannelStates.waiting_for_channel)
    return {"status": "ok"}


@router.post("/bot/request-post")
async def bot_request_post(request: Request, user_id: int = Depends(get_user_id)):
    bot = request.app.state.bot
    dp = request.app.state.dp
    from handlers.posts import PostStates

    text = "💬 Отправьте текст вашего поста.\n✨ Можно прислать текст с картинкой или видео.\nДля отмены — /cancel"
    try:
        await bot.send_message(chat_id=user_id, text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    await dp.storage.set_state(key=StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id), state=PostStates.waiting_for_post)
    return {"status": "ok"}


@router.post("/bot/request-post-edit/{template_id}")
async def bot_request_post_edit(template_id: int, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    bot = request.app.state.bot
    dp = request.app.state.dp
    from handlers.posts import PostStates

    res = await db.execute(select(PostTemplate).where(PostTemplate.id == template_id, PostTemplate.owner_id == user_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Пост не найден")

    try:
        await bot.send_message(chat_id=user_id, text=f"✍️ Отправьте новый текст и медиа для Поста #{template_id}.\nДля отмены — /cancel")
    except Exception:
        pass

    key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
    await dp.storage.set_state(key=key, state=PostStates.waiting_for_edit)
    await dp.storage.update_data(key=key, data={"edit_template_id": template_id})
    return {"status": "ok"}

# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/channels")
async def get_channels(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.owner_id == user_id, Channel.is_active == True))
    channels = result.scalars().all()
    return {"channels": [
        {
            "id": ch.id,
            "title": ch.title,
            "username": ch.username,
            "telegram_id": ch.telegram_id,
            "members_count": ch.members_count,
            "members_formatted": fmt(ch.members_count),
            "has_photo": ch.photo_url is not None,
            "photo_url": ch.photo_url,
        } for ch in channels
    ]}

@router.post("/channels/{channel_id}/sync")
async def sync_channel(channel_id: int, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    bot = request.app.state.bot
    result = await db.execute(select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id))
    ch = result.scalar_one_or_none()
    if not ch: raise HTTPException(status_code=404)

    from services.s3_service import upload_tg_avatar_to_s3

    try:
        chat = await bot.get_chat(ch.telegram_id)
        count = await bot.get_chat_member_count(ch.telegram_id)
        photo_id = chat.photo.small_file_id if chat.photo else None

        if photo_id and photo_id != ch.photo_file_id:
            new_url = await upload_tg_avatar_to_s3(photo_id, chat.id)
            if new_url: ch.photo_url = new_url

        ch.title = chat.title
        ch.members_count = count
        ch.photo_file_id = photo_id
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Бот больше не администратор в этом канале")

    return {"status": "success"}

@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, request: Request, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.id == channel_id, Channel.owner_id == user_id))
    ch = result.scalar_one_or_none()
    if not ch: raise HTTPException(status_code=404)

    bot = request.app.state.bot
    try: await bot.leave_chat(ch.telegram_id)
    except: pass

    await db.delete(ch)
    await db.commit()
    return {"status": "success"}

# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates")
async def get_templates(user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PostTemplate).where(PostTemplate.owner_id == user_id))
    templates = result.scalars().all()
    return {"templates": [
        {
            "id": t.id,
            "text": t.text,
            "media_type": t.media_type,
            "button_text": t.button_text,
            "button_color": t.button_color,
            "preview": strip_html_tags(t.text)[:120] + ("..." if len(strip_html_tags(t.text)) > 120 else ""),
        } for t in templates
    ]}

@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, user_id: int = Depends(get_user_id), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PostTemplate).where(PostTemplate.id == template_id, PostTemplate.owner_id == user_id))
    t = result.scalar_one_or_none()
    if not t: raise HTTPException(status_code=404)
    await db.delete(t)
    await db.commit()
    return {"status": "success"}

# =====================================================================
# ФОНОВАЯ ЗАДАЧА ДЛЯ РАССЫЛКИ ПОСТОВ
# =====================================================================
async def post_to_channels_background_task(giveaway_id: int, bot: Bot):
    """Рассылает пост по каналам в фоновом режиме (чтобы не блокировать ответ юзеру)"""
    import logging
    logging.info(f"🚀 Запуск фоновой публикации для розыгрыша #{giveaway_id}")
    
    # Так как задача фоновая, текущая сессия БД (Depends(get_db)) уже закрыта. 
    # Создаем новую независимую сессию!
    async with AsyncSessionLocal() as db:
        # 1. Получаем сам розыгрыш
        giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
        if not giveaway: return
            
        # 2. Получаем шаблон поста
        template = await db.scalar(select(PostTemplate).where(PostTemplate.id == giveaway.template_id))
        if not template: return
            
        # 3. Получаем реальные каналы из базы (чтобы узнать их telegram_id)
        # giveaway.publish_channel_ids - это массив наших внутренних ID [1, 5, 8]
        channels_result = await db.execute(
            select(Channel).where(Channel.id.in_(giveaway.publish_channel_ids))
        )
        channels = channels_result.scalars().all()
        
        # 4. Формируем кнопку-ссылку для участия (ОТКРЫВАЕТ MINI APP)
        bot_info = await bot.get_me()
        
        # Название твоего Mini App (Short Name), которое ты задавала в BotFather.
        # Если у тебя ссылка вида https://t.me/RandomWayBot/app, то short_name = "app"
        app_short_name = os.getenv("MINI_APP_SHORT_NAME", "app") 
        
        # Специальная ссылка, которая откроет Mini App поверх канала и передаст ID розыгрыша (gw_5)
        giveaway_url = f"https://t.me/{bot_info.username}/{app_short_name}?startapp=gw_{giveaway.id}"
        
        # Собираем красивую кнопку (Эмодзи + Текст)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=f"{giveaway.button_color_emoji} {giveaway.button_text}",
                url=giveaway_url
            )
        ]])
        
        # 5. Рассылаем по всем выбранным каналам
        for channel in channels:
            try:
                if template.media_type == "photo":
                    await bot.send_photo(chat_id=channel.telegram_id, photo=template.media_id, caption=template.text, reply_markup=kb)
                elif template.media_type == "video":
                    await bot.send_video(chat_id=channel.telegram_id, video=template.media_id, caption=template.text, reply_markup=kb)
                elif template.media_type == "animation":
                    await bot.send_animation(chat_id=channel.telegram_id, animation=template.media_id, caption=template.text, reply_markup=kb)
                else:
                    await bot.send_message(chat_id=channel.telegram_id, text=template.text, reply_markup=kb)
                
                logging.info(f"✅ Успешно опубликовано в {channel.title}")
                
                # Защита от спама (Telegram API разрешает не более 30 сообщений в секунду)
                await asyncio.sleep(0.5) 
                
            except Exception as e:
                logging.error(f"❌ Ошибка публикации в {channel.title} (ID: {channel.telegram_id}): {e}")
                # TODO: Если ошибка (например, бот удален из админов), можно отправить создателю уведомление


# =====================================================================
# ЭНДПОИНТ ПУБЛИКАЦИИ
# =====================================================================
@router.post("/giveaways/publish")
async def publish_giveaway(
    data: GiveawayPublishSchema, 
    request: Request, # ➕ Добавили request, чтобы получить бота
    bg_tasks: BackgroundTasks,
    user_id: int = Depends(get_user_id),
    db: AsyncSession = Depends(get_db)
):
    try:
        if not data.start_immediately and not data.start_date:
            raise HTTPException(status_code=400, detail="Укажите дату начала")
        
        # 1. Сохраняем в БД
        giveaway = Giveaway(
            creator_id=user_id,
            title=data.title,
            template_id=data.template_id,
            button_text=data.button_text,
            button_color_emoji=data.button_emoji,
            sponsor_channel_ids=data.sponsor_channels,
            publish_channel_ids=data.publish_channels,
            result_channel_ids=data.result_channels,
            start_immediately=data.start_immediately,
            start_date=data.start_date,
            end_date=data.end_date,
            winners_count=data.winners_count,
            use_boosts=data.use_boosts,
            use_invites=data.use_invites,
            max_invites=data.max_invites,
            use_stories=data.use_stories,
            use_captcha=data.use_captcha,
            status="active" if data.start_immediately else "pending"
        )
        
        db.add(giveaway)
        await db.commit()
        await db.refresh(giveaway)

        # 2. Если нужно запустить сразу - кидаем задачу в фон!
        if data.start_immediately:
            bot = request.app.state.bot # Достаем бота из стейта приложения
            # Передаем бота в фоновую задачу
            bg_tasks.add_task(post_to_channels_background_task, giveaway.id, bot)

        # 3. Мгновенно отвечаем фронту "Успех"
        return {"status": "success", "giveaway_id": giveaway.id}
        
    except Exception as e:
        import logging
        logging.error(f"Ошибка создания розыгрыша: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Ошибка при сохранении розыгрыша. Проверьте данные.")