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


giveaway_repo = GiveawayRepository()