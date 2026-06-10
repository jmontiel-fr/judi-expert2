"""Réparer les colonnes refunded_at / stripe_refund_id si absentes.

Certaines bases locales ont alembic_version=008 sans ces colonnes
(create_all au démarrage + version Alembic avancée manuellement).

Revision ID: 009
Revises: 008
"""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS "
        "refunded_at TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS "
        "stripe_refund_id VARCHAR(255)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tickets DROP COLUMN IF EXISTS stripe_refund_id")
    op.execute("ALTER TABLE tickets DROP COLUMN IF EXISTS refunded_at")
