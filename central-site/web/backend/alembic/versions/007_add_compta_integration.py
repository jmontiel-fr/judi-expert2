"""Ajouter colonnes B2B/B2C à experts, créer tables subscriptions et subscription_logs.

Revision ID: 007
Revises: 006
Create Date: 2025-07-01 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Expert : colonnes profil facturation B2B/B2C ---
    op.add_column(
        "experts",
        sa.Column("profile_type", sa.String(3), server_default="B2C", nullable=False),
    )
    op.add_column(
        "experts",
        sa.Column("company_address", sa.Text(), nullable=True),
    )
    op.add_column(
        "experts",
        sa.Column("billing_email", sa.String(255), nullable=True),
    )
    op.add_column(
        "experts",
        sa.Column("siret", sa.String(14), nullable=True),
    )
    op.add_column(
        "experts",
        sa.Column("rcs", sa.String(50), nullable=True),
    )

    # --- Table subscriptions ---
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expert_id", sa.Integer(), sa.ForeignKey("experts.id"), unique=True, nullable=False),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("current_period_end", sa.DateTime(), nullable=False),
        sa.Column("termination_scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("termination_effective_at", sa.DateTime(), nullable=True),
        sa.Column("payment_failed_at", sa.DateTime(), nullable=True),
        sa.Column("first_rejection_notified_at", sa.DateTime(), nullable=True),
        sa.Column("blocked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # --- Table subscription_logs ---
    op.create_table(
        "subscription_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expert_id", sa.Integer(), sa.ForeignKey("experts.id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    # --- Supprimer tables ---
    op.drop_table("subscription_logs")
    op.drop_table("subscriptions")

    # --- Supprimer colonnes Expert ---
    op.drop_column("experts", "rcs")
    op.drop_column("experts", "siret")
    op.drop_column("experts", "billing_email")
    op.drop_column("experts", "company_address")
    op.drop_column("experts", "profile_type")
