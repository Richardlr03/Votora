"""split votes by system

Revision ID: 8ee6508f8c71
Revises: 
Create Date: 2026-02-03 23:38:17.326473

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8ee6508f8c71'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=150), nullable=False),
            sa.Column("email", sa.String(length=150), nullable=False),
            sa.Column("password_hash", sa.String(length=256), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("username"),
        )
        existing_tables.add("users")

    if "meetings" not in existing_tables:
        op.create_table(
            "meetings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("admin_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("meetings")

    if "motions" not in existing_tables:
        op.create_table(
            "motions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("meeting_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("num_winners", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("motions")

    if "voters" not in existing_tables:
        op.create_table(
            "voters",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("meeting_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )
        existing_tables.add("voters")

    if "options" not in existing_tables:
        op.create_table(
            "options",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("motion_id", sa.Integer(), nullable=False),
            sa.Column("text", sa.String(length=200), nullable=False),
            sa.ForeignKeyConstraint(["motion_id"], ["motions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("options")

    if "candidate_votes" not in existing_tables:
        op.create_table(
            'candidate_votes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('voter_id', sa.Integer(), nullable=False),
            sa.Column('motion_id', sa.Integer(), nullable=False),
            sa.Column('option_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['motion_id'], ['motions.id']),
            sa.ForeignKeyConstraint(['option_id'], ['options.id']),
            sa.ForeignKeyConstraint(['voter_id'], ['voters.id']),
            sa.PrimaryKeyConstraint('id')
        )

    if "preference_votes" not in existing_tables:
        op.create_table(
            'preference_votes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('voter_id', sa.Integer(), nullable=False),
            sa.Column('motion_id', sa.Integer(), nullable=False),
            sa.Column('option_id', sa.Integer(), nullable=False),
            sa.Column('preference_rank', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['motion_id'], ['motions.id']),
            sa.ForeignKeyConstraint(['option_id'], ['options.id']),
            sa.ForeignKeyConstraint(['voter_id'], ['voters.id']),
            sa.PrimaryKeyConstraint('id')
        )

    if "yes_no_votes" not in existing_tables:
        op.create_table(
            'yes_no_votes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('voter_id', sa.Integer(), nullable=False),
            sa.Column('motion_id', sa.Integer(), nullable=False),
            sa.Column('option_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['motion_id'], ['motions.id']),
            sa.ForeignKeyConstraint(['option_id'], ['options.id']),
            sa.ForeignKeyConstraint(['voter_id'], ['voters.id']),
            sa.PrimaryKeyConstraint('id')
        )
    if "votes" in existing_tables:
        op.execute(
            sa.text(
                """
                INSERT INTO yes_no_votes (voter_id, motion_id, option_id)
                SELECT v.voter_id, v.motion_id, v.option_id
                FROM votes v
                JOIN motions m ON m.id = v.motion_id
                WHERE m.type = 'YES_NO'
                """
            )
        )
        op.execute(
            sa.text(
                """
                INSERT INTO candidate_votes (voter_id, motion_id, option_id)
                SELECT v.voter_id, v.motion_id, v.option_id
                FROM votes v
                JOIN motions m ON m.id = v.motion_id
                WHERE m.type = 'CANDIDATE'
                """
            )
        )
        op.execute(
            sa.text(
                """
                INSERT INTO preference_votes (voter_id, motion_id, option_id, preference_rank)
                SELECT v.voter_id, v.motion_id, v.option_id, v.preference_rank
                FROM votes v
                JOIN motions m ON m.id = v.motion_id
                WHERE m.type = 'PREFERENCE' AND v.preference_rank IS NOT NULL
                """
            )
        )
        op.drop_table('votes')


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "votes" not in existing_tables:
        op.create_table(
            'votes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('voter_id', sa.Integer(), nullable=False),
            sa.Column('motion_id', sa.Integer(), nullable=False),
            sa.Column('option_id', sa.Integer(), nullable=False),
            sa.Column('preference_rank', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['motion_id'], ['motions.id']),
            sa.ForeignKeyConstraint(['option_id'], ['options.id']),
            sa.ForeignKeyConstraint(['voter_id'], ['voters.id']),
            sa.PrimaryKeyConstraint('id')
        )
    op.execute(
        sa.text(
            """
            INSERT INTO votes (voter_id, motion_id, option_id, preference_rank)
            SELECT voter_id, motion_id, option_id, NULL FROM yes_no_votes
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO votes (voter_id, motion_id, option_id, preference_rank)
            SELECT voter_id, motion_id, option_id, NULL FROM candidate_votes
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO votes (voter_id, motion_id, option_id, preference_rank)
            SELECT voter_id, motion_id, option_id, preference_rank FROM preference_votes
            """
        )
    )
    if "yes_no_votes" in existing_tables:
        op.drop_table('yes_no_votes')
    if "preference_votes" in existing_tables:
        op.drop_table('preference_votes')
    if "candidate_votes" in existing_tables:
        op.drop_table('candidate_votes')
    if "options" in existing_tables:
        op.drop_table("options")
    if "voters" in existing_tables:
        op.drop_table("voters")
    if "motions" in existing_tables:
        op.drop_table("motions")
    if "meetings" in existing_tables:
        op.drop_table("meetings")
    if "users" in existing_tables:
        op.drop_table("users")
