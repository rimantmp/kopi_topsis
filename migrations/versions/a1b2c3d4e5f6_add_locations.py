"""add locations and link recommendation sessions

Revision ID: a1b2c3d4e5f6
Revises: 3196a0cde329
Create Date: 2026-09-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '3196a0cde329'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=191), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    with op.batch_alter_table('recommendation_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('location_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_recommendation_sessions_location_id'), ['location_id'], unique=False)
        batch_op.create_foreign_key('fk_recommendation_sessions_location_id', 'locations', ['location_id'], ['id'])


def downgrade():
    with op.batch_alter_table('recommendation_sessions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_recommendation_sessions_location_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_recommendation_sessions_location_id'))
        batch_op.drop_column('location_id')
    op.drop_table('locations')