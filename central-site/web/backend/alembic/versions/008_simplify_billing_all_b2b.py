"""Simplifier le profil facturation — tous les experts sont B2B.

Supprime profile_type et rcs, ajoute entreprise.
Le SIRET devient optionnel (affiché "non attribué" si absent).

Revision ID: 008
Revises: 007
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ajouter colonne entreprise, supprimer profile_type et rcs."""
    # Ajouter la colonne entreprise
    op.add_column(
        "experts",
        sa.Column("entreprise", sa.String(255), nullable=True),
    )

    # Supprimer profile_type (plus nécessaire, tous B2B)
    op.drop_column("experts", "profile_type")

    # Supprimer rcs (plus nécessaire)
    op.drop_column("experts", "rcs")


def downgrade() -> None:
    """Restaurer profile_type et rcs, supprimer entreprise."""
    # Restaurer profile_type
    op.add_column(
        "experts",
        sa.Column("profile_type", sa.String(3), server_default="B2C", nullable=False),
    )

    # Restaurer rcs
    op.add_column(
        "experts",
        sa.Column("rcs", sa.String(50), nullable=True),
    )

    # Supprimer entreprise
    op.drop_column("experts", "entreprise")
