import os
import asyncio
import logging
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import AsyncSessionLocal
from models import Giveaway, PostTemplate, Channel
from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
from repositories.channel_repo import channel_repo

# Импортируем сам Celery (без задач!), чтобы отправлять команды
from celery_app import celery

class GiveawayService:
    
    async def _post_to_channels_task(self, giveaway_id: int):
        logging.info(f"🚀 Фоновая публикация розыгрыша #{giveaway_id}")
        # Бот создается заново внутри воркера
        bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
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
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logging.error(f"❌ Ошибка публикации в {channel.title}: {e}")
        finally:
            await bot.session.close()

    async def _finalize_giveaway_task(self, giveaway_id: int):
        logging.info(f"🎲 Подведение итогов розыгрыша #{giveaway_id}")
        bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            async with AsyncSessionLocal() as db:
                # 🚀 ИСПРАВЛЕНО: ищем по ID без проверки на 'active', так как статус уже 'finalizing'
                giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
                if not giveaway: return
                
                giveaway.status = "finalizing"
                await db.commit()

                participants = await participant_repo.get_all_by_giveaway(db, giveaway_id)
                sponsor_channels = await channel_repo.get_by_ids(db, giveaway.sponsor_channel_ids)
                
                valid_participants =[]
                batch_size = 25
                
                for i in range(0, len(participants), batch_size):
                    batch = participants[i:i+batch_size]
                    for p in batch:
                        is_honest = True
                        for ch in sponsor_channels:
                            try:
                                member = await bot.get_chat_member(chat_id=ch.telegram_id, user_id=p.user_id)
                                if member.status in["left", "kicked", "banned"]:
                                    is_honest = False
                                    break
                            except Exception:
                                pass
                                
                        if is_honest:
                            valid_participants.append(p)
                        else:
                            p.is_active = False 
                            db.add(p)
                    
                    await db.commit()
                    await asyncio.sleep(1)

                pool =[]
                for p in valid_participants:
                    tickets = 1
                    if p.has_boosted: tickets += 1
                    tickets += p.invite_count
                    pool.extend([p.user_id] * tickets)
                    
                winners_ids = set()
                while len(winners_ids) < giveaway.winners_count and pool:
                    chosen_id = random.choice(pool)
                    winners_ids.add(chosen_id)
                    pool = [x for x in pool if x != chosen_id]

                for p in valid_participants:
                    if p.user_id in winners_ids:
                        p.is_winner = True
                        db.add(p)
                
                giveaway.status = "completed"
                await db.commit()

                if giveaway.result_channel_ids:
                    winners_data = await participant_repo.get_winners_with_users(db, giveaway_id)
                    winners_text = "\n".join([
                        f"🏆 {u.first_name}" + (f" (@{u.username})" if u.username else "") 
                        for p, u in winners_data
                    ])
                    
                    post_text = f"🎉 <b>Итоги розыгрыша «{giveaway.title}» подведены!</b>\n\nПоздравляем победителей:\n{winners_text}\n\n<i>Всего честных участников: {len(valid_participants)}</i>"
                    
                    result_channels = await channel_repo.get_by_ids(db, giveaway.result_channel_ids)
                    for ch in result_channels:
                        try:
                            await bot.send_message(chat_id=ch.telegram_id, text=post_text)
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logging.error(f"Не удалось опубликовать итоги в {ch.title}: {e}")
        finally:
            await bot.session.close()

    async def publish_giveaway(self, db: AsyncSession, bot: Bot, user_id: int, data: dict, bg_tasks) -> int:
        if not data.get('start_immediately') and not data.get('start_date'):
            raise HTTPException(status_code=400, detail="Укажите дату начала")
        
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
            # 🚀 CELERY: Отправляем по имени, без импорта самого файла с задачей!
            celery.send_task("tasks.giveaway_tasks.task_publish_giveaway", args=[giveaway.id])

        return giveaway.id

    async def finalize_giveaway(self, db: AsyncSession, bot: Bot, giveaway_id: int, user_id: int, bg_tasks):
        giveaway = await giveaway_repo.get_active_by_id(db, giveaway_id)
        if not giveaway or giveaway.creator_id != user_id:
            raise HTTPException(status_code=400, detail="Розыгрыш не найден или уже завершен")
            
        giveaway.status = "finalizing"
        await db.commit()
        
        # 🚀 CELERY: Отправляем задачу в фон
        celery.send_task("tasks.giveaway_tasks.task_finalize_giveaway", args=[giveaway_id])
        return {"status": "processing"}

    async def get_creator_giveaways(self, db: AsyncSession, user_id: int) -> list[dict]:
        giveaways = await giveaway_repo.get_all_by_creator(db, user_id)
        result =[]
        for g in giveaways:
            p_count = await participant_repo.count_by_giveaway(db, g.id)
            result.append({
                "id": g.id,
                "title": g.title,
                "status": g.status,
                "participants_count": p_count,
                "winners_count": g.winners_count,
                "start_date": g.start_date.isoformat() if g.start_date else None,
                "end_date": g.end_date.isoformat() if g.end_date else None,
            })
        return result

    async def get_giveaway_status(self, db: AsyncSession, giveaway_id: int) -> dict:
        giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
        if not giveaway: raise HTTPException(status_code=404)
        
        winners =[]
        if giveaway.status == "completed":
            winners_data = await participant_repo.get_winners_with_users(db, giveaway_id)
            winners =[{"name": u.first_name, "username": u.username} for p, u in winners_data]
            
        return {
            "status": giveaway.status,
            "winners": winners
        }

    async def draw_additional_winners(self, db: AsyncSession, bot: Bot, giveaway_id: int, count: int, user_id: int):
        import random
        from models import User
        
        # Используем криптографически безопасный генератор (Enterprise standard)
        secure_random = random.SystemRandom()

        # 1. Проверяем права создателя
        giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
        if not giveaway or giveaway.creator_id != user_id:
            raise HTTPException(status_code=403, detail="Нет прав или розыгрыш не найден")

        if giveaway.status != "completed":
            raise HTTPException(status_code=400, detail="Розыгрыш еще не завершен")

        # 2. Получаем всех честных участников, которые ЕЩЕ НЕ выиграли
        participants = await participant_repo.get_all_by_giveaway(db, giveaway_id)
        
        pool =[]
        available_participants = {}

        for p in participants:
            if p.is_active and not p.is_winner:
                # Считаем билеты с учетом бустов и приглашений
                tickets = 1
                if p.has_boosted: tickets += 1
                tickets += p.invite_count
                
                pool.extend([p.user_id] * tickets)
                available_participants[p.user_id] = p

        # 3. Проверяем, хватает ли уникальных людей
        unique_available_users = set(pool)
        if len(unique_available_users) < count:
            raise HTTPException(
                status_code=400, 
                detail=f"Недостаточно новых участников. Доступно: {len(unique_available_users)}"
            )

        # 4. Крутим рулетку
        new_winners_ids = set()
        while len(new_winners_ids) < count and pool:
            chosen_id = secure_random.choice(pool)
            new_winners_ids.add(chosen_id)
            # Удаляем все билеты этого юзера, чтобы он не выиграл дважды
            pool =[x for x in pool if x != chosen_id]

        # 5. Обновляем флаги в БД
        new_winners_list = []
        for wid in new_winners_ids:
            p = available_participants[wid]
            p.is_winner = True
            db.add(p)
            new_winners_list.append(wid)

        giveaway.winners_count += count # Увеличиваем общее число победителей в статистике
        await db.commit()

        # 6. Получаем юзернеймы новых победителей для поста
        users_result = await db.execute(select(User).where(User.telegram_id.in_(new_winners_list)))
        new_winner_users = users_result.scalars().all()

        winners_text = "\n".join([
            f"🏆 {u.first_name}" + (f" (@{u.username})" if u.username else "") 
            for u in new_winner_users
        ])

        post_text = (
            f"🎁 <b>Дополнительные победители!</b>\n"
            f"В розыгрыше «{giveaway.title}» выбраны новые счастливчики:\n\n"
            f"{winners_text}"
        )

        # 7. Рассылаем в каналы итогов
        if giveaway.result_channel_ids:
            channels = await channel_repo.get_by_ids(db, giveaway.result_channel_ids)
            for ch in channels:
                try:
                    await bot.send_message(chat_id=ch.telegram_id, text=post_text)
                    await asyncio.sleep(0.5) # Защита от Rate Limit Telegram
                except Exception as e:
                    logging.error(f"Ошибка публикации доп. победителей в {ch.title}: {e}")

        return {"status": "success", "drawn_count": len(new_winners_ids)}

giveaway_service = GiveawayService()