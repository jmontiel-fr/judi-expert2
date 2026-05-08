"""Add doc_type and doc_format columns to step_files table.

Revision ID: 005
Revises: 004
Create Date: 2026-05-07 12:00:00.000000

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
    op.add_column("step_files", sa.Column("doc_type", sa.String(50), nullable=True))
    op.add_column("step_files", sa.Column("doc_format", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("step_files", "doc_format")
    op.drop_column("step_files", "doc_type")
