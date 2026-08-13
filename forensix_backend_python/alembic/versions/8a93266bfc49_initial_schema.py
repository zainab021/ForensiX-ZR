"""initial_schema

Revision ID: 8a93266bfc49
Revises: 
Create Date: 2026-06-05 18:15:12.501129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a93266bfc49'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="citizen"),
        sa.Column("officer_code", sa.String(length=80), nullable=True, unique=True),
        sa.Column("status", sa.String(length=30), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=180), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="pending"),
        sa.Column("priority", sa.String(length=40), server_default="normal"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("case_no", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("crime_type", sa.String(length=90), nullable=False),
        sa.Column("location", sa.String(length=180), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="open"),
        sa.Column("assigned_officer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cases_case_no", "cases", ["case_no"], unique=True)

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("reports.id"), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("evidence_type", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("collected_by", sa.String(length=120), nullable=True),
        sa.Column("file_path", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="stored"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("target_role", sa.String(length=40), server_default="all"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=180), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("activity_logs")
    op.drop_table("notifications")
    op.drop_table("evidence")
    op.drop_table("cases")
    op.drop_table("reports")
    op.drop_table("users")
