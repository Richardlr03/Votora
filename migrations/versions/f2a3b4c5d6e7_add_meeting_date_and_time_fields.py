"""add meeting date and time fields

Revision ID: f2a3b4c5d6e7
Revises: e7a1b2c3d4f5
Create Date: 2026-02-10 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f2a3b4c5d6e7"
down_revision = "e7a1b2c3d4f5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("meetings", sa.Column("meeting_date", sa.Date(), nullable=True))
    op.add_column("meetings", sa.Column("start_time", sa.Time(), nullable=True))
    op.add_column("meetings", sa.Column("end_time", sa.Time(), nullable=True))


def downgrade():
    op.drop_column("meetings", "end_time")
    op.drop_column("meetings", "start_time")
    op.drop_column("meetings", "meeting_date")
