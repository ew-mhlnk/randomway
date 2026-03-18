from sqlalchemy.ext.asyncio import AsyncSession
from repositories.giveaway_repo import giveaway_repo
from fastapi import HTTPException

class GiveawayService:
    @staticmethod
    async def create_draft(db: AsyncSession, user_id: int, data: dict):
        """Бизнес-логика создания черновика розыгрыша"""
        
        # 1. Защита: проверяем, не пытается ли юзер создать розыгрыш без шаблона
        if not data.get("template_id"):
            raise HTTPException(status_code=400, detail="Необходимо выбрать шаблон поста")

        # 2. Подготовка данных для сохранения
        giveaway_data = {
            "creator_id": user_id,
            "title": data.get("title", "Без названия"),
            "giveaway_type": data.get("type", "standard"),
            "template_id": int(data["template_id"]),
            "winners_count": int(data.get("winners_count", 1)),
            "is_active": False, # Пока это только черновик! Он станет True после публикации
            # Даты пока ставим заглушками, они прилетят на 9 шаге
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date")
        }

        # 3. Делегируем работу репозиторию
        return await giveaway_repo.create(db, obj_in_data=giveaway_data)

giveaway_service = GiveawayService()