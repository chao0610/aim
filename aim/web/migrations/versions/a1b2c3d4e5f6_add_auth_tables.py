"""Add auth tables and ownership columns

Revision ID: a1b2c3d4e5f6
Revises: 3d5fd76e8485
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '3d5fd76e8485'
branch_labels = None
depends_on = None


def upgrade():
    # aim_user table
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
    op.create_table(
        'api_token',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['aim_user.id']),
        sa.UniqueConstraint('token_hash'),
    )

    # ownership columns on run
    with op.batch_alter_table('run') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('is_public', sa.Boolean(), server_default='0', nullable=False))
        batch_op.create_foreign_key('fk_run_user_id', 'aim_user', ['user_id'], ['id'])

    # ownership columns on experiment
    with op.batch_alter_table('experiment') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('is_public', sa.Boolean(), server_default='0', nullable=False))
        batch_op.create_foreign_key('fk_experiment_user_id', 'aim_user', ['user_id'], ['id'])


def downgrade():
    with op.batch_alter_table('experiment') as batch_op:
        batch_op.drop_constraint('fk_experiment_user_id', type_='foreignkey')
        batch_op.drop_column('is_public')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('run') as batch_op:
        batch_op.drop_constraint('fk_run_user_id', type_='foreignkey')
        batch_op.drop_column('is_public')
        batch_op.drop_column('user_id')

    op.drop_table('api_token')
    op.drop_table('aim_user')
