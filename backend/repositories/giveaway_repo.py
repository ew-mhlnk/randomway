"""backend\repositories\giveaway_repo.py"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Giveaway
from repositories.base import BaseRepository


class GiveawayRepository(BaseRepository[Giveaway]):
    def __init__(self):
        super().__init__(Giveaway)

    async def get_active_by_user(self, db: AsyncSession, user_id: int):
        stmt = select(self.model).where(
            self.model.creator_id == user_id,
            self.model.is_active == True,
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    # 🚀 ДОБАВЛЯЕМ ЭТОТ МЕТОД:
    async def get_active_by_id(self, db: AsyncSession, giveaway_id: int) -> Giveaway | None:
        stmt = select(self.model).where(
            self.model.id == giveaway_id,
            self.model.status == "active"  # Участник может зайти только в активный розыгрыш
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

giveaway_repo = GiveawayRepository()