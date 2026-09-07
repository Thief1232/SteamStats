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