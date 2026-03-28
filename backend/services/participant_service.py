import os
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from fastapi import HTTPException
import logging

from repositories.giveaway_repo import giveaway_repo
from repositories.participant_repo import participant_repo
from repositories.channel_repo import channel_repo

class ParticipantService:
    async def join_giveaway(self, db: AsyncSession, bot: Bot, giveaway_id: int, user_id: int, ref_code: str | None = None, payload: dict = {}) -> dict:
        
        giveaway = await giveaway_repo.get_active_by_id(db, giveaway_id)
        if not giveaway:
            raise HTTPException(status_code=400, detail="Розыгрыш не активен или не найден")

        # 🚀 ПРОВЕРКА КАПЧИ
        if giveaway.use_captcha:
            captcha_token = payload.get("captcha_token")
            if not captcha_token:
                raise HTTPException(status_code=400, detail="Пройдите проверку на робота (Капча)")
            
            secret_key = os.getenv("TURNSTILE_SECRET_KEY")
            if secret_key:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                        data={"secret": secret_key, "response": captcha_token}
                    ) as resp:
                        outcome = await resp.json()
                        if not outcome.get("success"):
                            raise HTTPException(status_code=400, detail="Капча не пройдена. Вы бот?")

        missing_channels = []
        if giveaway.sponsor_channel_ids:
            channels = await channel_repo.get_by_ids(db, giveaway.sponsor_channel_ids)
            for ch in channels:
                try:
                    member = await bot.get_chat_member(chat_id=ch.telegram_id, user_id=user_id)
                    if member.status in ["left", "kicked", "banned"]:
                        invite_link = f"https://t.me/{ch.username}" if ch.username else await bot.export_chat_invite_link(ch.telegram_id)
                        missing_channels.append({"id": ch.id, "title": ch.title, "url": invite_link})
                except Exception as e:
                    logging.warning(f"Не удалось проверить подписку для канала {ch.id}: {e}")
                    pass

        if missing_channels:
            return {"status": "missing_subscriptions", "channels": missing_channels}

        participant = await participant_repo.get_by_user_and_giveaway(db, user_id, giveaway_id)
        
        if not participant:
            participant = await participant_repo.create(db, obj_in={
                "giveaway_id": giveaway_id,
                "user_id": user_id,
                "referred_by": ref_code
            })
            
            if ref_code:
                await participant_repo.increment_invite(db, ref_code)

        return {
            "status": "success",
            "giveaway": {
                "title": giveaway.title,
                "use_boosts": giveaway.use_boosts,
                "use_invites": giveaway.use_invites,
                "use_stories": giveaway.use_stories
            },
            "participant": {
                "referral_code": participant.referral_code,
                "invite_count": participant.invite_count
            }
        }

participant_service = ParticipantService()