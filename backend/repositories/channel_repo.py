from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Channel
from repositories.base import BaseRepository

class ChannelRepository(BaseRepository[Channel]):
    def __init__(self):
        super().__init__(Channel)

    async def get_by_ids(self, db: AsyncSession, channel_ids: list[int]) -> list[Channel]:
        result = await db.execute(select(self.model).where(self.model.id.in_(channel_ids)))
        return list(result.scalars().all())

# 🚀 ЭТА СТРОКА ОБЯЗАТЕЛЬНО ДОЛЖНА БЫТЬ ПРИЖАТА К ЛЕВОМУ КРАЮ
channel_repo = ChannelRepository()