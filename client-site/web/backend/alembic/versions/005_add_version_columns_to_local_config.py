"""Add app_version and llm_model_version columns to local_config table.

Revision ID: 005
Revises: 004
Create Date: 2026-05-20 12:00:00.000000

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
    op.add_column("local_config", sa.Column("app_version", sa.String(20), nullable=True))
    op.add_column("local_config", sa.Column("llm_model_version", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("local_config", "llm_model_version")
    op.drop_column("local_config", "app_version")
