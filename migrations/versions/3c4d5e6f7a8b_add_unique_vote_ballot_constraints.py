"""add unique vote ballot constraints

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-06-27 21:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3c4d5e6f7a8b"
down_revision = "2b3c4d5e6f7a"
branch_labels = None
depends_on = None


def _dedupe_simple_votes(connection, table_name):
    connection.execute(
        sa.text(
            f"""
            DELETE t1 FROM {table_name} t1
            INNER JOIN {table_name} t2
                ON t1.voter_id = t2.voter_id
               AND t1.motion_id = t2.motion_id
               AND t1.id < t2.id
            """
        )
    )


def _dedupe_option_votes(connection, table_name):
    connection.execute(
        sa.text(
            f"""
            DELETE t1 FROM {table_name} t1
            INNER JOIN {table_name} t2
                ON t1.voter_id = t2.voter_id
               AND t1.motion_id = t2.motion_id
               AND t1.option_id = t2.option_id
               AND t1.id < t2.id
            """
        )
    )


def upgrade():
    bind = op.get_bind()
    driver = bind.dialect.name

    if driver == "sqlite":
        for table_name, columns in (
            ("yes_no_votes", ("voter_id", "motion_id")),
            ("candidate_votes", ("voter_id", "motion_id")),
            ("preference_votes", ("voter_id", "motion_id", "option_id")),
            ("score_votes", ("voter_id", "motion_id", "option_id")),
            ("cumulative_votes", ("voter_id", "motion_id", "option_id")),
        ):
            cols = ", ".join(columns)
            bind.execute(
                sa.text(
                    f"""
                    DELETE FROM {table_name}
                    WHERE id NOT IN (
                        SELECT MAX(id)
                        FROM {table_name}
                        GROUP BY {cols}
                    )
                    """
                )
            )
    else:
        _dedupe_simple_votes(bind, "yes_no_votes")
        _dedupe_simple_votes(bind, "candidate_votes")
        _dedupe_option_votes(bind, "preference_votes")
        _dedupe_option_votes(bind, "score_votes")
        _dedupe_option_votes(bind, "cumulative_votes")

    with op.batch_alter_table("yes_no_votes", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_yes_no_votes_voter_motion",
            ["voter_id", "motion_id"],
        )

    with op.batch_alter_table("candidate_votes", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_candidate_votes_voter_motion",
            ["voter_id", "motion_id"],
        )

    with op.batch_alter_table("preference_votes", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_preference_votes_voter_motion_option",
            ["voter_id", "motion_id", "option_id"],
        )

    with op.batch_alter_table("score_votes", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_score_votes_voter_motion_option",
            ["voter_id", "motion_id", "option_id"],
        )

    with op.batch_alter_table("cumulative_votes", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_cumulative_votes_voter_motion_option",
            ["voter_id", "motion_id", "option_id"],
        )


def downgrade():
    with op.batch_alter_table("cumulative_votes", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_cumulative_votes_voter_motion_option", type_="unique"
        )

    with op.batch_alter_table("score_votes", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_score_votes_voter_motion_option", type_="unique"
        )

    with op.batch_alter_table("preference_votes", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_preference_votes_voter_motion_option", type_="unique"
        )

    with op.batch_alter_table("candidate_votes", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_candidate_votes_voter_motion", type_="unique"
        )

    with op.batch_alter_table("yes_no_votes", schema=None) as batch_op:
        batch_op.drop_constraint("uq_yes_no_votes_voter_motion", type_="unique")
