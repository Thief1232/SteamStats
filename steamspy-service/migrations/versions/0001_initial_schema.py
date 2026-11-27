"""Initial schema (what src/db/schema.sql used to create).

Databases created before migrations existed already have this table, so the
statement is IF NOT EXISTS: on such a database this revision only records itself
in alembic_version. Later revisions are plain Alembic operations.

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
        CREATE TABLE IF NOT EXISTS game_stats (
            app_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            owners_min BIGINT,
            owners_max BIGINT,
            average_playtime_forever INTEGER,
            median_playtime_forever INTEGER,
            ccu INTEGER,
            positive INTEGER,
            negative INTEGER,
            last_fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS game_stats")
