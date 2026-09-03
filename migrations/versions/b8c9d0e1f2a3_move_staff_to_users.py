"""move staff permissions into users

Revision ID: b8c9d0e1f2a3
Revises: 126c621e9b04
"""
from alembic import op
import sqlalchemy as sa

revision = "b8c9d0e1f2a3"
down_revision = "126c621e9b04"
branch_labels = None
depends_on = None


def upgrade():
    """Replace standalone staff identities while preserving moderation history."""
    bind = op.get_bind()
    op.add_column("users", sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("staff_role", sa.String(20), nullable=True))

    staff_rows = bind.execute(
        sa.text("SELECT id, email, password_hash, role, status FROM staff")
    ).mappings().all()
    staff_to_user = {}
    for staff in staff_rows:
        user = bind.execute(
            sa.text("SELECT id FROM users WHERE email = :email"), {"email": staff["email"]}
        ).mappings().first()
        if user:
            user_id = user["id"]
            bind.execute(
                sa.text("UPDATE users SET is_staff = :is_staff, staff_role = :role WHERE id = :id"),
                {"is_staff": staff["status"] == "active", "role": staff["role"], "id": user_id},
            )
        else:
            base_username = f"staff_{staff['id']}"
            username = base_username
            suffix = 1
            while bind.execute(
                sa.text("SELECT 1 FROM users WHERE username = :username"), {"username": username}
            ).first():
                suffix += 1
                username = f"{base_username}_{suffix}"
            bind.execute(
                sa.text("INSERT INTO users (username, email, password_hash, status, is_staff, staff_role) VALUES (:username, :email, :password_hash, 'active', :is_staff, :role)"),
                {"username": username, "email": staff["email"], "password_hash": staff["password_hash"], "is_staff": staff["status"] == "active", "role": staff["role"]},
            )
            user_id = bind.execute(
                sa.text("SELECT id FROM users WHERE email = :email"), {"email": staff["email"]}
            ).scalar_one()
        staff_to_user[staff["id"]] = user_id

    flags = bind.execute(sa.text("SELECT * FROM flags")).mappings().all()
    audit_rows = bind.execute(sa.text("SELECT * FROM audit_log")).mappings().all()

    op.create_table("flags_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("flagged_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True), sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for flag in flags:
        bind.execute(sa.text("INSERT INTO flags_new (id, target_type, target_id, flagged_by, reason, status, resolved_by, resolution_note, resolved_at, created_at) VALUES (:id, :target_type, :target_id, :flagged_by, :reason, :status, :resolved_by, :resolution_note, :resolved_at, :created_at)"),
            {**dict(flag), "flagged_by": staff_to_user[flag["flagged_by"]], "resolved_by": staff_to_user.get(flag["resolved_by"])})

    op.create_table("audit_log_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False), sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False), sa.Column("flag_id", sa.Integer(), sa.ForeignKey("flags_new.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for audit in audit_rows:
        bind.execute(sa.text("INSERT INTO audit_log_new (id, actor_id, action, target_type, target_id, flag_id, created_at) VALUES (:id, :actor_id, :action, :target_type, :target_id, :flag_id, :created_at)"),
            {**dict(audit), "actor_id": staff_to_user[audit["actor_id"]]})

    op.drop_table("audit_log")
    op.drop_table("flags")
    op.drop_table("staff")
    op.rename_table("flags_new", "flags")
    op.rename_table("audit_log_new", "audit_log")


def downgrade():
    raise RuntimeError("This migration cannot be downgraded safely after moderation data exists.")
