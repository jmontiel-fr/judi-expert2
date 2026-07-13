"""Add update_type column to app_version table.

Allows distinguishing between lightweight image-only updates ("images")
and full reinstallation updates ("full") that require the expert to
re-download and re-run the installer.

Revision ID: 010
Revises: 009
Create Date: 2026-07-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_version",
        sa.Column(
            "update_type",
            sa.String(20),
            server_default="images",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("app_version", "update_type")
