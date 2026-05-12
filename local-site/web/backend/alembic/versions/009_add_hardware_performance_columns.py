"""Ajout des colonnes hardware performance tuning à local_config.

Revision ID: 009
Revises: 008
"""

from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "local_config",
        sa.Column("detected_hardware_json", sa.String(1024), nullable=True),
    )
    op.add_column(
        "local_config",
        sa.Column("performance_profile_override", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("local_config", "performance_profile_override")
    op.drop_column("local_config", "detected_hardware_json")
