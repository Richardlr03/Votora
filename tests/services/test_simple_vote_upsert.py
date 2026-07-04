from app.models import Meeting, Motion, Option, Voter, YesNoVote
from app.services.voting.simple_vote import upsert_single_option_vote


def _yes_no_setup(db_session):
    meeting = Meeting(title="Upsert Meeting")
    db_session.add(meeting)
    db_session.flush()

    voter = Voter(
        meeting_id=meeting.id,
        student_id="610000001",
        name="Upsert Voter",
        code="UPSERT01",
    )
    motion = Motion(
        meeting_id=meeting.id,
        title="Approve budget",
        type="YES_NO",
        status="OPEN",
    )
    db_session.add_all([voter, motion])
    db_session.flush()

    yes_option = Option(motion_id=motion.id, text="Yes")
    no_option = Option(motion_id=motion.id, text="No")
    db_session.add_all([yes_option, no_option])
    db_session.commit()
    return voter, motion, yes_option, no_option


def test_upsert_inserts_then_updates_single_row(db_session):
    voter, motion, yes_option, no_option = _yes_no_setup(db_session)

    upsert_single_option_vote(
        db_session, YesNoVote, voter.id, motion.id, yes_option.id
    )
    db_session.commit()

    upsert_single_option_vote(
        db_session, YesNoVote, voter.id, motion.id, no_option.id
    )
    db_session.commit()

    votes = YesNoVote.query.filter_by(voter_id=voter.id, motion_id=motion.id).all()
    assert len(votes) == 1
    assert votes[0].option_id == no_option.id
