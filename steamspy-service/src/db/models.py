from datetime import datetime

from sqlalchemy import TIMESTAMP, BigInteger, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GameStats(Base):
    __tablename__ = "game_stats"
    app_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    owners_min: Mapped[int | None] = mapped_column(BigInteger)
    owners_max: Mapped[int | None] = mapped_column(BigInteger)
    average_playtime_forever: Mapped[int | None] = mapped_column(Integer)
    median_playtime_forever: Mapped[int | None] = mapped_column(Integer)
    ccu: Mapped[int | None] = mapped_column(Integer)
    positive: Mapped[int | None] = mapped_column(Integer)
    negative: Mapped[int | None] = mapped_column(Integer)
    last_fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)