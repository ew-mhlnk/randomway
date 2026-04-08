import os
import asyncio
import logging
import random
import aiohttp
import json
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.future import select
from fastapi import HTTPException
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter
from database import AsyncSessionLocal, DATABASE_URL
from models import Giveaway, PostTemplate, Channel, Participant
from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
from repositories.channel_repo import channel_repo
from celery_app import celery

celery_engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)
CelerySessionLocal = async_sessionmaker(bind=celery_engine, expire_on_commit=False)

BUTTON_STYLE_MAP: dict[str, str | None] = {
    "default": None,
    "green": "success",
    "red": "danger",
    "blue": "primary",
}
_TG_SEMAPHORE = asyncio.Semaphore(20)


def _make_join_button(text: str, url: str, color: str, custom_emoji_id: str | None) -> dict:
    btn: dict = {"text": text, "url": url}
    style = BUTTON_STYLE_MAP.get(color)
    if style:
        btn["style"] = style
    if custom_emoji_id:
        btn["icon_custom_emoji_id"] = custom_emoji_id
    return btn


async def _send_post(bot: Bot, chat_id: int, template: PostTemplate, keyboard: dict) -> int | None:
    params: dict = {"chat_id": chat_id, "reply_markup": keyboard, "parse_mode": "HTML"}
    if template.media_type == "photo":
        method = "sendPhoto"
        params["photo"] = template.media_id
        params["caption"] = template.text
    elif template.media_type == "video":
        method = "sendVideo"
        params["video"] = template.media_id
        params["caption"] = template.text
    elif template.media_type == "animation":
        method = "sendAnimation"
        params["animation"] = template.media_id
        params["caption"] = template.text
    else:
        method = "sendMessage"
        params["text"] = template.text

    # Логируем клавиатуру, чтобы убедиться, что icon_custom_emoji_id не теряется
    logging.info(f"Sending to {chat_id}, method: {method}, keyboard: {json.dumps(keyboard)}")

    url = f"https://api.telegram.org/bot{bot.token}/{method}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"].get("message_id")
                else:
                    logging.error(f"Telegram API Error: {data}")
                    return None
    except Exception as e:
        logging.error(f"Request error: {e}")
        return None


async def _check_member_safe(bot: Bot, chat_id: int, user_id: int) -> bool:
    async with _TG_SEMAPHORE:
        for _ in range(3):
            try:
                m = await asyncio.wait_for(
                    bot.get_chat_member(chat_id=chat_id, user_id=user_id), timeout=5.0)
                return m.status not in["left", "kicked", "banned"]
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except (asyncio.TimeoutError, Exception):
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
        
        # ИСПРАВЛЕНИЕ: Избегаем конфликта встроенного эмодзи и кастомного
        button_text = giveaway.button_text if giveaway.button_custom_emoji_id else f"{giveaway.button_color_emoji}{giveaway.button_text}"
        join_btn = _make_join_button(
            text=button_text,
            url=url, color=giveaway.button_color, custom_emoji_id=giveaway.button_custom_emoji_id,
        )

        post_msg_id = await _send_post(bot, user_id, template, {"inline_keyboard": [[join_btn]]})
        details = (
            f"👀 <b>Ваш пост</b> 👆\n\n"
            f"📋 <b>Информация:</b>\n"
            f"🏷 Название: {giveaway.title}\n"
            f"⏰ Старт: {start_str} | 🏆 Призов: {giveaway.winners_count}\n"
            f"📌 <b>Спонсоры:</b>\n{sponsor_lines}\n📢 <b>Публикация:</b>\n{publish_lines}\n📊 <b>Итоги:</b>\n{result_lines}"
        )
        confirm_keyboard = {"inline_keyboard": [[{"text": "✅ Принять", "callback_data": f"confirm_gw_{giveaway.id}"},
             {"text": "❌ Отмена", "callback_data": f"cancel_gw_{giveaway.id}"}]
        ]}
        rp = {"reply_to_message_id": post_msg_id} if post_msg_id else {}
        params = {"chat_id": user_id, "text": details, "parse_mode": "HTML", "reply_markup": confirm_keyboard, **rp}
        
        async with aiohttp.ClientSession() as session:
            await session.post(f"https://api.telegram.org/bot{bot.token}/sendMessage", json=params)

    async def _post_to_channels_task(self, giveaway_id: int):
        async with Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
            async with CelerySessionLocal() as db:
                giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
                template = await db.scalar(select(PostTemplate).where(PostTemplate.id == giveaway.template_id))
                if not giveaway or not template: return
                channels = (await db.execute(select(Channel).where(Channel.id.in_(giveaway.publish_channel_ids)))).scalars().all()
                bot_info = await bot.get_me()
                
                url = f"https://t.me/{bot_info.username}/{os.getenv('MINI_APP_SHORT_NAME', 'app')}?startapp=gw_{giveaway.id}"
                
                # ИСПРАВЛЕНИЕ: Избегаем конфликта встроенного эмодзи и кастомного
                button_text = giveaway.button_text if giveaway.button_custom_emoji_id else f"{giveaway.button_color_emoji}{giveaway.button_text}"
                btn = _make_join_button(
                    text=button_text,
                    url=url, color=giveaway.button_color,
                    custom_emoji_id=giveaway.button_custom_emoji_id,
                )

                for ch in channels:
                    try:
                        msg_id = await _send_post(bot, ch.telegram_id, template, {"inline_keyboard": [[btn]]})
                        if msg_id and not giveaway.post_message_id:
                            giveaway.post_message_id = msg_id
                            giveaway.post_channel_id = ch.telegram_id
                            await db.commit()
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logging.error(f"Publish error {ch.title}: {e}")

    async def _finalize_giveaway_task(self, giveaway_id: int):
        async with Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
            async with CelerySessionLocal() as db:
                giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
                if not giveaway or giveaway.status == "completed": return
                giveaway.status = "finalizing"
                await db.commit()
                participants = await participant_repo.get_all_by_giveaway(db, giveaway_id)
                sponsor_channels = await channel_repo.get_by_ids(db, giveaway.sponsor_channel_ids)
                pool_ids, p_map, pre_winners =[], {}, set()
                
                for p in participants:
                    p_map[p.user_id] = p
                    if p.is_winner: pre_winners.add(p.user_id)
                    elif p.is_active:
                        weight = 1 + min(getattr(p, 'boost_count', 0), 10) + p.invite_count
                        pool_ids.extend([p.user_id] * weight)
                        
                winners = set(pre_winners)
                need = giveaway.winners_count - len(winners)
                
                if need > 0 and pool_ids:
                    rng = random.SystemRandom()
                    unique_pool = list(set(pool_ids))
                    rng.shuffle(unique_pool)
                    candidates = unique_pool[:min(need * 3, len(unique_pool))]
                    if sponsor_channels:
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
                        remaining =[u for u in unique_pool if u not in winners and u not in candidates]
                        while len(winners) < giveaway.winners_count and remaining:
                            w = rng.choice(remaining)
                            winners.add(w)
                            remaining =[x for x in remaining if x != w]
                    else:
                        while len(winners) < giveaway.winners_count and pool_ids:
                            c = rng.choice(pool_ids)
                            winners.add(c)
                            pool_ids = [x for x in pool_ids if x != c]
                            
                for p in participants:
                    p.is_winner = p.user_id in winners
                    db.add(p)
                giveaway.status = "completed"
                await db.commit()
                
                if giveaway.result_channel_ids:
                    wd = await participant_repo.get_winners_with_users(db, giveaway_id)
                    bot_info = await bot.get_me()
                    winners_lines =[]
                    for i, (p, u) in enumerate(wd, 1):
                        if u.username:
                            name_link = f'<a href="https://t.me/{u.username}">{u.first_name}</a>'
                        else:
                            name_link = f'<a href="tg://user?id={u.telegram_id}">{u.first_name}</a>'
                        winners_lines.append(f"{i}. {name_link}")
                        
                    winners_text = "\n".join(winners_lines)
                    check_url = f"https://t.me/{bot_info.username}?start=checklot{giveaway_id}"
                    text = (
                        f'🎉 Результаты розыгрыша "<b>{giveaway.title}</b>":\n\n'
                        f'🏆 Победители:\n{winners_text}\n\n'
                        f'<a href="{check_url}">✔️ Проверить результаты</a>'
                    )
                    result_channels = await channel_repo.get_by_ids(db, giveaway.result_channel_ids)
                    for ch in result_channels:
                        params: dict = {
                            "chat_id": ch.telegram_id,
                            "text": text,
                            "parse_mode": "HTML",
                            "disable_web_page_preview": True,
                        }
                        if (giveaway.post_channel_id == ch.telegram_id
                                and giveaway.post_message_id):
                            params["reply_to_message_id"] = giveaway.post_message_id
                        async with aiohttp.ClientSession() as session:
                            await session.post(
                                f"https://api.telegram.org/bot{bot.token}/sendMessage",
                                json=params
                            )

    async def publish_giveaway(self, db: AsyncSession, bot: Bot, user_id: int, data: dict, bg_tasks) -> int:
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

    async def confirm_giveaway(self, giveaway_id: int, user_id: int) -> str:
        async with AsyncSessionLocal() as db:
            giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
            if not giveaway or giveaway.creator_id != user_id:
                raise ValueError("Розыгрыш не найден")
            giveaway.status = "active" if giveaway.start_immediately else "pending"
            await db.commit()
            if giveaway.start_immediately:
                celery.send_task("tasks.giveaway_tasks.task_publish_giveaway", args=[giveaway_id])
            return giveaway.title

    async def cancel_giveaway_confirmation(self, giveaway_id: int, user_id: int) -> str:
        async with AsyncSessionLocal() as db:
            giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
            giveaway.status = "cancelled"
            await db.commit()
            return giveaway.title

    async def finalize_giveaway(self, db: AsyncSession, bot: Bot, giveaway_id: int, user_id: int, bg_tasks):
        giveaway = await giveaway_repo.get_active_by_id(db, giveaway_id)
        giveaway.status = "finalizing"
        await db.commit()
        celery.send_task("tasks.giveaway_tasks.task_finalize_giveaway", args=[giveaway_id])
        return {"status": "processing"}

    async def get_creator_giveaways(self, db: AsyncSession, user_id: int) -> list[dict]:
        giveaways = await giveaway_repo.get_all_by_creator(db, user_id)
        result =[]
        for g in giveaways:
            p_count = await participant_repo.count_by_giveaway(db, g.id)
            result.append({
                "id": g.id, "title": g.title, "status": g.status,
                "participants_count": p_count, "winners_count": g.winners_count,
                "start_date": g.start_date.isoformat() if g.start_date else None,
                "end_date": g.end_date.isoformat() if g.end_date else None,
            })
        return result

    async def get_giveaway_status(self, db: AsyncSession, giveaway_id: int) -> dict:
        g = await giveaway_repo.get_by_id(db, giveaway_id)
        if not g: raise HTTPException(status_code=404)
        winners =[]
        if g.status == "completed":
            wd = await participant_repo.get_winners_with_users(db, giveaway_id)
            winners =[{"name": u.first_name, "username": u.username} for _, u in wd]
        return {"status": g.status, "winners": winners}

    async def draw_additional_winners(self, db: AsyncSession, bot: Bot, giveaway_id: int, count: int, user_id: int):
        from models import User
        rng = random.SystemRandom()
        g = await giveaway_repo.get_by_id(db, giveaway_id)
        if g.status != "completed": raise HTTPException(status_code=400)
        
        parts = await participant_repo.get_all_by_giveaway(db, giveaway_id)
        pool, avail =[], {}
        for p in parts:
            if p.is_active and not p.is_winner:
                pool.extend([p.user_id] * (1 + p.invite_count))
                avail[p.user_id] = p
                
        nw = set()
        while len(nw) < count and pool:
            c = rng.choice(pool)
            nw.add(c)
            pool = [x for x in pool if x != c]
            
        for wid in nw:
            avail[wid].is_winner = True
            db.add(avail[wid])
            
        g.winners_count += count
        await db.commit()
        
        ur = await db.execute(select(User).where(User.telegram_id.in_(list(nw))))
        wu = ur.scalars().all()
        wt = "\n".join([f"🏆 {u.first_name}" for u in wu])
        
        if g.result_channel_ids:
            chs = await channel_repo.get_by_ids(db, g.result_channel_ids)
            post = f"🎉 <b>Дополнительные победители!</b>\nРозыгрыш «{g.title}»:\n\n{wt}"
            for ch in chs:
                await bot.send_message(chat_id=ch.telegram_id, text=post)
                
        return {"status": "success", "drawn_count": len(nw)}

giveaway_service = GiveawayService()