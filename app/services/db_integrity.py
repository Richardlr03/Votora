from sqlalchemy.exc import IntegrityError


def commit_session(session):
    """Commit the session, rolling back on unique constraint violations."""
    try:
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False
