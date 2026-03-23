from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Enum, Integer, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from datetime import datetime, timezone
import enum
from database import Base

class GiveawayType(str, enum.Enum):
    STANDARD = "STANDARD"

class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    
    # Шаг 1: Основное
    title: Mapped[str] = mapped_column(String(255))
    template_id: Mapped[int] = mapped_column(ForeignKey("post_templates.id"))
    button_text: Mapped[str] = mapped_column(String(100), default="Участвовать")
    button_color_emoji: Mapped[str] = mapped_column(String(10), default="🔵") # Эмодзи вместо цвета
    
    # Шаги 2, 3, 4: Каналы (Используем PostgreSQL ARRAY для скорости, не нужны сложные Join-ы)
    sponsor_channel_ids: Mapped[list[int]] = mapped_column(PG_ARRAY(BigInteger), default=list)
    publish_channel_ids: Mapped[list[int]] = mapped_column(PG_ARRAY(BigInteger), default=list)
    result_channel_ids: Mapped[list[int]] = mapped_column(PG_ARRAY(BigInteger), default=list)
    
    # Шаг 5: Даты (ВСЕГДА ХРАНИМ В UTC!)
    start_immediately: Mapped[bool] = mapped_column(Boolean, default=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Шаг 6: Победители
    winners_count: Mapped[int] = mapped_column(Integer, default=1)
    
    # Шаги 7, 8, 9: Бусты, Друзья, Сторис
    use_boosts: Mapped[bool] = mapped_column(Boolean, default=False)
    use_invites: Mapped[bool] = mapped_column(Boolean, default=False)
    max_invites: Mapped[int] = mapped_column(Integer, default=100)
    use_stories: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Шаг 10: Защита
    use_captcha: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Системное
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="draft") # draft, active, finished

    creator = relationship("User", back_populates="giveaways")
    template = relationship("PostTemplate")