from datetime import datetime

from sqlalchemy import TIMESTAMP, BigInteger, ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class SteamAccount(Base):
    __tablename__ = "steam_accounts"
    steam_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    persona_name: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    profile_url: Mapped[str | None] = mapped_column(Text)
    account_created: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    visibility: Mapped[str] = mapped_column(Text, nullable=False, default="public")
    linked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_fetched_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class Game(Base):
    __tablename__ = "games"
    app_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    icon_url: Mapped[str | None] = mapped_column(Text)


class OwnedGame(Base):
    __tablename__ = "owned_games"
    steam_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("steam_accounts.steam_id"), primary_key=True
    )
    app_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.app_id"), primary_key=True
    )
    playtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    playtime_2weeks_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_played: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    achievements_unlocked: Mapped[int | None] = mapped_column(Integer)
    achievements_total: Mapped[int | None] = mapped_column(Integer)
    last_fetched_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)