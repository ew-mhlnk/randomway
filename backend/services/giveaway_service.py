"""backend/services/giveaway_service.py

Ключевые изменения:
- Цвет кнопки передается через поле "style" (Telegram Bot API 9.4).
- Кастомные эмодзи передаются через "icon_custom_emoji_id" в __pydantic_extra__.
- Отказались от сырых bot.session.make_request в пользу стандартных методов aiogram.
- Остальная логика без изменений
"""

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
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database import AsyncSessionLocal
from models import Giveaway, PostTemplate, Channel
from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
from repositories.channel_repo import channel_repo
from celery_app import celery

# ── Маппинг цвета → Telegram Bot API 9.4 (style) ────────────────────────
BUTTON_STYLE_MAP: dict[str, str | None] = {
    "default": "primary",  # Синяя (в интерфейсе мы называли её default)
    "green": "success",    # Зеленая
    "red": "danger",       # Красная
    "purple": "primary",   # Фоллбэк (в API 9.4 пока только 3 цвета, ставим синий)
}

_TG_SEMAPHORE = asyncio.Semaphore(20)


# ── Функция сборки кнопки (Telegram Bot API 9.4) ────────────────────────
def _build_color_button(giveaway: "Giveaway", giveaway_url: str):
    from aiogram.types import InlineKeyboardButton

    btn_text = giveaway.button_text
    custom_emoji_id = getattr(giveaway, "button_custom_emoji_id", None)
    
    # Если премиум-иконки нет, а выбран обычный эмодзи — склеиваем его с текстом
    if not custom_emoji_id:
        emoji = getattr(giveaway, "button_color_emoji", "")
        # Игнорируем плейсхолдер ⭐, если он случайно прилетел со старого фронта
        if emoji and emoji != "⭐": 
            btn_text = f"{emoji} {btn_text}".strip()

    # Создаем базовую кнопку
    btn = InlineKeyboardButton(text=btn_text, url=giveaway_url)

    # Инициализируем хранилище дополнительных полей Pydantic (Aiogram 3.x)
    if getattr(btn, "__pydantic_extra__", None) is None:
        btn.__pydantic_extra__ = {}

    # 1. Применяем стиль (цвет кнопки)
    color_str = getattr(giveaway, "button_color", "default")
    style = BUTTON_STYLE_MAP.get(color_str)
    if style:
        btn.__pydantic_extra__["style"] = style

    # 2. Применяем кастомную иконку Telegram Premium
    if custom_emoji_id:
        btn.__pydantic_extra__["icon_custom_emoji_id"] = custom_emoji_id

    return btn


# ── Обновленный метод отправки ───────────────────────────────────────────
async def _send_giveaway_post(
    bot: Bot,
    chat_id: int,
    template: PostTemplate,
    giveaway: Giveaway,
    giveaway_url: str,
) -> None:
    """Отправляет пост стандартными методами aiogram, но с прокачанной кнопкой"""
    from aiogram.types import InlineKeyboardMarkup
    
    # Собираем клавиатуру с нашей кастомной кнопкой
    kb = InlineKeyboardMarkup(inline_keyboard=[[_build_color_button(giveaway, giveaway_url)]])

    try:
        if template.media_type == "photo":
            await bot.send_photo(chat_id=chat_id, photo=template.media_id, caption=template.text, reply_markup=kb)
        elif template.media_type == "video":
            await bot.send_video(chat_id=chat_id, video=template.media_id, caption=template.text, reply_markup=kb)
        elif template.media_type == "animation":
            await bot.send_animation(chat_id=chat_id, animation=template.media_id, caption=template.text, reply_markup=kb)
        else:
            await bot.send_message(chat_id=chat_id, text=template.text, reply_markup=kb)
    except Exception as e:
        logging.error(f"Ошибка отправки поста в канал {chat_id}: {e}")
        raise


async def _check_member_safe(bot: Bot, chat_id: int, user_id: int) -> bool:
    async with _TG_SEMAPHORE:
        for _ in range(3):
            try:
                member = await asyncio.wait_for(
                    bot.get_chat_member(chat_id=chat_id, user_id=user_id), timeout=5.0
                )
                return member.status not in ["left", "kicked", "banned"]
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except asyncio.TimeoutError:
                return True
            except Exception:
                return True
        return True


class GiveawayService:

    async def _post_to_channels_task(self, giveaway_id: int):
        logging.info(f"🚀 Публикация розыгрыша #{giveaway_id}")
        bot = Bot(
            token=os.getenv("BOT_TOKEN"),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            async with AsyncSessionLocal() as db:
                giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
                if not giveaway:
                    return

                template = await db.scalar(
                    select(PostTemplate).where(PostTemplate.id == giveaway.template_id)
                )
                if not template:
                    return

                channels_result = await db.execute(
                    select(Channel).where(Channel.id.in_(giveaway.publish_channel_ids))
                )
                channels = channels_result.scalars().all()

                bot_info = await bot.get_me()
                app_short_name = os.getenv("MINI_APP_SHORT_NAME", "app")
                giveaway_url = (
                    f"https://t.me/{bot_info.username}/{app_short_name}"
                    f"?startapp=gw_{giveaway.id}"
                )

                for channel in channels:
                    try:
                        # Используем нашу новую функцию
                        await _send_giveaway_post(
                            bot=bot,
                            chat_id=channel.telegram_id,
                            template=template,
                            giveaway=giveaway,
                            giveaway_url=giveaway_url,
                        )
                        logging.info(f"✅ Опубликовано в {channel.title}")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logging.error(f"❌ Ошибка публикации в {channel.title}: {e}")
        finally:
            await bot.session.close()

    async def _finalize_giveaway_task(self, giveaway_id: int):
        logging.info(f"🎲 Финализация розыгрыша #{giveaway_id}")
        bot = Bot(
            token=os.getenv("BOT_TOKEN"),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            async with AsyncSessionLocal() as db:
                giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
                if not giveaway:
                    return

                # Идемпотентность — не финализировать дважды
                if giveaway.status == "completed":
                    logging.info(f"Розыгрыш #{giveaway_id} уже завершён, пропускаем")
                    return

                giveaway.status = "finalizing"
                await db.commit()

                participants = await participant_repo.get_all_by_giveaway(db, giveaway_id)
                sponsor_channels = await channel_repo.get_by_ids(db, giveaway.sponsor_channel_ids)

                valid_participants = []
                batch_size = 50

                async def check_user_channels(p):
                    if not sponsor_channels:
                        return p, True
                    checks = await asyncio.gather(*[
                        _check_member_safe(bot, ch.telegram_id, p.user_id)
                        for ch in sponsor_channels
                    ])
                    return p, all(checks)

                for i in range(0, len(participants), batch_size):
                    batch = participants[i: i + batch_size]
                    results = await asyncio.gather(*[check_user_channels(p) for p in batch])
                    for p, is_honest in results:
                        if is_honest:
                            valid_participants.append(p)
                        else:
                            p.is_active = False
                            db.add(p)
                    await db.commit()
                    await asyncio.sleep(0.5)

                # Рулетка с криптографически безопасным random
                secure_rng = random.SystemRandom()
                pool = []
                pre_selected = set()

                for p in valid_participants:
                    if p.is_winner:
                        pre_selected.add(p.user_id)
                    else:
                        tickets = 1
                        if p.has_boosted:
                            tickets += 1
                        tickets += p.invite_count
                        if getattr(p, "story_clicks", 0) > 0:
                            tickets += 1
                        pool.extend([p.user_id] * tickets)

                winners_ids = set(pre_selected)
                while len(winners_ids) < giveaway.winners_count and pool:
                    chosen = secure_rng.choice(pool)
                    winners_ids.add(chosen)
                    pool = [x for x in pool if x != chosen]

                for p in valid_participants:
                    p.is_winner = p.user_id in winners_ids
                    db.add(p)

                giveaway.status = "completed"
                await db.commit()

                if giveaway.result_channel_ids:
                    winners_data = await participant_repo.get_winners_with_users(db, giveaway_id)
                    winners_text = "\n".join([
                        f"🏆 {u.first_name}" + (f" (@{u.username})" if u.username else "")
                        for _, u in winners_data
                    ])
                    post_text = (
                        f"🎉 <b>Итоги розыгрыша «{giveaway.title}» подведены!</b>\n\n"
                        f"Поздравляем победителей:\n{winners_text}\n\n"
                        f"<i>Честных участников: {len(valid_participants)}</i>"
                    )
                    result_channels = await channel_repo.get_by_ids(db, giveaway.result_channel_ids)
                    for ch in result_channels:
                        try:
                            await bot.send_message(chat_id=ch.telegram_id, text=post_text)
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logging.error(f"Ошибка публикации итогов в {ch.title}: {e}")
        finally:
            await bot.session.close()

    async def publish_giveaway(
        self, db: AsyncSession, bot: Bot, user_id: int, data: dict, bg_tasks
    ) -> int:
        if not data.get("start_immediately") and not data.get("start_date"):
            raise HTTPException(status_code=400, detail="Укажите дату начала")

        giveaway = await giveaway_repo.create(
            db,
            obj_in_data={
                "creator_id": user_id,
                "title": data["title"],
                "template_id": data["template_id"],
                "button_text": data["button_text"],
                "button_color_emoji": data.get("button_emoji", ""),
                "button_color": data.get("button_color", "default"),
                "button_custom_emoji_id": data.get("button_custom_emoji_id") or None,
                "sponsor_channel_ids": data["sponsor_channels"],
                "publish_channel_ids": data["publish_channels"],
                "result_channel_ids": data["result_channels"],
                "start_immediately": data["start_immediately"],
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "winners_count": data["winners_count"],
                "use_boosts": data["use_boosts"],
                "use_invites": data["use_invites"],
                "max_invites": data["max_invites"],
                "use_stories": data["use_stories"],
                "use_captcha": data["use_captcha"],
                "status": "active" if data["start_immediately"] else "pending",
            },
        )

        if data["start_immediately"]:
            celery.send_task(
                "tasks.giveaway_tasks.task_publish_giveaway", args=[giveaway.id]
            )

        return giveaway.id

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
        if not giveaway:
            raise HTTPException(status_code=404)

        winners = []
        if giveaway.status == "completed":
            winners_data = await participant_repo.get_winners_with_users(db, giveaway_id)
            winners = [{"name": u.first_name, "username": u.username} for _, u in winners_data]

        return {"status": giveaway.status, "winners": winners}

    async def draw_additional_winners(
        self, db: AsyncSession, bot: Bot, giveaway_id: int, count: int, user_id: int
    ):
        from models import User

        secure_rng = random.SystemRandom()
        giveaway = await giveaway_repo.get_by_id(db, giveaway_id)
        if not giveaway or giveaway.creator_id != user_id:
            raise HTTPException(status_code=403, detail="Нет прав")
        if giveaway.status != "completed":
            raise HTTPException(status_code=400, detail="Розыгрыш ещё не завершён")

        participants = await participant_repo.get_all_by_giveaway(db, giveaway_id)
        pool = []
        available = {}

        for p in participants:
            if p.is_active and not p.is_winner:
                tickets = 1 + (1 if p.has_boosted else 0) + p.invite_count
                if p.story_clicks > 0:
                    tickets += 1
                pool.extend([p.user_id] * tickets)
                available[p.user_id] = p

        if len(set(pool)) < count:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно участников. Доступно: {len(set(pool))}",
            )

        new_winners = set()
        while len(new_winners) < count and pool:
            chosen = secure_rng.choice(pool)
            new_winners.add(chosen)
            pool = [x for x in pool if x != chosen]

        for wid in new_winners:
            available[wid].is_winner = True
            db.add(available[wid])

        giveaway.winners_count += count
        await db.commit()

        users_result = await db.execute(
            select(User).where(User.telegram_id.in_(list(new_winners)))
        )
        new_winner_users = users_result.scalars().all()
        winners_text = "\n".join([
            f"🏆 {u.first_name}" + (f" (@{u.username})" if u.username else "")
            for u in new_winner_users
        ])

        if giveaway.result_channel_ids:
            channels = await channel_repo.get_by_ids(db, giveaway.result_channel_ids)
            post = (
                f"🎁 <b>Дополнительные победители!</b>\n"
                f"Розыгрыш «{giveaway.title}»:\n\n{winners_text}"
            )
            for ch in channels:
                try:
                    await bot.send_message(chat_id=ch.telegram_id, text=post)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logging.error(f"Ошибка доп. победителей в {ch.title}: {e}")

        return {"status": "success", "drawn_count": len(new_winners)}


giveaway_service = GiveawayService()