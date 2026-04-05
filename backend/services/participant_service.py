"""backend/services/participant_service.py"""
import os
import aiohttp
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from fastapi import HTTPException

from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
from repositories.channel_repo import channel_repo


class ParticipantService:
    async def join_giveaway(
        self,
        db: AsyncSession,
        bot: Bot,
        giveaway_id: int,
        user_id: int,
        ref_code: str | None = None,
        payload: dict | None = None,
    ) -> dict:
        if payload is None:
            payload = {}

        giveaway = await giveaway_repo.get_active_by_id(db, giveaway_id)
        if not giveaway:
            raise HTTPException(status_code=400, detail="Розыгрыш не активен или не найден")

        # ── Уже участвует? Возвращаем статус БЕЗ капчи ─────────────────
        existing = await participant_repo.get_by_user_and_giveaway(db, user_id, giveaway_id)
        if existing:
            boost_url = await self._get_boost_url(db, giveaway)
            return {
                "status": "already_joined",
                "giveaway": {
                    "title":       giveaway.title,
                    "use_boosts":  giveaway.use_boosts,
                    "use_invites": giveaway.use_invites,
                    "use_stories": giveaway.use_stories,
                    "boost_url":   boost_url,
                    "max_invites": giveaway.max_invites,
                },
                "participant": {
                    "referral_code": existing.referral_code,
                    "invite_count":  existing.invite_count,
                    "has_boosted":   existing.has_boosted,
                    "boost_count":   getattr(existing, "boost_count", 0),
                    "story_clicks":  existing.story_clicks,
                },
            }

        # ── Капча (только для новых участников) ────────────────────────
        if giveaway.use_captcha:
            captcha_token = payload.get("captcha_token")
            if not captcha_token:
                raise HTTPException(status_code=400, detail="Пройдите проверку на робота (Капча)")
            secret_key = os.getenv("TURNSTILE_SECRET_KEY")
            if secret_key:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                        data={"secret": secret_key, "response": captcha_token},
                    ) as resp:
                        outcome = await resp.json()
                        if not outcome.get("success"):
                            logging.error(f"Turnstile error: {outcome}")
                            raise HTTPException(status_code=400, detail="Капча не пройдена. Попробуйте ещё раз.")

        # ── Проверка подписок ───────────────────────────────────────────
        missing_channels = []
        if giveaway.sponsor_channel_ids:
            channels = await channel_repo.get_by_ids(db, giveaway.sponsor_channel_ids)
            for ch in channels:
                try:
                    member = await bot.get_chat_member(chat_id=ch.telegram_id, user_id=user_id)
                    if member.status in ["left", "kicked", "banned"]:
                        invite_link = (
                            f"https://t.me/{ch.username}" if ch.username
                            else await bot.export_chat_invite_link(ch.telegram_id)
                        )
                        missing_channels.append({"id": ch.id, "title": ch.title, "url": invite_link})
                except Exception as e:
                    logging.warning(f"Проверка подписки {ch.id}: {e}")

        if missing_channels:
            return {"status": "missing_subscriptions", "channels": missing_channels}

        # ── Регистрируем нового участника ───────────────────────────────
        participant = await participant_repo.create(db, obj_in_data={
            "giveaway_id": giveaway_id,
            "user_id":     user_id,
            "referred_by": ref_code,
        })
        if ref_code:
            await participant_repo.increment_invite(db, ref_code)

        boost_url = await self._get_boost_url(db, giveaway)

        return {
            "status": "success",
            "is_new": True,
            "giveaway": {
                "title":       giveaway.title,
                "use_boosts":  giveaway.use_boosts,
                "use_invites": giveaway.use_invites,
                "use_stories": giveaway.use_stories,
                "boost_url":   boost_url,
                "max_invites": giveaway.max_invites,
            },
            "participant": {
                "referral_code": participant.referral_code,
                "invite_count":  participant.invite_count,
                "has_boosted":   participant.has_boosted,
                "boost_count":   0,
                "story_clicks":  participant.story_clicks,
            },
        }

    async def _get_boost_url(self, db, giveaway) -> str | None:
        """Возвращает ссылку для буста первого канала из boost_channel_ids (или sponsor)."""
        if not giveaway.use_boosts:
            return None
        # Приоритет: boost_channel_ids → sponsor_channel_ids
        ids = (giveaway.boost_channel_ids or []) or (giveaway.sponsor_channel_ids or [])
        if not ids:
            return None
        from sqlalchemy.future import select
        from models import Channel
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as s:
            ch = await s.scalar(select(Channel).where(Channel.id == ids[0]))
        if not ch:
            return None
        if ch.username:
            return f"https://t.me/boost/{ch.username}"
        cid = str(ch.telegram_id).replace("-100", "")
        return f"https://t.me/boost?c={cid}"

    # ── Проверка бустов — учитываем boost_count ─────────────────────────
    async def check_boost(self, db: AsyncSession, bot: Bot, giveaway_id: int, user_id: int) -> dict:
        participant = await participant_repo.get_by_user_and_giveaway(db, user_id, giveaway_id)
        if not participant:
            raise HTTPException(status_code=404, detail="Участник не найден")

        from sqlalchemy.future import select
        from models import Giveaway, Channel
        giveaway = await db.scalar(select(Giveaway).where(Giveaway.id == giveaway_id))
        if not giveaway or not giveaway.use_boosts:
            raise HTTPException(status_code=400, detail="Бусты не включены")

        # Каналы для проверки буста
        boost_ids = giveaway.boost_channel_ids or giveaway.sponsor_channel_ids or []
        if not boost_ids:
            raise HTTPException(status_code=400, detail="Нет каналов для буста")

        channels = await channel_repo.get_by_ids(db, boost_ids)
        total_boosts = 0

        for ch in channels:
            try:
                boosts = await bot.get_user_chat_boosts(chat_id=ch.telegram_id, user_id=user_id)
                if boosts and boosts.boosts:
                    total_boosts += len(boosts.boosts)
            except Exception as e:
                logging.warning(f"Проверка бустов {ch.id}: {e}")

        if total_boosts > 0:
            capped = min(total_boosts, 10)
            participant.has_boosted = True
            participant.boost_count = capped
            db.add(participant)
            await db.commit()
            return {"status": "success", "boost_count": capped}

        raise HTTPException(
            status_code=400,
            detail="Бустов не найдено. Нажмите «Забустить канал» и попробуйте снова через минуту."
        )


participant_service = ParticipantService()