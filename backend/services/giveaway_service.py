"""backend/services/giveaway_service.py"""

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
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import AsyncSessionLocal
from models import Giveaway, PostTemplate, Channel
from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
from repositories.channel_repo import channel_repo
from celery_app import celery

# ── Bot API 9.4: поле style в InlineKeyboardButton ────────────────────────
# Значения: "success" (зеленый), "danger" (красный), "primary" (синий)
BUTTON_STYLE_MAP: dict[str, str | None] = {
    "default": "primary",  
    "green":   "success",
    "red":     "danger",
    "blue":    "primary",
}

_TG_SEMAPHORE = asyncio.Semaphore(20)


def _make_join_button(text: str, url: str, color: str, custom_emoji_id: str | None) -> InlineKeyboardButton:
    """Собирает объект кнопки с поддержкой style и icon_custom_emoji_id (Bot API 9.4)"""
    btn = InlineKeyboardButton(text=text, url=url)
    
    # Инициализируем хранилище скрытых полей Pydantic (взлом Aiogram для передачи новых фич)
    if getattr(btn, "__pydantic_extra__", None) is None:
        btn.__pydantic_extra__ = {}

    style = BUTTON_STYLE_MAP.get(color)
    if style:
        btn.__pydantic_extra__["style"] = style

    if custom_emoji_id:
        btn.__pydantic_extra__["icon_custom_emoji_id"] = custom_emoji_id

    return btn


async def _send_post(bot: Bot, chat_id: int, template: PostTemplate,
                     keyboard: InlineKeyboardMarkup, parse_mode: str = "HTML") -> int | None:
    """Отправляет пост в чат с inline-клавиатурой стандартными методами Aiogram."""
    try:
        if template.media_type == "photo":
            msg = await bot.send_photo(chat_id=chat_id, photo=template.media_id, caption=template.text, reply_markup=keyboard, parse_mode=parse_mode)
        elif template.media_type == "video":
            msg = await bot.send_video(chat_id=chat_id, video=template.media_id, caption=template.text, reply_markup=keyboard, parse_mode=parse_mode)
        elif template.media_type == "animation":
            msg = await bot.send_animation(chat_id=chat_id, animation=template.media_id, caption=template.text, reply_markup=keyboard, parse_mode=parse_mode)
        else:
            msg = await bot.send_message(chat_id=chat_id, text=template.text, reply_markup=keyboard, parse_mode=parse_mode)
        
        return msg.message_id
    except Exception as e:
        logging.error(f"Ошибка _send_post для {chat_id}: {e}")
        return None


async def _check_member_safe(bot: Bot, chat_id: int, user_id: int) -> bool:
    async with _TG_SEMAPHORE:
        for _ in range(3):
            try:
                member = await asyncio.wait_for(
                    bot.get_chat_member(chat_id=chat_id, user_id=user_id), timeout=5.0)
                return member.status not in["left", "kicked", "banned"]
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except asyncio.TimeoutError:
                return True
            except Exception:
                return True
        return True


class GiveawayService:

    # ── Шаг 1: Отправить детали в бот, ждём подтверждения ─────────────────
    async def send_confirmation_to_bot(
        self, db: AsyncSession, bot: Bot, user_id: int, giveaway_id: int
    ) -> None:
        """Отправляет создателю в бот превью поста и кнопки Принять/Отмена"""
        giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
        if not giveaway:
            return

        template = await db.scalar(
            select(PostTemplate).where(PostTemplate.id == giveaway.template_id))
        if not template:
            return

        async def channel_lines(ids: list[int]) -> str:
            if not ids:
                return "  —"
            channels = await channel_repo.get_by_ids(db, ids)
            lines =[]
            for i, ch in enumerate(channels, 1):
                link = f"https://t.me/{ch.username}" if ch.username else f"https://t.me/c/{str(ch.telegram_id).replace('-100','')}/0"
                lines.append(f"{i}. 🎲 {ch.title} ({link})")
            return "\n".join(lines) if lines else "  —"

        sponsor_lines = await channel_lines(giveaway.sponsor_channel_ids)
        publish_lines = await channel_lines(giveaway.publish_channel_ids)
        result_lines  = await channel_lines(giveaway.result_channel_ids)
        boost_lines   = await channel_lines(giveaway.boost_channel_ids or[])

        start_str = "Начнётся сразу" if giveaway.start_immediately else (
            giveaway.start_date.strftime("%d.%m.%Y, %H:%M GMT+3") if giveaway.start_date else "—")
        end_str = giveaway.end_date.strftime("%d.%m.%Y, %H:%M GMT+3") if giveaway.end_date else "—"

        bot_info = await bot.get_me()
        app_short = os.getenv("MINI_APP_SHORT_NAME", "app")
        giveaway_url = f"https://t.me/{bot_info.username}/{app_short}?startapp=gw_{giveaway.id}"

        # 1. Отправляем пост-превью
        join_btn = _make_join_button(
            text=f"{giveaway.button_color_emoji} {giveaway.button_text}".strip(),
            url=giveaway_url,
            color=giveaway.button_color,
            custom_emoji_id=giveaway.button_custom_emoji_id,
        )
        post_keyboard = InlineKeyboardMarkup(inline_keyboard=[[join_btn]])
        post_msg_id = await _send_post(bot, user_id, template, post_keyboard)

        # 2. Текст с деталями
        details = (
            f"👆🏻 Ваш пост 👆🏻\n\n"
            f"ℹ️ <b>Информация о розыгрыше:</b>\n"
            f"📝 Название: {giveaway.title}\n"
            f"⏰ Дата начала: {start_str}\n"
            f"⏰ Дата окончания: {end_str}\n"
            f"🏆 Кол-во победителей: {giveaway.winners_count}\n"
            f"📺 Постинг сторис: {'✅' if giveaway.use_stories else '❌'}\n"
            f"⚡️ Буст каналов: {'✅' if giveaway.use_boosts else '❌'}\n"
            f"👥 Приглашение друзей: {'✅' if giveaway.use_invites else '❌'}\n"
            f"🔢 Макс. приглашений: {giveaway.max_invites}\n"
            f"🔒 Капча: {'✅' if giveaway.use_captcha else '❌'}\n\n"
            f"🗂️ <b>Каналы для подписки:</b>\n{sponsor_lines}\n\n"
            f"🚀 <b>Старт будет опубликован в:</b>\n{publish_lines}\n\n"
            f"🏁 <b>Итоги будут опубликованы в:</b>\n{result_lines}"
        )
        if giveaway.use_boosts and giveaway.boost_channel_ids:
            details += f"\n\n🔍 <b>Каналы для буста:</b>\n{boost_lines}"

        confirm_text = (
            "\n\nВаш розыгрыш готов к запуску! Пожалуйста, проверьте всё ещё раз "
            "и нажмите «Принять», чтобы создать розыгрыш.\n\n"
            "‼️ Права администратора (и для вас, и для бота) в каналах публикации "
            "должны сохраняться до конца розыгрыша!\n\n"
            "⚠️ Розыгрыш будет опубликован в выбранные каналы сразу после подтверждения!"
        )

        # 3. Кнопки подтверждения (с цветами API 9.4)
        btn_confirm = InlineKeyboardButton(text="✅ Принять", callback_data=f"confirm_gw_{giveaway.id}")
        btn_confirm.__pydantic_extra__ = {"style": "success"} # Зеленая

        btn_cancel = InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_gw_{giveaway.id}")
        btn_cancel.__pydantic_extra__ = {"style": "danger"}   # Красная

        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn_confirm, btn_cancel]])

        # Отправляем сообщение-подтверждение (реплаем на превью поста)
        await bot.send_message(
            chat_id=user_id,
            text=details + confirm_text,
            parse_mode="HTML",
            reply_markup=confirm_keyboard,
            reply_to_message_id=post_msg_id if post_msg_id else None
        )

    # ── Публикация в каналы (вызывается после подтверждения) ──────────────
    async def _post_to_channels_task(self, giveaway_id: int):
        logging.info(f"🚀 Публикация розыгрыша #{giveaway_id}")
        bot = Bot(token=os.getenv("BOT_TOKEN"),
                  default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            async with AsyncSessionLocal() as db:
                giveaway = await db.scalar(
                    select(Giveaway).where(Giveaway.id == giveaway_id))
                if not giveaway:
                    return

                template = await db.scalar(
                    select(PostTemplate).where(PostTemplate.id == giveaway.template_id))
                if not template:
                    return

                channels_q = await db.execute(
                    select(Channel).where(Channel.id.in_(giveaway.publish_channel_ids)))
                channels = channels_q.scalars().all()

                bot_info = await bot.get_me()
                app_short = os.getenv("MINI_APP_SHORT_NAME", "app")
                url = f"https://t.me/{bot_info.username}/{app_short}?startapp=gw_{giveaway.id}"

                btn = _make_join_button(
                    text=f"{giveaway.button_color_emoji} {giveaway.button_text}".strip(),
                    url=url,
                    color=giveaway.button_color,
                    custom_emoji_id=giveaway.button_custom_emoji_id,
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn]])

                for ch in channels:
                    try:
                        await _send_post(bot, ch.telegram_id, template, keyboard)
                        logging.info(f"✅ Опубликовано в {ch.title}")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logging.error(f"❌ Ошибка публикации в {ch.title}: {e}")
        finally:
            await bot.session.close()

    # ── Финализация ────────────────────────────────────────────────────────
    async def _finalize_giveaway_task(self, giveaway_id: int):
        logging.info(f"🎲 Финализация #{giveaway_id}")
        bot = Bot(token=os.getenv("BOT_TOKEN"),
                  default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            async with AsyncSessionLocal() as db:
                giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
                if not giveaway or giveaway.status == "completed":
                    return

                giveaway.status = "finalizing"
                await db.commit()

                participants = await participant_repo.get_all_by_giveaway(db, giveaway_id)
                sponsor_channels = await channel_repo.get_by_ids(db, giveaway.sponsor_channel_ids)

                valid = []
                batch_size = 50

                async def check_one(p):
                    if not sponsor_channels:
                        return p, True
                    checks = await asyncio.gather(*[
                        _check_member_safe(bot, ch.telegram_id, p.user_id)
                        for ch in sponsor_channels
                    ])
                    return p, all(checks)

                for i in range(0, len(participants), batch_size):
                    results = await asyncio.gather(*[check_one(p) for p in participants[i:i+batch_size]])
                    for p, ok in results:
                        if ok:
                            valid.append(p)
                        else:
                            p.is_active = False
                            db.add(p)
                    await db.commit()
                    await asyncio.sleep(0.3)

                rng = random.SystemRandom()
                pool = []
                pre_winners = set()

                for p in valid:
                    if p.is_winner:
                        pre_winners.add(p.user_id)
                    else:
                        tickets = 1
                        if p.has_boosted:
                            # макс 10 бустов = макс 10 доп. билетов
                            tickets += min(getattr(p, 'boost_count', 1), 10)
                        tickets += p.invite_count
                        if p.story_clicks > 0:
                            tickets += 1
                        pool.extend([p.user_id] * tickets)

                winners = set(pre_winners)
                while len(winners) < giveaway.winners_count and pool:
                    chosen = rng.choice(pool)
                    winners.add(chosen)
                    pool = [x for x in pool if x != chosen]

                for p in valid:
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
                    text = (f"🎉 <b>Итоги розыгрыша «{giveaway.title}»!</b>\n\n"
                            f"Поздравляем победителей:\n{wt}\n\n"
                            f"<i>Честных участников: {len(valid)}</i>")
                    rcs = await channel_repo.get_by_ids(db, giveaway.result_channel_ids)
                    for ch in rcs:
                        try:
                            await bot.send_message(chat_id=ch.telegram_id, text=text)
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logging.error(f"Итоги в {ch.title}: {e}")
        finally:
            await bot.session.close()

    # ── publish_giveaway — создаёт запись, шлёт в бот, НЕ публикует сразу ─
    async def publish_giveaway(
        self, db: AsyncSession, bot: Bot, user_id: int, data: dict, bg_tasks
    ) -> int:
        if not data.get("start_immediately") and not data.get("start_date"):
            raise HTTPException(status_code=400, detail="Укажите дату начала")

        giveaway = await giveaway_repo.create(db, obj_in_data={
            "creator_id":  user_id,
            "title":       data["title"],
            "template_id": data["template_id"],
            "button_text": data["button_text"],
            "button_color_emoji":    data.get("button_emoji", "🎁"),
            "button_color":          data.get("button_color", "default"),
            "button_custom_emoji_id": data.get("button_custom_emoji_id") or None,
            "sponsor_channel_ids": data["sponsor_channels"],
            "publish_channel_ids": data["publish_channels"],
            "result_channel_ids":  data["result_channels"],
            "boost_channel_ids":   data.get("boost_channels", []),
            "start_immediately":   data["start_immediately"],
            "start_date":          data.get("start_date"),
            "end_date":            data.get("end_date"),
            "winners_count": data["winners_count"],
            "use_boosts":    data["use_boosts"],
            "use_invites":   data["use_invites"],
            "max_invites":   data["max_invites"],
            "use_stories":   data["use_stories"],
            "use_captcha":   data["use_captcha"],
            # Ждём подтверждения от пользователя в боте
            "status": "pending_confirmation",
        })

        # Отправляем детали + кнопки Принять/Отмена в бот (фоново)
        bg_tasks.add_task(self.send_confirmation_to_bot, db, bot, user_id, giveaway.id)

        return giveaway.id

    # ── Подтверждение (вызывается из callback handler бота) ───────────────
    async def confirm_giveaway(self, giveaway_id: int, user_id: int) -> str:
        """Активирует розыгрыш и запускает публикацию. Возвращает title."""
        async with AsyncSessionLocal() as db:
            giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
            if not giveaway or giveaway.creator_id != user_id:
                raise ValueError("Розыгрыш не найден")
            if giveaway.status != "pending_confirmation":
                raise ValueError("Розыгрыш уже обработан")

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

    async def finalize_giveaway(
        self, db: AsyncSession, bot: Bot, giveaway_id: int, user_id: int, bg_tasks
    ):
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
                "end_date":   g.end_date.isoformat()   if g.end_date   else None,
            })
        return result

    async def get_giveaway_status(self, db: AsyncSession, giveaway_id: int) -> dict:
        giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
        if not giveaway:
            raise HTTPException(status_code=404)
        winners = []
        if giveaway.status == "completed":
            wd = await participant_repo.get_winners_with_users(db, giveaway_id)
            winners = [{"name": u.first_name, "username": u.username} for _, u in wd]
        return {"status": giveaway.status, "winners": winners}

    async def draw_additional_winners(
        self, db: AsyncSession, bot: Bot, giveaway_id: int, count: int, user_id: int
    ):
        from models import User
        rng = random.SystemRandom()
        giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
        if not giveaway or giveaway.creator_id != user_id:
            raise HTTPException(status_code=403, detail="Нет прав")
        if giveaway.status != "completed":
            raise HTTPException(status_code=400, detail="Розыгрыш не завершён")

        participants = await participant_repo.get_all_by_giveaway(db, giveaway_id)
        pool, available = [], {}
        for p in participants:
            if p.is_active and not p.is_winner:
                tickets = 1 + (min(getattr(p,'boost_count',1),10) if p.has_boosted else 0) + p.invite_count
                if p.story_clicks > 0: tickets += 1
                pool.extend([p.user_id] * tickets)
                available[p.user_id] = p

        if len(set(pool)) < count:
            raise HTTPException(status_code=400, detail=f"Доступно только {len(set(pool))} участников")

        new_w = set()
        while len(new_w) < count and pool:
            c = rng.choice(pool)
            new_w.add(c)
            pool = [x for x in pool if x != c]

        for wid in new_w:
            available[wid].is_winner = True
            db.add(available[wid])
        giveaway.winners_count += count
        await db.commit()

        users_r = await db.execute(select(User).where(User.telegram_id.in_(list(new_w))))
        wu = users_r.scalars().all()
        wt = "\n".join([f"🏆 {u.first_name}" + (f" (@{u.username})" if u.username else "") for u in wu])

        if giveaway.result_channel_ids:
            chs = await channel_repo.get_by_ids(db, giveaway.result_channel_ids)
            post = f"🎁 <b>Дополнительные победители!</b>\nРозыгрыш «{giveaway.title}»:\n\n{wt}"
            for ch in chs:
                try:
                    await bot.send_message(chat_id=ch.telegram_id, text=post)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logging.error(f"Доп. победители в {ch.title}: {e}")

        return {"status": "success", "drawn_count": len(new_w)}


giveaway_service = GiveawayService()