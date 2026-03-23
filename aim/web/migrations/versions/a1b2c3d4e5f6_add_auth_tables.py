"""No-op placeholder — auth tables belong in run_metadata.sqlite (structured SDK DB),
not in aim_db. See aim/storage/migrations/versions/e1f2a3b4c5d6_add_ownership.py.

Revision ID: a1b2c3d4e5f6
Revises: 3d5fd76e8485
Create Date: 2026-03-21
"""

revision = 'a1b2c3d4e5f6'
down_revision = '3d5fd76e8485'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
