"""Ajouter les champs de versionnage à step_files.

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "step_files",
        sa.Column("is_modified", sa.Boolean(), server_default="0", nullable=False),
    )
    op.add_column(
        "step_files",
        sa.Column("original_file_path", sa.String(500), nullable=True),
    )
    op.add_column(
        "step_files",
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("step_files", "updated_at")
    op.drop_column("step_files", "original_file_path")
    op.drop_column("step_files", "is_modified")
