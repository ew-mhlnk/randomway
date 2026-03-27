from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func
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

participant_repo = ParticipantRepository()