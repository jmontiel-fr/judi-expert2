"""Add ticket_config table for configurable ticket pricing.

Revision ID: 002
Revises: 001
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prix_ht", sa.Numeric(10, 2), nullable=False, server_default="49.00"
        ),
        sa.Column(
            "tva_rate", sa.Numeric(5, 2), nullable=False, server_default="20.00"
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Seed default config row
    op.execute(
        sa.text(
            "INSERT INTO ticket_config (prix_ht, tva_rate) VALUES (49.00, 20.00)"
        )
    )


def downgrade() -> None:
    op.drop_table("ticket_config")
