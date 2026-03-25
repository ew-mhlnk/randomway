from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Text, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from datetime import datetime, timezone
import enum
import secrets
import string
from database import Base

class GiveawayType(str, enum.Enum):
    STANDARD = "STANDARD"
    BOOSTS = "BOOSTS"
    INVITES = "INVITES"
    CUSTOM = "CUSTOM"

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    channels = relationship("Channel", back_populates="owner")
    templates = relationship("PostTemplate", back_populates="owner")
    giveaways = relationship("Giveaway", back_populates="creator")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    title: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    members_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Наша ссылка на Cloudflare
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    owner = relationship("User", back_populates="channels")


class PostTemplate(Base):
    __tablename__ = "post_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    text: Mapped[str] = mapped_column(Text)
    media_id: Mapped[str | None] = mapped_column(String(255))
    media_type: Mapped[str | None] = mapped_column(String(50))
    button_text: Mapped[str] = mapped_column(String(100), default="Участвовать")
    button_color: Mapped[str] = mapped_column(String(20), default="blue")

    owner = relationship("User", back_populates="templates")
    giveaways = relationship("Giveaway", back_populates="template")


class Giveaway(Base):
    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    
    # Шаг 1: Основное
    title: Mapped[str] = mapped_column(String(255))
    template_id: Mapped[int] = mapped_column(ForeignKey("post_templates.id"))
    button_text: Mapped[str] = mapped_column(String(100), default="Участвовать")
    button_color_emoji: Mapped[str] = mapped_column(String(10), default="🔵")
    
    # Шаги 2, 3, 4: Каналы (PG_ARRAY)
    sponsor_channel_ids: Mapped[list[int]] = mapped_column(PG_ARRAY(BigInteger), default=list)
    publish_channel_ids: Mapped[list[int]] = mapped_column(PG_ARRAY(BigInteger), default=list)
    result_channel_ids: Mapped[list[int]] = mapped_column(PG_ARRAY(BigInteger), default=list)
    
    # Шаг 5: Даты
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
    status: Mapped[str] = mapped_column(String(50), default="draft")

    creator = relationship("User", back_populates="giveaways")
    template = relationship("PostTemplate", back_populates="giveaways")


# ─────────────────────────────────────────────────────────────────────────────
# УЧАСТНИКИ
# ─────────────────────────────────────────────────────────────────────────────

def generate_ref_code():
    """Генерирует случайный код из 8 символов для рефералки"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))

class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    giveaway_id: Mapped[int] = mapped_column(Integer, ForeignKey("giveaways.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), index=True)
    
    # Реферальная система
    referral_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, default=generate_ref_code)
    referred_by: Mapped[str | None] = mapped_column(String(20), nullable=True) # Код того, кто пригласил
    invite_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Выполнение бонусов
    has_boosted: Mapped[bool] = mapped_column(Boolean, default=False)
    story_clicks: Mapped[int] = mapped_column(Integer, default=0)
    
    # Финал
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))