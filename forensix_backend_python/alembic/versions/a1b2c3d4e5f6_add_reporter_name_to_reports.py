"""add reporter_name to reports

Revision ID: a1b2c3d4e5f6
Revises: f3c1a9b7d2e4
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3c1a9b7d2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('reports', sa.Column('reporter_name', sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column('reports', 'reporter_name')
