from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func, case
from models import Participant
from repositories.base import BaseRepository

class ParticipantRepository(BaseRepository[Participant]):
    def __init__(self):
        super().__init__(Participant)

    async def get_by_user_and_giveaway(self, db: AsyncSession, user_id: int, giveaway_id: int) -> Participant | None:
        result = await db.execute(
            select(self.model).where(self.model.user_id == user_id, self.model.giveaway_id == giveaway_id)
        )
        return result.scalar_one_or_none()

    async def increment_invite(self, db: AsyncSession, ref_code: str) -> None:
        await db.execute(
            update(self.model)
            .where(self.model.referral_code == ref_code)
            .values(invite_count=self.model.invite_count + 1)
        )
        await db.commit()

    # 🚀 НОВЫЙ МЕТОД ДЛЯ ПОДСЧЕТА УЧАСТНИКОВ
    async def count_by_giveaway(self, db: AsyncSession, giveaway_id: int) -> int:
        result = await db.execute(select(func.count()).where(self.model.giveaway_id == giveaway_id))
        return result.scalar() or 0

    # Получить всех участников конкретного розыгрыша
    async def get_all_by_giveaway(self, db: AsyncSession, giveaway_id: int) -> list[Participant]:
        result = await db.execute(select(self.model).where(self.model.giveaway_id == giveaway_id))
        return list(result.scalars().all())

    # Получить победителей вместе с их юзернеймами (JOIN с таблицей User)
    async def get_winners_with_users(self, db: AsyncSession, giveaway_id: int):
        from models import User # Локальный импорт
        result = await db.execute(
            select(self.model, User)
            .join(User, self.model.user_id == User.telegram_id)
            .where(self.model.giveaway_id == giveaway_id, self.model.is_winner == True)
        )
        return result.all() # Вернет список кортежей (Participant, User)

    async def get_analytics_stats(self, db: AsyncSession, giveaway_id: int) -> dict:
        """Один быстрый запрос для получения всей аналитики розыгрыша"""
        result = await db.execute(
            select(
                func.count(self.model.id).label("total"),
                # Считаем тех, у кого is_active = False (ливнули/хитрецы)
                func.sum(case((self.model.is_active == False, 1), else_=0)).label("cheaters"),
                # Считаем тех, кто дал буст
                func.sum(case((self.model.has_boosted == True, 1), else_=0)).label("boosts")
            ).where(self.model.giveaway_id == giveaway_id)
        )
        row = result.fetchone()
        return {
            "total": row.total or 0,
            "cheaters": row.cheaters or 0,
            "boosts": row.boosts or 0
        }

participant_repo = ParticipantRepository()