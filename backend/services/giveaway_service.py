import os
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import AsyncSessionLocal
from models import Giveaway, PostTemplate, Channel
from repositories.giveaway_repo import giveaway_repo

class GiveawayService:
    
    # 1. Фоновая задача для рассылки
    async def _post_to_channels_task(self, giveaway_id: int, bot: Bot):
        logging.info(f"🚀 Запуск фоновой публикации для розыгрыша #{giveaway_id}")
        
        async with AsyncSessionLocal() as db:
            giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
            if not giveaway: return
                
            template = await db.scalar(select(PostTemplate).where(PostTemplate.id == giveaway.template_id))
            if not template: return
                
            channels_result = await db.execute(select(Channel).where(Channel.id.in_(giveaway.publish_channel_ids)))
            channels = channels_result.scalars().all()
            
            bot_info = await bot.get_me()
            app_short_name = os.getenv("MINI_APP_SHORT_NAME", "app") 
            giveaway_url = f"https://t.me/{bot_info.username}/{app_short_name}?startapp=gw_{giveaway.id}"
            
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=f"{giveaway.button_color_emoji} {giveaway.button_text}",
                    url=giveaway_url
                )
            ]])
            
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
                    await asyncio.sleep(0.5) # Защита от спама (Rate Limit)
                    
                except Exception as e:
                    logging.error(f"❌ Ошибка публикации в {channel.title}: {e}")


    # 2. Основной метод публикации
    async def publish_giveaway(self, db: AsyncSession, bot: Bot, user_id: int, data: dict, bg_tasks) -> int:
        if not data.get('start_immediately') and not data.get('start_date'):
            raise HTTPException(status_code=400, detail="Укажите дату начала")
        
        # Создаем через репозиторий
        giveaway = await giveaway_repo.create(db, obj_in_data={
            "creator_id": user_id,
            "title": data['title'],
            "template_id": data['template_id'],
            "button_text": data['button_text'],
            "button_color_emoji": data['button_emoji'],
            "sponsor_channel_ids": data['sponsor_channels'],
            "publish_channel_ids": data['publish_channels'],
            "result_channel_ids": data['result_channels'],
            "start_immediately": data['start_immediately'],
            "start_date": data.get('start_date'),
            "end_date": data.get('end_date'),
            "winners_count": data['winners_count'],
            "use_boosts": data['use_boosts'],
            "use_invites": data['use_invites'],
            "max_invites": data['max_invites'],
            "use_stories": data['use_stories'],
            "use_captcha": data['use_captcha'],
            "status": "active" if data['start_immediately'] else "pending"
        })

        if data['start_immediately']:
            bg_tasks.add_task(self._post_to_channels_task, giveaway.id, bot)

        return giveaway.id

giveaway_service = GiveawayService()