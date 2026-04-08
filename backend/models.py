"""backend/models.py"""
from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from datetime import datetime, timezone
import secrets, string
from database import Base


class User(Base):
    __tablename__ = "users"
    telegram_id:  Mapped[int]        = mapped_column(BigInteger, primary_key=True, index=True)
    username:     Mapped[str | None] = mapped_column(String(255))
    first_name:   Mapped[str]        = mapped_column(String(255))
    created_at:   Mapped[datetime]   = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    channels  = relationship("Channel",      back_populates="owner")
    templates = relationship("PostTemplate", back_populates="owner")
    giveaways = relationship("Giveaway",     back_populates="creator")


class Channel(Base):
    __tablename__ = "channels"
    id:            Mapped[int]        = mapped_column(primary_key=True, autoincrement=True)
    telegram_id:   Mapped[int]        = mapped_column(BigInteger, unique=True, index=True)
    owner_id:      Mapped[int]        = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    title:         Mapped[str]        = mapped_column(String(255))
    username:      Mapped[str | None] = mapped_column(String(255))
    is_active:     Mapped[bool]       = mapped_column(Boolean, default=True)
    members_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_url:     Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner = relationship("User", back_populates="channels")


class PostTemplate(Base):
    __tablename__ = "post_templates"
    id:           Mapped[int]        = mapped_column(primary_key=True, autoincrement=True)
    owner_id:     Mapped[int]        = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    text:         Mapped[str]        = mapped_column(Text)
    media_id:     Mapped[str | None] = mapped_column(String(255))
    media_type:   Mapped[str | None] = mapped_column(String(50))
    button_text:  Mapped[str]        = mapped_column(String(100), default="Участвовать")
    button_color: Mapped[str]        = mapped_column(String(20),  default="blue")
    owner     = relationship("User",     back_populates="templates")
    giveaways = relationship("Giveaway", back_populates="template")


class Giveaway(Base):
    __tablename__ = "giveaways"

    id:         Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))

    title:              Mapped[str]        = mapped_column(String(255))
    template_id:        Mapped[int]        = mapped_column(ForeignKey("post_templates.id"))
    button_text:        Mapped[str]        = mapped_column(String(100), default="Участвовать")
    button_color_emoji: Mapped[str]        = mapped_column(String(10),  default="🎁")
    button_color:       Mapped[str]        = mapped_column(String(20),  default="default", server_default="default")
    button_custom_emoji_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Маскот розыгрыша (id файла без расширения: 1-duck, 2-cat, ...)
    mascot_id: Mapped[str] = mapped_column(String(20), default="1-duck", server_default="1-duck")

    sponsor_channel_ids: Mapped[list[int]] = mapped_column(PG_ARRAY(BigInteger), default=list)
    publish_channel_ids: Mapped[list[int]] = mapped_column(PG_ARRAY(BigInteger), default=list)
    result_channel_ids:  Mapped[list[int]] = mapped_column(PG_ARRAY(BigInteger), default=list)
    boost_channel_ids:   Mapped[list[int]] = mapped_column(
        PG_ARRAY(BigInteger), default=list, server_default="{}")

    start_immediately: Mapped[bool]            = mapped_column(Boolean, default=True)
    start_date:        Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date:          Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    winners_count: Mapped[int]  = mapped_column(Integer, default=1)
    use_boosts:    Mapped[bool] = mapped_column(Boolean, default=False)
    use_invites:   Mapped[bool] = mapped_column(Boolean, default=False)
    max_invites:   Mapped[int]  = mapped_column(Integer, default=100)
    use_captcha:   Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    status:    Mapped[str]  = mapped_column(String(50), default="draft")

    # Для хранения информации о первом опубликованном посте (чтобы ответить на ним с результатами)
    post_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    post_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    creator  = relationship("User",         back_populates="giveaways")
    template = relationship("PostTemplate", back_populates="giveaways")


def generate_ref_code():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


class Participant(Base):
    __tablename__ = "participants"
    id:            Mapped[int]        = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    giveaway_id:   Mapped[int]        = mapped_column(Integer, ForeignKey("giveaways.id"), index=True)
    user_id:       Mapped[int]        = mapped_column(BigInteger, ForeignKey("users.telegram_id"), index=True)
    referral_code: Mapped[str]        = mapped_column(String(20), unique=True, index=True, default=generate_ref_code)
    referred_by:   Mapped[str | None] = mapped_column(String(20), nullable=True)
    invite_count:  Mapped[int]        = mapped_column(Integer, default=0)
    has_boosted:   Mapped[bool]       = mapped_column(Boolean, default=False)
    boost_count:   Mapped[int]        = mapped_column(Integer, default=0)
    is_winner:     Mapped[bool]       = mapped_column(Boolean, default=False)
    is_active:     Mapped[bool]       = mapped_column(Boolean, default=True)
    joined_at:     Mapped[datetime]   = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))