from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import enum
from database import Base

# Типы розыгрышей (как в твоем ТЗ)
class GiveawayType(str, enum.Enum):
    STANDARD = "standard"
    BOOSTS = "boosts"
    INVITES = "invites"
    CUSTOM = "custom"

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    channels = relationship("Channel", back_populates="owner")
    templates = relationship("PostTemplate", back_populates="owner")
    giveaways = relationship("Giveaway", back_populates="creator")


class Channel(Base):
    """Таблица для сохраненных каналов пользователя"""
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True) # ID самого канала (-100...)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    
    title: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255)) # @durov
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True) # Бот все еще админ?
    
    owner = relationship("User", back_populates="channels")


class PostTemplate(Base):
    """Таблица для сохраненных шаблонов постов"""
    __tablename__ = "post_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    
    text: Mapped[str] = mapped_column(Text)
    media_id: Mapped[str | None] = mapped_column(String(255)) # ID фото/видео в Telegram
    media_type: Mapped[str | None] = mapped_column(String(50)) # 'photo' или 'video'
    
    button_text: Mapped[str] = mapped_column(String(100), default="Участвовать")
    button_color: Mapped[str] = mapped_column(String(20), default="blue")

    owner = relationship("User", back_populates="templates")
    giveaways = relationship("Giveaway", back_populates="template")


class Giveaway(Base):
    """Главная таблица розыгрышей (по твоему ТЗ)"""
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    template_id: Mapped[int] = mapped_column(ForeignKey("post_templates.id"))
    
    title: Mapped[str] = mapped_column(String(255))
    giveaway_type: Mapped[GiveawayType] = mapped_column(Enum(GiveawayType, native_enum=False, length=50), default=GiveawayType.STANDARD)
    
    winners_count: Mapped[int] = mapped_column(default=1)
    
    # Даты (в UTC, на фронте переведем в МСК)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Фичи
    use_captcha: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_stories: Mapped[bool] = mapped_column(Boolean, default=False)
    max_invites: Mapped[int] = mapped_column(default=0) # 0 = выключено
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    creator = relationship("User", back_populates="giveaways")
    template = relationship("PostTemplate", back_populates="giveaways")