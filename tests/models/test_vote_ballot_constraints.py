import pytest
from sqlalchemy.exc import IntegrityError

from app.models import CandidateVote, Meeting, Motion, Option, Voter, YesNoVote


def _make_yes_no_ballot(db_session):
    meeting = Meeting(title="Constraint Meeting")
    db_session.add(meeting)
    db_session.flush()

    motion = Motion(meeting_id=meeting.id, title="Approve budget", type="YES_NO")
    voter = Voter(
        meeting_id=meeting.id,
        student_id="600000001",
        name="Constraint Voter",
        code="CONST0001",
    )
    db_session.add_all([motion, voter])
    db_session.flush()

    yes_option = Option(motion_id=motion.id, text="Yes")
    no_option = Option(motion_id=motion.id, text="No")
    db_session.add_all([yes_option, no_option])
    db_session.flush()

    db_session.add(
        YesNoVote(
            voter_id=voter.id,
            motion_id=motion.id,
            option_id=yes_option.id,
        )
    )
    db_session.commit()
    return motion, voter, yes_option, no_option


def test_yes_no_vote_allows_one_ballot_per_voter_motion(db_session):
    motion, voter, _yes_option, no_option = _make_yes_no_ballot(db_session)

    duplicate = YesNoVote(
        voter_id=voter.id,
        motion_id=motion.id,
        option_id=no_option.id,
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_candidate_vote_allows_one_ballot_per_voter_motion(db_session):
    meeting = Meeting(title="FPTP Constraint Meeting")
    db_session.add(meeting)
    db_session.flush()

    motion = Motion(meeting_id=meeting.id, title="Pick president", type="FPTP")
    voter = Voter(
        meeting_id=meeting.id,
        student_id="600000002",
        name="FPTP Voter",
        code="CONST0002",
    )
    db_session.add_all([motion, voter])
    db_session.flush()

    alice = Option(motion_id=motion.id, text="Alice")
    bob = Option(motion_id=motion.id, text="Bob")
    db_session.add_all([alice, bob])
    db_session.flush()

    db_session.add(
        CandidateVote(
            voter_id=voter.id,
            motion_id=motion.id,
            option_id=alice.id,
        )
    )
    db_session.commit()

    db_session.add(
        CandidateVote(
            voter_id=voter.id,
            motion_id=motion.id,
            option_id=bob.id,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()
