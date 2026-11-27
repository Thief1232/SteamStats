"""Initial schema (what src/db/schema.sql used to create).

Databases created before migrations existed already have these tables, so every
statement is IF NOT EXISTS: on such a database this revision only records itself
in alembic_version. Later revisions are plain Alembic operations.

Achievements are stored as an aggregate (unlocked/total) in owned_games, which is
how GetPlayerAchievements is summarised; a per-achievement table only makes sense
once the UI shows which specific achievements are missing.

Revision ID: 0001
Revises:
Create Date: 2026-11-27
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    # Steam profile. Created on the first public view, no registration needed;
    # user_id is set only when the owner signs in through Steam.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS steam_accounts (
            steam_id BIGINT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            persona_name TEXT NOT NULL,
            avatar_url TEXT,
            profile_url TEXT,
            account_created TIMESTAMPTZ,
            visibility TEXT NOT NULL DEFAULT 'public',
            linked_at TIMESTAMPTZ,
            last_fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            app_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            icon_url TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS owned_games (
            steam_id BIGINT NOT NULL REFERENCES steam_accounts(steam_id),
            app_id INTEGER NOT NULL REFERENCES games(app_id),
            playtime_minutes INTEGER NOT NULL DEFAULT 0,
            playtime_2weeks_minutes INTEGER NOT NULL DEFAULT 0,
            last_played TIMESTAMPTZ,
            achievements_unlocked INTEGER,
            achievements_total INTEGER,
            achievements_fetched_at TIMESTAMPTZ,
            last_fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (steam_id, app_id)
        )
        """
    )
    # Databases created before the achievements TTL existed lack this column.
    op.execute(
        "ALTER TABLE owned_games ADD COLUMN IF NOT EXISTS achievements_fetched_at TIMESTAMPTZ"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sessions, owned_games, games, steam_accounts, users")
