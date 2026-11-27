"""Store sessions under the SHA-256 of their token instead of the token itself.

Existing sessions keep working: their ids are replaced by the same hash the app now
looks up (queries.session_key), so nobody is signed out by this migration.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-27
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE sessions SET id = encode(sha256(convert_to(id, 'UTF8')), 'hex')")


def downgrade() -> None:
    # A hash cannot be turned back into a token: everyone signs in again.
    op.execute("DELETE FROM sessions")
