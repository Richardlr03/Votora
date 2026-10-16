"""add preference ballot submissions

Revision ID: a4b5c6d7e8f9
Revises: b8c9d0e1f2a3
Create Date: 2026-10-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a4b5c6d7e8f9"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "preference_ballots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("voter_id", sa.Integer(), nullable=False),
        sa.Column("motion_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "submitted_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["motion_id"], ["motions.id"]),
        sa.ForeignKeyConstraint(["voter_id"], ["voters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "voter_id",
            "motion_id",
            name="uq_preference_ballots_voter_motion",
        ),
    )

    # Every existing group of preference rows represents one submitted ballot.
    op.execute(
        sa.text(
            """
            INSERT INTO preference_ballots (voter_id, motion_id, status)
            SELECT voter_id, motion_id,
                   CASE
                       WHEN SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) > 0
                       THEN 'active'
                       ELSE 'invalidated'
                   END
            FROM preference_votes
            GROUP BY voter_id, motion_id
            """
        )
    )


def downgrade():
    op.drop_table("preference_ballots")
