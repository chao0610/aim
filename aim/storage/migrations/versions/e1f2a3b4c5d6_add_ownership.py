"""Add auth tables and ownership columns to structured DB

Revision ID: e1f2a3b4c5d6
Revises: 661514b12ee1
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'e1f2a3b4c5d6'
down_revision = '661514b12ee1'
branch_labels = None
depends_on = None


def _has_table(bind, name):
    return inspect(bind).has_table(name)


def _has_column(bind, table, column):
    return column in {c['name'] for c in inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()

    # aim_user table
    if not _has_table(bind, 'aim_user'):
        op.create_table(
            'aim_user',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('username', sa.Text(), nullable=False),
            sa.Column('password_hash', sa.Text(), nullable=False),
            sa.Column('is_admin', sa.Boolean(), server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('username'),
        )

    # api_token table
    if not _has_table(bind, 'api_token'):
        op.create_table(
            'api_token',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('token_hash', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('token_hash'),
        )

    # ownership columns on run
    with op.batch_alter_table('run') as batch_op:
        if not _has_column(bind, 'run', 'user_id'):
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        if not _has_column(bind, 'run', 'is_public'):
            batch_op.add_column(sa.Column('is_public', sa.Boolean(), server_default='0', nullable=False))

    # ownership columns on experiment
    with op.batch_alter_table('experiment') as batch_op:
        if not _has_column(bind, 'experiment', 'user_id'):
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        if not _has_column(bind, 'experiment', 'is_public'):
            batch_op.add_column(sa.Column('is_public', sa.Boolean(), server_default='0', nullable=False))


def downgrade():
    with op.batch_alter_table('experiment') as batch_op:
        batch_op.drop_column('is_public')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('run') as batch_op:
        batch_op.drop_column('is_public')
        batch_op.drop_column('user_id')

    op.drop_table('api_token')
    op.drop_table('aim_user')
