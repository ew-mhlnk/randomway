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

    async def get_all_by_creator(self, db: AsyncSession, creator_id: int) -> list[Giveaway]:
        result = await db.execute(
            select(self.model)
            .where(self.model.creator_id == creator_id)
            .order_by(self.model.id.desc())
        )
        return list(result.scalars().all())

    async def get_active_by_id(self, db: AsyncSession, giveaway_id: int) -> Giveaway | None:
        stmt = select(self.model).where(
            self.model.id == giveaway_id,
            self.model.status == "active"
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_expired_active_giveaways(self, db: AsyncSession):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(self.model).where(
                self.model.status == "active",
                self.model.end_date <= now
            )
        )
        return result.scalars().all()

giveaway_repo = GiveawayRepository()