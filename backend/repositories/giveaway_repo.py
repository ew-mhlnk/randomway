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

    # 🚀 НОВЫЙ МЕТОД: ПОЛУЧИТЬ ВСЕ РОЗЫГРЫШИ БЛОГЕРА
    async def get_all_by_creator(self, db: AsyncSession, creator_id: int) -> list[Giveaway]:
        result = await db.execute(
            select(self.model)
            .where(self.model.creator_id == creator_id)
            .order_by(self.model.id.desc())  # Сортируем: новые сверху
        )
        return list(result.scalars().all())

    async def get_active_by_id(self, db: AsyncSession, giveaway_id: int) -> Giveaway | None:
        stmt = select(self.model).where(
            self.model.id == giveaway_id,
            self.model.status == "active"  # Участник может зайти только в активный розыгрыш
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

giveaway_repo = GiveawayRepository()