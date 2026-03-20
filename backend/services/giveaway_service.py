from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from repositories.giveaway_repo import giveaway_repo


class GiveawayService:
    @staticmethod
    async def create_draft(db: AsyncSession, user_id: int, data: dict):
        """Бизнес-логика создания черновика розыгрыша"""

        if not data.get("template_id"):
            raise HTTPException(status_code=400, detail="Необходимо выбрать шаблон поста")

        giveaway_data = {
            "creator_id": user_id,
            "title": data.get("title", "Без названия"),
            "giveaway_type": data.get("type", "STANDARD").upper(),
            "template_id": int(data["template_id"]),
            "winners_count": int(data.get("winners_count", 1)),
            "is_active": False,
            # start_date и end_date — None до шага 9, колонки nullable
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
        }

        return await giveaway_repo.create(db, obj_in_data=giveaway_data)


giveaway_service = GiveawayService()