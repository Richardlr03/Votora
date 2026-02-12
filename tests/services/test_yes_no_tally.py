from app.models import YesNoVote, Meeting, Motion, Option, User, Voter
from app.services.voting.yes_no import tally_yes_no_abstain


def test_yes_no_tally(db_session):
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
        title="Yes No Vote",
        type="YES_NO",
        approved_threshold_pct=50,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Yes")
    option_b = Option(motion_id=motion.id, text="No")
    option_c = Option(motion_id=motion.id, text="Abstain")
    db_session.add_all([option_a, option_b, option_c])
    db_session.flush()

    voter_1 = Voter(meeting_id=meeting.id, name="V1", code="CODE0001")
    voter_2 = Voter(meeting_id=meeting.id, name="V2", code="CODE0002")
    db_session.add_all([voter_1, voter_2])
    db_session.flush()

    # Totals tie at 10, with identical point-level distributions -> deadlock.
    db_session.add_all(
        [
            YesNoVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_a.id,
            ),
            YesNoVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_a.id,
            ),
        ]
    )
    db_session.commit()

    result = tally_yes_no_abstain(motion)
    assert result["total_votes"] == 2
    assert result["decisive_votes"] == 2
    assert result["yes_votes"] == 2
    assert result["no_votes"] == 0
    assert result["abstain_votes"] == 0
    assert result["yes_pct_decisive"] == 100
    assert result["approved_threshold_pct"] == 50
    assert result["decision"] == "PASSED"

def test_yes_no_tally_fails(db_session):
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
        title="Yes No Vote",
        type="YES_NO",
        approved_threshold_pct=80,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Yes")
    option_b = Option(motion_id=motion.id, text="No")
    option_c = Option(motion_id=motion.id, text="Abstain")
    db_session.add_all([option_a, option_b, option_c])
    db_session.flush()

    voter_1 = Voter(meeting_id=meeting.id, name="V1", code="CODE0001")
    voter_2 = Voter(meeting_id=meeting.id, name="V2", code="CODE0002")
    db_session.add_all([voter_1, voter_2])
    db_session.flush()

    # Totals tie at 10, with identical point-level distributions -> deadlock.
    db_session.add_all(
        [
            YesNoVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_a.id,
            ),
            YesNoVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_b.id,
            ),
        ]
    )
    db_session.commit()

    result = tally_yes_no_abstain(motion)
    assert result["total_votes"] == 2
    assert result["decisive_votes"] == 2
    assert result["yes_votes"] == 1
    assert result["no_votes"] == 1
    assert result["abstain_votes"] == 0
    assert result["yes_pct_decisive"] == 50
    assert result["approved_threshold_pct"] == 80
    assert result["decision"] == "FAILED"

def test_yes_no_tally_nodecision(db_session):
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
        title="Yes No Vote",
        type="YES_NO",
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Yes")
    option_b = Option(motion_id=motion.id, text="No")
    option_c = Option(motion_id=motion.id, text="Abstain")
    db_session.add_all([option_a, option_b, option_c])
    db_session.flush()

    voter_1 = Voter(meeting_id=meeting.id, name="V1", code="CODE0001")
    voter_2 = Voter(meeting_id=meeting.id, name="V2", code="CODE0002")
    db_session.add_all([voter_1, voter_2])
    db_session.flush()

    # Totals tie at 10, with identical point-level distributions -> deadlock.
    db_session.add_all(
        [
            YesNoVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_c.id,
            ),
            YesNoVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_c.id,
            ),
        ]
    )
    db_session.commit()

    result = tally_yes_no_abstain(motion)
    assert result["total_votes"] == 2
    assert result["decisive_votes"] == 0
    assert result["yes_votes"] == 0
    assert result["no_votes"] == 0
    assert result["abstain_votes"] == 2
    assert result["approved_threshold_pct"] == 50
    assert result["decision"] == "NO_DECISION"