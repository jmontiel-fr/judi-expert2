"""Initial models — création des 5 tables du Site Central.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- experts ---
    op.create_table(
        "experts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cognito_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("nom", sa.String(100), nullable=False),
        sa.Column("prenom", sa.String(100), nullable=False),
        sa.Column("adresse", sa.Text(), nullable=False),
        sa.Column("domaine", sa.String(100), nullable=False),
        sa.Column("accept_newsletter", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- tickets ---
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_code", sa.String(255), nullable=False, unique=True),
        sa.Column("expert_id", sa.Integer(), sa.ForeignKey("experts.id"), nullable=False),
        sa.Column("domaine", sa.String(100), nullable=False),
        sa.Column("statut", sa.String(20), nullable=False, server_default="actif"),
        sa.Column("montant", sa.Numeric(10, 2), nullable=False),
        sa.Column("stripe_payment_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("used_at", sa.DateTime(), nullable=True),
    )

    # --- domaines ---
    op.create_table(
        "domaines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nom", sa.String(100), nullable=False, unique=True),
        sa.Column("repertoire", sa.String(255), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default="false"),
    )

    # --- corpus_versions ---
    op.create_table(
        "corpus_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domaine_id", sa.Integer(), sa.ForeignKey("domaines.id"), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("ecr_image_uri", sa.String(500), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- contact_messages ---
    op.create_table(
        "contact_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expert_id", sa.Integer(), sa.ForeignKey("experts.id"), nullable=True),
        sa.Column("domaine", sa.String(100), nullable=False),
        sa.Column("objet", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- Seed admin account (Exigence 19.1) ---
    op.execute(
        sa.text(
            "INSERT INTO experts (cognito_sub, email, nom, prenom, adresse, domaine, accept_newsletter) "
            "VALUES ('admin', 'admin@judi-expert.fr', 'Admin', 'Judi-Expert', 'Administration', "
            "'général', false)"
        )
    )


def downgrade() -> None:
    op.drop_table("contact_messages")
    op.drop_table("corpus_versions")
    op.drop_table("domaines")
    op.drop_table("tickets")
    op.drop_table("experts")
