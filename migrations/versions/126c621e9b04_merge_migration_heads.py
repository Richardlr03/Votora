"""merge migration heads

Revision ID: 126c621e9b04
Revises: 3c4d5e6f7a8b, a7b8c9d0e1f2
Create Date: 2026-09-03 20:18:11.687364

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '126c621e9b04'
down_revision = ('3c4d5e6f7a8b', 'a7b8c9d0e1f2')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
