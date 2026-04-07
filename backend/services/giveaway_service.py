"""backend/services/giveaway_service.py"""
import os
import asyncio
import logging
import random
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter

from database import AsyncSessionLocal
from models import Giveaway, PostTemplate, Channel
from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
from repositories.channel_repo import channel_repo
from celery_app import celery

# Bot API 9.4: style 1=green, 2=red, 3=blue, absent=default
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

    url = f"https://api.telegram.org/bot{bot.token}/{method}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"].get("message_id")
                else:
                    logging.error(f"Telegram API Error in _send_post: {data}")
                    return None
    except Exception as e:
        logging.error(f"Request error in _send_post: {e}")
        return None


async def _check_member_safe(bot: Bot, chat_id: int, user_id: int) -> bool:
    async with _TG_SEMAPHORE:
        for _ in range(3):
            try:
                m = await asyncio.wait_for(
                    bot.get_chat_member(chat_id=chat_id, user_id=user_id), timeout=5.0)
                return m.status not in ["left", "kicked", "banned"]
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except (asyncio.TimeoutError, Exception):
                return True
        return True


class GiveawayService:

    async def send_confirmation_to_bot(self, db: AsyncSession, bot: Bot, user_id: int, giveaway_id: int):
        giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
        if not giveaway:
            return
        template = await db.scalar(select(PostTemplate).where(PostTemplate.id == giveaway.template_id))
        if not template:
            return

        async def channel_lines(ids: list[int]) -> str:
            if not ids:
                return "—"
            channels = await channel_repo.get_by_ids(db, ids)
            return "\n".join([
                f"{i+1}. 📢 {ch.title} ({'https://t.me/'+ch.username if ch.username else 'приватный'})"
                for i, ch in enumerate(channels)
            ]) or "—"

        sponsor_lines = await channel_lines(giveaway.sponsor_channel_ids)
        publish_lines = await channel_lines(giveaway.publish_channel_ids)
        result_lines = await channel_lines(giveaway.result_channel_ids)
        boost_lines = await channel_lines(giveaway.boost_channel_ids or [])

        start_str = "Начнётся сразу" if giveaway.start_immediately else (
            giveaway.start_date.strftime("%d.%m.%Y, %H:%M GMT+3") if giveaway.start_date else "—")
        end_str = giveaway.end_date.strftime("%d.%m.%Y, %H:%M GMT+3") if giveaway.end_date else "—"

        bot_info = await bot.get_me()
        app_short = os.getenv("MINI_APP_SHORT_NAME", "app")
        url = f"https://t.me/{bot_info.username}/{app_short}?startapp=gw_{giveaway.id}"

        join_btn = _make_join_button(
            text=f"{giveaway.button_color_emoji}{giveaway.button_text}",
            url=url, color=giveaway.button_color, custom_emoji_id=giveaway.button_custom_emoji_id,
        )
        post_msg_id = await _send_post(bot, user_id, template, {"inline_keyboard": [[join_btn]]})

        details = (
            f"👀 <b>Ваш пост</b> 👆\n\n"
            f"📋 <b>Информация о розыгрыше:</b>\n"
            f"🏷 Название: {giveaway.title}\n"
            f"⏰ Дата начала: {start_str}\n"
            f"⏰ Дата окончания: {end_str}\n"
            f"🏆 Кол-во победителей: {giveaway.winners_count}\n"
            f"⚡ Буст каналов: {'✅' if giveaway.use_boosts else '❌'}\n"
            f"👥 Приглашение друзей: {'✅' if giveaway.use_invites else '❌'}\n"
            f"👥 Макс. приглашений: {giveaway.max_invites}\n"
            f"🤖 Капча: {'✅' if giveaway.use_captcha else '❌'}\n"
            f"🎭 Маскот: {giveaway.mascot_id}\n\n"
            f"📌 <b>Каналы для подписки:</b>\n{sponsor_lines}\n\n"
            f"📢 <b>Старт будет опубликован в:</b>\n{publish_lines}\n\n"
            f"📊 <b>Итоги будут опубликованы в:</b>\n{result_lines}"
        )
        if giveaway.use_boosts and giveaway.boost_channel_ids:
            details += f"\n\n⚡ <b>Каналы для буста:</b>\n{boost_lines}"

        confirm_text = (
            "\n\nВаш розыгрыш готов к запуску! Проверьте всё ещё раз и нажмите «Принять».\n\n"
            "⚠️ Права администратора должны сохраняться до конца розыгрыша!\n\n"
            "🚀 Розыгрыш будет опубликован сразу после подтверждения!"
        )

        # ВАЖНО: confirm_keyboard БЕЗ поля "style" — оно не работает в sendMessage через aiohttp
        # Style работает только для кнопок KeyboardButton (reply keyboard), не InlineKeyboard
        confirm_keyboard = {"inline_keyboard": [[
            {"text": "✅ Принять", "callback_data": f"confirm_gw_{giveaway.id}"},
            {"text": "❌ Отмена", "callback_data": f"cancel_gw_{giveaway.id}"},
        ]]}

        rp = {"reply_to_message_id": post_msg_id} if post_msg_id else {}
        params = {
            "chat_id": user_id,
            "text": details + confirm_text,
            "parse_mode": "HTML",
            "reply_markup": confirm_keyboard,
            **rp
        }

        tg_url = f"https://api.telegram.org/bot{bot.token}/sendMessage"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(tg_url, json=params) as resp:
                    data = await resp.json()
                    if not data.get("ok"):
                        logging.error(f"send_confirmation_to_bot error: {data}")
        except Exception as e:
            logging.error(f"send_confirmation_to_bot exception: {e}")

    async def _post_to_channels_task(self, giveaway_id: int):
        # ФИКС: используем async with Bot(...) чтобы сессия всегда закрывалась
        async with Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
            async with AsyncSessionLocal() as db:
                giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
                if not giveaway:
                    return
                template = await db.scalar(select(PostTemplate).where(PostTemplate.id == giveaway.template_id))
                if not template:
                    return
                cq = await db.execute(select(Channel).where(Channel.id.in_(giveaway.publish_channel_ids)))
                channels = cq.scalars().all()

                if not channels:
                    logging.warning(f"No publish channels for giveaway {giveaway_id}")
                    return

                bot_info = await bot.get_me()
                url = f"https://t.me/{bot_info.username}/{os.getenv('MINI_APP_SHORT_NAME', 'app')}?startapp=gw_{giveaway.id}"
                btn = _make_join_button(
                    text=f"{giveaway.button_color_emoji}{giveaway.button_text}",
                    url=url, color=giveaway.button_color, custom_emoji_id=giveaway.button_custom_emoji_id,
                )
                for ch in channels:
                    try:
                        msg_id = await _send_post(bot, ch.telegram_id, template, {"inline_keyboard": [[btn]]})
                        if msg_id:
                            logging.info(f"Published to {ch.title} (msg_id={msg_id})")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logging.error(f"Публикация в {ch.title}: {e}")

    async def _finalize_giveaway_task(self, giveaway_id: int):
        # ФИКС: используем async with Bot(...) чтобы сессия всегда закрывалась
        async with Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML)) as bot:
            async with AsyncSessionLocal() as db:
                giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
                if not giveaway or giveaway.status == "completed":
                    return
                giveaway.status = "finalizing"
                await db.commit()

                participants = await participant_repo.get_all_by_giveaway(db, giveaway_id)
                sponsor_channels = await channel_repo.get_by_ids(db, giveaway.sponsor_channel_ids)

                # ФИКС: не проверяем всех, а сначала выбираем кандидатов и проверяем только их
                # Алгоритм: выбираем N*3 случайных кандидатов (с весами), проверяем подписку,
                # из прошедших берём N победителей
                rng = random.SystemRandom()

                # Строим пул с весами
                pool_ids = []
                pre_winners = set()
                participant_map = {}

                for p in participants:
                    participant_map[p.user_id] = p
                    if p.is_winner:
                        pre_winners.add(p.user_id)
                    elif p.is_active:
                        weight = 1 + min(getattr(p, 'boost_count', 0), 10) + p.invite_count
                        pool_ids.extend([p.user_id] * weight)

                winners = set(pre_winners)
                need = giveaway.winners_count - len(winners)

                if need > 0 and pool_ids:
                    # Выбираем кандидатов для проверки: берём need*3 уникальных
                    unique_pool = list(set(pool_ids))
                    rng.shuffle(unique_pool)
                    candidates_to_check = unique_pool[:min(need * 3, len(unique_pool))]

                    # Проверяем подписку только у кандидатов
                    if sponsor_channels:
                        async def check_one(uid):
                            checks = await asyncio.gather(*[
                                _check_member_safe(bot, ch.telegram_id, uid)
                                for ch in sponsor_channels
                            ])
                            return uid, all(checks)

                        for i in range(0, len(candidates_to_check), 20):
                            batch = candidates_to_check[i:i+20]
                            results = await asyncio.gather(*[check_one(uid) for uid in batch])
                            for uid, ok in results:
                                if ok and len(winners) < giveaway.winners_count:
                                    winners.add(uid)
                                elif not ok and uid in participant_map:
                                    participant_map[uid].is_active = False
                                    db.add(participant_map[uid])
                            if len(winners) >= giveaway.winners_count:
                                break
                            await asyncio.sleep(0.3)

                        # Если кандидатов не хватило — добираем из остатка без проверки
                        remaining = [uid for uid in unique_pool if uid not in winners and uid not in set(candidates_to_check)]
                        while len(winners) < giveaway.winners_count and remaining:
                            winner = rng.choice(remaining)
                            winners.add(winner)
                            remaining = [x for x in remaining if x != winner]
                    else:
                        # Нет каналов-спонсоров — просто выбираем случайных
                        while len(winners) < giveaway.winners_count and pool_ids:
                            c = rng.choice(pool_ids)
                            winners.add(c)
                            pool_ids = [x for x in pool_ids if x != c]

                await db.commit()

                # Помечаем победителей
                for p in participants:
                    p.is_winner = p.user_id in winners
                    db.add(p)
                giveaway.status = "completed"
                await db.commit()

                if giveaway.result_channel_ids:
                    wd = await participant_repo.get_winners_with_users(db, giveaway_id)
                    wt = "\n".join([
                        f"🏆 {u.first_name}" + (f" (@{u.username})" if u.username else "")
                        for _, u in wd
                    ])
                    text = f"🎉 <b>Итоги розыгрыша «{giveaway.title}»!</b>\n\n{wt}\n\n<i>Участников прошло проверку: {len(winners)}</i>"
                    for ch in await channel_repo.get_by_ids(db, giveaway.result_channel_ids):
                        try:
                            await bot.send_message(chat_id=ch.telegram_id, text=text)
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logging.error(f"Итоги {ch.title}: {e}")

    async def publish_giveaway(self, db: AsyncSession, bot: Bot, user_id: int, data: dict, bg_tasks) -> int:
        if not data.get("start_immediately") and not data.get("start_date"):
            raise HTTPException(status_code=400, detail="Укажите дату начала")

        giveaway = await giveaway_repo.create(db, obj_in_data={
            "creator_id": user_id,
            "title": data["title"],
            "template_id": data["template_id"],
            "button_text": data["button_text"],
            "button_color_emoji": data.get("button_emoji", "🎉"),
            "button_color": data.get("button_color", "default"),
            "button_custom_emoji_id": data.get("button_custom_emoji_id"),
            "mascot_id": data.get("mascot_id", "1-duck"),
            "sponsor_channel_ids": data["sponsor_channels"],
            "publish_channel_ids": data["publish_channels"],
            "result_channel_ids": data["result_channels"],
            "boost_channel_ids": data.get("boost_channels", []),
            "start_immediately": data["start_immediately"],
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "winners_count": data["winners_count"],
            "use_boosts": data["use_boosts"],
            "use_invites": data["use_invites"],
            "max_invites": data["max_invites"],
            "use_captcha": data["use_captcha"],
            "status": "pending_confirmation",
        })
        bg_tasks.add_task(self.send_confirmation_to_bot, db, bot, user_id, giveaway.id)
        return giveaway.id

    async def confirm_giveaway(self, giveaway_id: int, user_id: int) -> str:
        async with AsyncSessionLocal() as db:
            giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
            if not giveaway or giveaway.creator_id != user_id:
                raise ValueError("Розыгрыш не найден")
            if giveaway.status != "pending_confirmation":
                raise ValueError("Уже обработан")
            giveaway.status = "active" if giveaway.start_immediately else "pending"
            await db.commit()
            if giveaway.start_immediately:
                celery.send_task("tasks.giveaway_tasks.task_publish_giveaway", args=[giveaway_id])
            return giveaway.title

    async def cancel_giveaway_confirmation(self, giveaway_id: int, user_id: int) -> str:
        async with AsyncSessionLocal() as db:
            giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
            if not giveaway or giveaway.creator_id != user_id:
                raise ValueError("Не найдено")
            if giveaway.status != "pending_confirmation":
                raise ValueError("Уже обработан")
            giveaway.status = "cancelled"
            await db.commit()
            return giveaway.title

    async def finalize_giveaway(self, db: AsyncSession, bot: Bot, giveaway_id: int, user_id: int, bg_tasks):
        giveaway = await giveaway_repo.get_active_by_id(db, giveaway_id)
        if not giveaway or giveaway.creator_id != user_id:
            raise HTTPException(status_code=400, detail="Розыгрыш не найден или уже завершён")
        giveaway.status = "finalizing"
        await db.commit()
        celery.send_task("tasks.giveaway_tasks.task_finalize_giveaway", args=[giveaway_id])
        return {"status": "processing"}

    async def get_creator_giveaways(self, db: AsyncSession, user_id: int) -> list[dict]:
        giveaways = await giveaway_repo.get_all_by_creator(db, user_id)
        result = []
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
        if not g:
            raise HTTPException(status_code=404)
        winners = []
        if g.status == "completed":
            wd = await participant_repo.get_winners_with_users(db, giveaway_id)
            winners = [{"name": u.first_name, "username": u.username} for _, u in wd]
        return {"status": g.status, "winners": winners}

    async def draw_additional_winners(self, db: AsyncSession, bot: Bot, giveaway_id: int, count: int, user_id: int):
        from models import User
        rng = random.SystemRandom()
        g = await giveaway_repo.get_by_id(db, giveaway_id)
        if not g or g.creator_id != user_id:
            raise HTTPException(status_code=403, detail="Нет прав")
        if g.status != "completed":
            raise HTTPException(status_code=400, detail="Не завершён")

        parts = await participant_repo.get_all_by_giveaway(db, giveaway_id)
        pool, avail = [], {}
        for p in parts:
            if p.is_active and not p.is_winner:
                weight = 1 + min(getattr(p, 'boost_count', 0), 10) + p.invite_count
                pool.extend([p.user_id] * weight)
                avail[p.user_id] = p

        if len(set(pool)) < count:
            raise HTTPException(status_code=400, detail=f"Доступно {len(set(pool))} участников")

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
        wt = "\n".join([
            f"🏆 {u.first_name}" + (f" (@{u.username})" if u.username else "")
            for u in wu
        ])

        if g.result_channel_ids:
            chs = await channel_repo.get_by_ids(db, g.result_channel_ids)
            post = f"🎉 <b>Дополнительные победители!</b>\nРозыгрыш «{g.title}»:\n\n{wt}"
            for ch in chs:
                try:
                    await bot.send_message(chat_id=ch.telegram_id, text=post)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logging.error(f"Доп. победители {ch.title}: {e}")

        return {"status": "success", "drawn_count": len(nw)}


giveaway_service = GiveawayService()