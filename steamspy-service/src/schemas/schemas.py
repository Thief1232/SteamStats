from pydantic import BaseModel


class GameSearchResult(BaseModel):
    app_id: int
    name: str


class GameStatsResponse(BaseModel):
    app_id: int
    name: str
    owners_min: int | None
    owners_max: int | None
    average_playtime_forever: int | None
    median_playtime_forever: int | None
    ccu: int | None
    positive: int | None
    negative: int | None

    @classmethod
    def from_row(cls, row) -> "GameStatsResponse":
        return cls(
            app_id=row.app_id,
            name=row.name,
            owners_min=row.owners_min,
            owners_max=row.owners_max,
            average_playtime_forever=row.average_playtime_forever,
            median_playtime_forever=row.median_playtime_forever,
            ccu=row.ccu,
            positive=row.positive,
            negative=row.negative,
        )