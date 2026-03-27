"""add meeting join token and student id

Revision ID: 1a2b3c4d5e6f
Revises: f2a3b4c5d6e7
Create Date: 2026-03-27 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1a2b3c4d5e6f"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("meetings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("join_token", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column(
                "registration_open",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.create_unique_constraint(
            "uq_meetings_join_token",
            ["join_token"],
        )

    with op.batch_alter_table("voters", schema=None) as batch_op:
        batch_op.add_column(sa.Column("student_id", sa.String(length=50), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE voters
            SET student_id = code
            WHERE student_id IS NULL
            """
        )
    )

    with op.batch_alter_table("voters", schema=None) as batch_op:
        batch_op.alter_column("student_id", existing_type=sa.String(length=50), nullable=False)
        batch_op.create_unique_constraint(
            "uq_voters_meeting_id_student_id",
            ["meeting_id", "student_id"],
        )


def downgrade():
    with op.batch_alter_table("voters", schema=None) as batch_op:
        batch_op.drop_constraint("uq_voters_meeting_id_student_id", type_="unique")
        batch_op.drop_column("student_id")

    with op.batch_alter_table("meetings", schema=None) as batch_op:
        batch_op.drop_constraint("uq_meetings_join_token", type_="unique")
        batch_op.drop_column("registration_open")
        batch_op.drop_column("join_token")
