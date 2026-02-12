from app.models import CumulativeVote, Meeting, Motion, Option, User, Voter
from app.services.voting import tally_cumulative_votes


def test_cumulative_tally_one_winner(db_session):
    admin = User(
        username="svc_admin",
        email="svc_admin@example.com",
        password_hash="hashed-password",
    )
    db_session.add(admin)
    db_session.flush()
    meeting = Meeting(title="Svc Meeting", admin_id=admin.id)
    db_session.add(meeting)
    db_session.flush()

    motion = Motion(
        meeting_id=meeting.id,
        title="Budget Vote",
        type="CUMULATIVE",
        budget_points=10,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Alice")
    option_b = Option(motion_id=motion.id, text="Bob")
    db_session.add_all([option_a, option_b])
    db_session.flush()

    voter_1 = Voter(meeting_id=meeting.id, name="V1", code="CODE0001")
    voter_2 = Voter(meeting_id=meeting.id, name="V2", code="CODE0002")
    db_session.add_all([voter_1, voter_2])
    db_session.flush()

    db_session.add_all(
        [
            CumulativeVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_a.id,
                points=10.0,
            ),
            CumulativeVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_b.id,
                points=0.0,
            ),
            CumulativeVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_a.id,
                points=5.0,
            ),
            CumulativeVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_b.id,
                points=5.0,
            ),
        ]
    )
    db_session.commit()

    result = tally_cumulative_votes(motion)
    assert result["ballot_count"] == 2
    assert result["is_tie"] is False
    assert result["deadlock"] is False
    assert len(result["winners"]) == 1
    assert result["winners"][0].id == option_a.id

def test_cumulative_tally_tiebreak_one_winner(db_session):
    admin = User(
        username="svc_admin",
        email="svc_admin@example.com",
        password_hash="hashed-password",
    )
    db_session.add(admin)
    db_session.flush()
    meeting = Meeting(title="Svc Meeting", admin_id=admin.id)
    db_session.add(meeting)
    db_session.flush()

    motion = Motion(
        meeting_id=meeting.id,
        title="Budget Vote",
        type="CUMULATIVE",
        budget_points=10,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Alice")
    option_b = Option(motion_id=motion.id, text="Bob")
    db_session.add_all([option_a, option_b])
    db_session.flush()

    voter_1 = Voter(meeting_id=meeting.id, name="V1", code="CODE0001")
    voter_2 = Voter(meeting_id=meeting.id, name="V2", code="CODE0002")
    voter_3 = Voter(meeting_id=meeting.id, name="V3", code="CODE0003")
    db_session.add_all([voter_1, voter_2, voter_3])
    db_session.flush()

    db_session.add_all(
        [
            CumulativeVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_a.id,
                points=10.0,
            ),
            CumulativeVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_b.id,
                points=0.0,
            ),
            CumulativeVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_a.id,
                points=2.0,
            ),
            CumulativeVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_b.id,
                points=8.0,
            ),
            CumulativeVote(
                voter_id=voter_3.id,
                motion_id=motion.id,
                option_id=option_a.id,
                points=3.0,
            ),
            CumulativeVote(
                voter_id=voter_3.id,
                motion_id=motion.id,
                option_id=option_b.id,
                points=7.0,
            ),
        ]
    )
    db_session.commit()

    result = tally_cumulative_votes(motion)
    assert result["ballot_count"] == 3
    assert result["is_tie"] is False
    assert result["deadlock"] is False
    assert len(result["winners"]) == 1
    assert result["winners"][0].id == option_a.id

def test_cumulative_tally_deadlock_when_point_level_distribution_matches(db_session):
    admin = User(
        username="svc_admin",
        email="svc_admin@example.com",
        password_hash="hashed-password",
    )
    db_session.add(admin)
    db_session.flush()

    meeting = Meeting(title="Svc Meeting", admin_id=admin.id)
    db_session.add(meeting)
    db_session.flush()

    motion = Motion(
        meeting_id=meeting.id,
        title="Budget Vote",
        type="CUMULATIVE",
        budget_points=10,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Alice")
    option_b = Option(motion_id=motion.id, text="Bob")
    db_session.add_all([option_a, option_b])
    db_session.flush()

    voter_1 = Voter(meeting_id=meeting.id, name="V1", code="CODE0001")
    voter_2 = Voter(meeting_id=meeting.id, name="V2", code="CODE0002")
    db_session.add_all([voter_1, voter_2])
    db_session.flush()

    # Totals tie at 10, with identical point-level distributions -> deadlock.
    db_session.add_all(
        [
            CumulativeVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_a.id,
                points=10.0,
            ),
            CumulativeVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_b.id,
                points=0.0,
            ),
            CumulativeVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_a.id,
                points=0.0,
            ),
            CumulativeVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_b.id,
                points=10.0,
            ),
        ]
    )
    db_session.commit()

    result = tally_cumulative_votes(motion)
    assert result["ballot_count"] == 2
    assert result["is_tie"] is True
    assert result["deadlock"] is True
    assert len(result["winners"]) == 2
