"""Create app_version table.

Revision ID: 005
Revises: 004
Create Date: 2026-05-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("download_url", sa.String(500), nullable=False),
        sa.Column("mandatory", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("release_notes", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_version")
