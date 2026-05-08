"""Add ville, code_postal, telephone, is_deleted to experts table.

Revision ID: 004
Revises: 003
Create Date: 2026-05-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("experts", sa.Column("ville", sa.String(100), nullable=False, server_default=""))
    op.add_column("experts", sa.Column("code_postal", sa.String(10), nullable=False, server_default=""))
    op.add_column("experts", sa.Column("telephone", sa.String(20), nullable=False, server_default=""))
    op.add_column("experts", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("experts", "is_deleted")
    op.drop_column("experts", "telephone")
    op.drop_column("experts", "code_postal")
    op.drop_column("experts", "ville")
