"""backend/services/giveaway_service.py"""
import os
import asyncio
import logging
import random
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.future import select
from fastapi import HTTPException
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter

from database import AsyncSessionLocal, DATABASE_URL
from models import Giveaway, PostTemplate, Channel
from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
from repositories.channel_repo import channel_repo

BUTTON_STYLE_MAP: dict[str, int | None] = {
    "default": None, "green": 1, "red": 2, "blue": 3,
}
_TG_SEMAPHORE = asyncio.Semaphore(20)

def _make_join_button(text: str, url: str, color: str, custom_emoji_id: str | None) -> dict:
    btn: dict = {"text": text, "url": url}
    style = BUTTON_STYLE_MAP.get(color)
    if style is not None:
        btn["style"] = style
    if custom_emoji_id:
        btn["icon_custom_emoji_id"] = custom_emoji_id
    return btn

async def _send_post(bot: Bot, chat_id: int, template: PostTemplate, keyboard: dict) -> int | None:
    params: dict = {"chat_id": chat_id, "reply_markup": keyboard, "parse_mode": "HTML"}
    if template.media_type == "photo":
        method, params["photo"] = "sendPhoto", template.media_id
    elif template.media_type == "video":
        method, params["video"] = "sendVideo", template.media_id
    elif template.media_type == "animation":
        method, params["animation"] = "sendAnimation", template.media_id
    else:
        method = "sendMessage"
    
    params["caption" if method != "sendMessage" else "text"] = template.text
    url = f"https://api.telegram.org/bot{bot.token}/{method}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                if data.get("ok"): return data["result"].get("message_id")
                logging.error(f"Telegram API Error: {data}")
    except Exception as e:
        logging.error(f"Request error: {e}")
    return None

async def _check_member_safe(bot: Bot, chat_id: int, user_id: int) -> bool:
    async with _TG_SEMAPHORE:
        for _ in range(3):
            try:
                m = await asyncio.wait_for(bot.get_chat_member(chat_id=chat_id, user_id=user_id), timeout=5.0)
                return m.status not in ["left", "kicked", "banned"]
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except Exception:
                return True
        return True

class GiveawayService:
    async def send_confirmation_to_bot(self, db: AsyncSession, bot: Bot, user_id: int, giveaway_id: int):
        giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
        if not giveaway: return
        template = await db.scalar(select(PostTemplate).where(PostTemplate.id == giveaway.template_id))
        if not template: return

        async def channel_lines(ids: list[int]) -> str:
            if not ids: return "—"
            channels = await channel_repo.get_by_ids(db, ids)
            return "\n".join([f"{i+1}. 📢 {ch.title}" for i, ch in enumerate(channels)]) or "—"

        sponsor_lines = await channel_lines(giveaway.sponsor_channel_ids)
        publish_lines = await channel_lines(giveaway.publish_channel_ids)
        result_lines = await channel_lines(giveaway.result_channel_ids)
        
        start_str = "Сразу" if giveaway.start_immediately else (giveaway.start_date.strftime("%d.%m %H:%M") if giveaway.start_date else "—")
        end_str = giveaway.end_date.strftime("%d.%m %H:%M") if giveaway.end_date else "—"

        bot_info = await bot.get_me()
        url = f"https://t.me/{bot_info.username}/{os.getenv('MINI_APP_SHORT_NAME', 'app')}?startapp=gw_{giveaway.id}"
        join_btn = _make_join_button(
            text=f"{giveaway.button_color_emoji}{giveaway.button_text}",
            url=url, color=giveaway.button_color, custom_emoji_id=giveaway.button_custom_emoji_id,
        )
        post_msg_id = await _send_post(bot, user_id, template, {"inline_keyboard": [[join_btn]]})

        details = (
            f"👀 <b>Ваш пост</b> 👆\n\n"
            f"📋 <b>Информация:</b>\n"
            f"🏷 Название: {giveaway.title}\n⏰ Старт: {start_str} | 🏆 Призов: {giveaway.winners_count}\n"
            f"📌 <b>Спонсоры:</b>\n{sponsor_lines}\n📢 <b>Публикация:</b>\n{publish_lines}\n📊 <b>Итоги:</b>\n{result_lines}"
        )
        
        # БЕЗ параметра style! Из-за него была ошибка 400 Bad Request
        confirm_keyboard = {"inline_keyboard": [
            [{"text": "✅ Принять", "callback_data": f"confirm_gw_{giveaway.id}"},
             {"text": "❌ Отмена", "callback_data": f"cancel_gw_{giveaway.id}"}]
        ]}
        
        rp = {"reply_to_message_id": post_msg_id} if post_msg_id else {}
        params = {"chat_id": user_id, "text": details, "parse_mode": "HTML", "reply_markup": confirm_keyboard, **rp}
        async with aiohttp.ClientSession() as session:
            await session.post(f"https://api.telegram.org/bot{bot.token}/sendMessage", json=params)

    async def _post_to_channels_task(self, giveaway_id: int):
        engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
        SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
        try:
            async with Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
                async with SessionLocal() as db:
                    giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
                    template = await db.scalar(select(PostTemplate).where(PostTemplate.id == giveaway.template_id))
                    if not giveaway or not template: return
                    channels = (await db.execute(select(Channel).where(Channel.id.in_(giveaway.publish_channel_ids)))).scalars().all()
                    
                    bot_info = await bot.get_me()
                    url = f"https://t.me/{bot_info.username}/{os.getenv('MINI_APP_SHORT_NAME', 'app')}?startapp=gw_{giveaway.id}"
                    btn = _make_join_button(
                        text=f"{giveaway.button_color_emoji}{giveaway.button_text}",
                        url=url, color=giveaway.button_color, custom_emoji_id=giveaway.button_custom_emoji_id,
                    )
                    for ch in channels:
                        try:
                            await _send_post(bot, ch.telegram_id, template, {"inline_keyboard": [[btn]]})
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logging.error(f"Publish error {ch.title}: {e}")
        finally:
            await engine.dispose()

    async def _finalize_giveaway_task(self, giveaway_id: int):
        engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
        SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
        try:
            async with Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
                async with SessionLocal() as db:
                    giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
                    if not giveaway or giveaway.status == "completed": return
                    giveaway.status = "finalizing"
                    await db.commit()

                    participants = await participant_repo.get_all_by_giveaway(db, giveaway_id)
                    sponsor_channels = await channel_repo.get_by_ids(db, giveaway.sponsor_channel_ids)

                    pool_ids, p_map, pre_winners = [], {}, set()
                    for p in participants:
                        p_map[p.user_id] = p
                        if p.is_winner: pre_winners.add(p.user_id)
                        elif p.is_active:
                            pool_ids.extend([p.user_id] * (1 + p.invite_count))

                    winners = set(pre_winners)
                    need = giveaway.winners_count - len(winners)

                    if need > 0 and pool_ids:
                        rng = random.SystemRandom()
                        unique_pool = list(set(pool_ids))
                        rng.shuffle(unique_pool)
                        candidates = unique_pool[:min(need * 3, len(unique_pool))]

                        for i in range(0, len(candidates), 20):
                            results = await asyncio.gather(*[
                                asyncio.gather(*[_check_member_safe(bot, ch.telegram_id, uid) for ch in sponsor_channels])
                                for uid in candidates[i:i+20]
                            ])
                            for uid, checks in zip(candidates[i:i+20], results):
                                if all(checks) and len(winners) < giveaway.winners_count:
                                    winners.add(uid)
                                elif not all(checks):
                                    p_map[uid].is_active = False
                                    db.add(p_map[uid])
                            if len(winners) >= giveaway.winners_count: break

                    for p in participants:
                        p.is_winner = p.user_id in winners
                        db.add(p)
                    giveaway.status = "completed"
                    await db.commit()

                    if giveaway.result_channel_ids:
                        wd = await participant_repo.get_winners_with_users(db, giveaway_id)
                        wt = "\n".join([f"🏆 {u.first_name}" for _, u in wd])
                        text = f"🎉 <b>Итоги розыгрыша «{giveaway.title}»!</b>\n\n{wt}"
                        for ch in await channel_repo.get_by_ids(db, giveaway.result_channel_ids):
                            await bot.send_message(chat_id=ch.telegram_id, text=text)
        finally:
            await engine.dispose()

    # Остальные методы оставляем без изменений, они работают от API FastAPI
    async def publish_giveaway(self, db, bot, user_id, data, bg_tasks):
        giveaway = await giveaway_repo.create(db, obj_in_data={
            "creator_id": user_id, "title": data["title"], "template_id": data["template_id"],
            "button_text": data["button_text"], "button_color_emoji": data.get("button_emoji", ""),
            "button_color": data.get("button_color", "default"), "button_custom_emoji_id": data.get("button_custom_emoji_id"),
            "mascot_id": data.get("mascot_id", "1-duck"), "sponsor_channel_ids": data["sponsor_channels"],
            "publish_channel_ids": data["publish_channels"], "result_channel_ids": data["result_channels"],
            "start_immediately": data["start_immediately"], "start_date": data.get("start_date"),
            "end_date": data.get("end_date"), "winners_count": data["winners_count"],
            "use_boosts": data["use_boosts"], "use_invites": data["use_invites"],
            "max_invites": data["max_invites"], "use_captcha": data["use_captcha"],
            "status": "pending_confirmation",
        })
        bg_tasks.add_task(self.send_confirmation_to_bot, db, bot, user_id, giveaway.id)
        return giveaway.id

    async def confirm_giveaway(self, giveaway_id, user_id):
        async with AsyncSessionLocal() as db:
            giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
            giveaway.status = "active" if giveaway.start_immediately else "pending"
            await db.commit()
            if giveaway.start_immediately:
                celery.send_task("tasks.giveaway_tasks.task_publish_giveaway", args=[giveaway_id])
            return giveaway.title

giveaway_service = GiveawayService()