"""Initial models — création des 5 tables de l'Application Locale.

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
    # --- local_config ---
    op.create_table(
        "local_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("domaine", sa.String(100), nullable=False),
        sa.Column("rag_version", sa.String(50), nullable=True),
        sa.Column("is_configured", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- dossiers ---
    op.create_table(
        "dossiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("ticket_id", sa.String(255), nullable=False, unique=True),
        sa.Column("domaine", sa.String(100), nullable=False),
        sa.Column("statut", sa.String(20), nullable=False, server_default="actif"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- steps ---
    op.create_table(
        "steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dossier_id", sa.Integer(), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(20), nullable=False, server_default="initial"),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("validated_at", sa.DateTime(), nullable=True),
    )

    # --- step_files ---
    op.create_table(
        "step_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("step_id", sa.Integer(), sa.ForeignKey("steps.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- chat_messages ---
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("step_files")
    op.drop_table("steps")
    op.drop_table("dossiers")
    op.drop_table("local_config")
