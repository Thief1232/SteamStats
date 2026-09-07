from typing import Literal
from pydantic import BaseModel

class UserProfile(BaseModel):
    steam_id: str
    persona_name: str
    avatar_url: str
    profile_url: str
    account_created: int | None
    visibility: Literal["public", "private"]

    @classmethod
    def from_row(cls, row) -> "UserProfile":
        return cls(
            steam_id=str(row.steam_id),
            persona_name=row.persona_name,
            avatar_url=row.avatar_url,
            profile_url=row.profile_url,
            account_created=int(row.account_created.timestamp()) if row.account_created else None,
            visibility=row.visibility,
        )


class Achievements(BaseModel):
    unlocked: int
    total: int
    pct: float

class GameEntry(BaseModel):
    app_id: int
    name: str
    icon_url: str | None
    playtime_minutes: int
    playtime_2weeks_minutes: int
    last_played: int | None
    achievements: Achievements | None

class RecentGame(BaseModel):
    app_id: int
    name: str
    playtime_2weeks_minutes: int
    playtime_minutes: int

class Library(BaseModel):
    total_games: int
    total_playtime_minutes: int
    played_count: int
    never_played_count: int
    games: list[GameEntry]
    recent: list[RecentGame]

    @classmethod
    def from_rows(cls, rows: list) -> "Library":
        games = []
        for owned, game in rows:
            achievements = None
            if owned.achievements_total:
                achievements = Achievements(
                    unlocked=owned.achievements_unlocked,
                    total=owned.achievements_total,
                    pct=round(owned.achievements_unlocked / owned.achievements_total * 100, 1),
                )
            games.append(GameEntry(
                app_id=game.app_id,
                name=game.name,
                icon_url=game.icon_url,
                playtime_minutes=owned.playtime_minutes,
                playtime_2weeks_minutes=owned.playtime_2weeks_minutes,
                last_played=int(owned.last_played.timestamp()) if owned.last_played else None,
                achievements=achievements,
            ))

        played = [g for g in games if g.playtime_minutes > 0]
        recent = sorted(
            (RecentGame(app_id=g.app_id, name=g.name,
                        playtime_2weeks_minutes=g.playtime_2weeks_minutes,
                        playtime_minutes=g.playtime_minutes)
             for g in games if g.playtime_2weeks_minutes > 0),
            key=lambda r: r.playtime_2weeks_minutes, reverse=True,
        )

        return cls(
            total_games=len(games),
            total_playtime_minutes=sum(g.playtime_minutes for g in games),
            played_count=len(played),
            never_played_count=len(games) - len(played),
            games=games,
            recent=recent,
        )