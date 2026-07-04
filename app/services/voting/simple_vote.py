from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


def upsert_single_option_vote(session, vote_model, voter_id, motion_id, option_id):
    """Insert or replace the voter's single-option ballot. Last write wins."""
    table = vote_model.__table__
    values = {
        "voter_id": voter_id,
        "motion_id": motion_id,
        "option_id": option_id,
    }
    dialect_name = session.get_bind().dialect.name

    if dialect_name == "mysql":
        stmt = mysql_insert(table).values(**values)
        stmt = stmt.on_duplicate_key_update(
            option_id=stmt.inserted.option_id,
        )
    elif dialect_name == "sqlite":
        stmt = sqlite_insert(table).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["voter_id", "motion_id"],
            set_={"option_id": stmt.excluded.option_id},
        )
    else:
        raise RuntimeError(
            f"Single-option vote upsert is not supported for dialect '{dialect_name}'."
        )

    session.execute(stmt)
