"""add approval voting

Revision ID: f3b4c5d6e7a8
Revises: a4b5c6d7e8f9
Create Date: 2026-10-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "f3b4c5d6e7a8"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("motions", sa.Column("approval_threshold_type", sa.String(20)))
    op.add_column("motions", sa.Column("approval_threshold_value", sa.Float()))
    op.add_column("motions", sa.Column("approval_percentage_basis", sa.String(20)))
    op.create_table(
        "approval_ballots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voter_id", sa.Integer(), sa.ForeignKey("voters.id"), nullable=False),
        sa.Column("motion_id", sa.Integer(), sa.ForeignKey("motions.id"), nullable=False),
        sa.Column("none_above", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.UniqueConstraint("voter_id", "motion_id", name="uq_approval_ballots_voter_motion"),
    )
    op.create_table(
        "approval_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voter_id", sa.Integer(), sa.ForeignKey("voters.id"), nullable=False),
        sa.Column("motion_id", sa.Integer(), sa.ForeignKey("motions.id"), nullable=False),
        sa.Column("option_id", sa.Integer(), sa.ForeignKey("options.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.UniqueConstraint("voter_id", "motion_id", "option_id", name="uq_approval_votes_voter_motion_option"),
    )


def downgrade():
    op.drop_table("approval_votes")
    op.drop_table("approval_ballots")
    op.drop_column("motions", "approval_percentage_basis")
    op.drop_column("motions", "approval_threshold_value")
    op.drop_column("motions", "approval_threshold_type")
