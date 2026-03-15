from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from database import Base

class User(Base):
    __tablename__ = "users"

    # Telegram ID - огромное число, поэтому BigInteger
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(255))
    
    # Реферальная система: кто пригласил этого юзера
    invited_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Связь: один юзер может создать много розыгрышей
    giveaways = relationship("Giveaway", back_populates="creator")


class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    
    # Настройки розыгрыша
    winners_count: Mapped[int] = mapped_column(default=1)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Статус: активен или уже завершен
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    creator = relationship("User", back_populates="giveaways")