"""add meeting member id label

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-06-27 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b3c4d5e6f7a"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "meetings",
        sa.Column(
            "member_id_label",
            sa.String(length=100),
            nullable=False,
            server_default="Member ID",
        ),
    )


def downgrade():
    op.drop_column("meetings", "member_id_label")
