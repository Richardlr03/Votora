"""add staff moderation and soft-deletion statuses

Revision ID: a7b8c9d0e1f2
Revises: f2a3b4c5d6e7
"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.add_column("users", sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.add_column("meetings", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    for table in ("yes_no_votes", "candidate_votes", "preference_votes", "score_votes", "cumulative_votes"):
        op.add_column(table, sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.create_table("staff", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("role", sa.String(20), nullable=False), sa.Column("email", sa.String(150), nullable=False, unique=True), sa.Column("password_hash", sa.String(256), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("staff.id")), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_table("flags", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("target_type", sa.String(20), nullable=False), sa.Column("target_id", sa.Integer(), nullable=False), sa.Column("flagged_by", sa.Integer(), sa.ForeignKey("staff.id"), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("staff.id")), sa.Column("resolution_note", sa.Text()), sa.Column("resolved_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.create_table("audit_log", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=False), sa.Column("action", sa.String(30), nullable=False), sa.Column("target_type", sa.String(20), nullable=False), sa.Column("target_id", sa.Integer(), nullable=False), sa.Column("flag_id", sa.Integer(), sa.ForeignKey("flags.id"), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))

def downgrade():
    op.drop_table("audit_log"); op.drop_table("flags"); op.drop_table("staff")
    for table in ("cumulative_votes", "score_votes", "preference_votes", "candidate_votes", "yes_no_votes"): op.drop_column(table, "status")
    op.drop_column("meetings", "status"); op.drop_column("users", "created_at"); op.drop_column("users", "status")
