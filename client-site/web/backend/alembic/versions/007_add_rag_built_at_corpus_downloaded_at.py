"""Ajout des colonnes rag_built_at et corpus_downloaded_at à local_config.

Revision ID: 007
Revises: 006
"""

from alembic import op
import sqlalchemy as sa


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("local_config", sa.Column("rag_built_at", sa.DateTime(), nullable=True))
    op.add_column("local_config", sa.Column("corpus_downloaded_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("local_config", "corpus_downloaded_at")
    op.drop_column("local_config", "rag_built_at")
