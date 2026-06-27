import random

from app.models import Meeting, Motion, Option, PreferenceVote, User, Voter
from app.services.voting import tally_preference_stv
from app.services.voting.preference import count_stv, parse_ballots_for_motion


def test_preference_tally_single_winner(db_session):
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
        title="Preference Vote",
        type="PREFERENCE",
        num_winners=1,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Alice")
    option_b = Option(motion_id=motion.id, text="Bob")
    option_c = Option(motion_id=motion.id, text="Charlie")
    db_session.add_all([option_a, option_b, option_c])
    db_session.flush()

    voter_1 = Voter(meeting_id=meeting.id, student_id="510000001", name="V1", code="PREF0001")
    voter_2 = Voter(meeting_id=meeting.id, student_id="510000002", name="V2", code="PREF0002")
    voter_3 = Voter(meeting_id=meeting.id, student_id="510000003", name="V3", code="PREF0003")
    db_session.add_all([voter_1, voter_2, voter_3])
    db_session.flush()

    db_session.add_all(
        [
            PreferenceVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_a.id,
                preference_rank=1,
            ),
            PreferenceVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_b.id,
                preference_rank=2,
            ),
            PreferenceVote(
                voter_id=voter_1.id,
                motion_id=motion.id,
                option_id=option_c.id,
                preference_rank=3,
            ),
            PreferenceVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_a.id,
                preference_rank=1,
            ),
            PreferenceVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_c.id,
                preference_rank=2,
            ),
            PreferenceVote(
                voter_id=voter_2.id,
                motion_id=motion.id,
                option_id=option_b.id,
                preference_rank=3,
            ),
            PreferenceVote(
                voter_id=voter_3.id,
                motion_id=motion.id,
                option_id=option_b.id,
                preference_rank=1,
            ),
            PreferenceVote(
                voter_id=voter_3.id,
                motion_id=motion.id,
                option_id=option_a.id,
                preference_rank=2,
            ),
            PreferenceVote(
                voter_id=voter_3.id,
                motion_id=motion.id,
                option_id=option_c.id,
                preference_rank=3,
            ),
        ]
    )
    db_session.commit()

    result = tally_preference_stv(motion)
    assert result["total_ballots"] == 3
    assert result["num_winners"] == 1
    assert result["quota"] == 2
    assert len(result["winners"]) == 1
    assert result["winners"][0].id == option_a.id
    assert result["informal_ballots"] == []


def test_preference_tally_two_winners_elected_in_first_round(db_session):
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
        title="Preference Vote",
        type="PREFERENCE",
        num_winners=2,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Alice")
    option_b = Option(motion_id=motion.id, text="Bob")
    option_c = Option(motion_id=motion.id, text="Charlie")
    db_session.add_all([option_a, option_b, option_c])
    db_session.flush()

    voters = [
        Voter(meeting_id=meeting.id, student_id="510000101", name="V1", code="PREF1001"),
        Voter(meeting_id=meeting.id, student_id="510000102", name="V2", code="PREF1002"),
        Voter(meeting_id=meeting.id, student_id="510000103", name="V3", code="PREF1003"),
        Voter(meeting_id=meeting.id, student_id="510000104", name="V4", code="PREF1004"),
    ]
    db_session.add_all(voters)
    db_session.flush()

    rankings = [
        [option_a.id, option_b.id, option_c.id],
        [option_a.id, option_c.id, option_b.id],
        [option_b.id, option_a.id, option_c.id],
        [option_b.id, option_c.id, option_a.id],
    ]

    votes = []
    for voter, ranking in zip(voters, rankings):
        for rank, option_id in enumerate(ranking, start=1):
            votes.append(
                PreferenceVote(
                    voter_id=voter.id,
                    motion_id=motion.id,
                    option_id=option_id,
                    preference_rank=rank,
                )
            )
    db_session.add_all(votes)
    db_session.commit()

    result = tally_preference_stv(motion)
    assert result["total_ballots"] == 4
    assert result["quota"] == 2
    assert result["num_winners"] == 2
    assert len(result["winners"]) == 2
    winner_ids = {winner.id for winner in result["winners"]}
    assert option_a.id in winner_ids
    assert option_b.id in winner_ids


def test_preference_tally_no_ballots(db_session):
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
        title="Preference Vote",
        type="PREFERENCE",
        num_winners=1,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Alice")
    option_b = Option(motion_id=motion.id, text="Bob")
    db_session.add_all([option_a, option_b])
    db_session.commit()

    result = tally_preference_stv(motion)
    assert result["total_ballots"] == 0
    assert result["num_winners"] == 1
    assert result["quota"] == 0
    assert len(result["winners"]) == 0
    assert result["rounds"] == []


def test_informal_ballots_are_logged(db_session):
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
        title="Preference Vote",
        type="PREFERENCE",
        num_winners=1,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Alice")
    option_b = Option(motion_id=motion.id, text="Bob")
    db_session.add_all([option_a, option_b])
    db_session.flush()

    valid_voter = Voter(meeting_id=meeting.id, student_id="510000201", name="Valid", code="PREF2001")
    duplicate_voter = Voter(meeting_id=meeting.id, student_id="510000202", name="Duplicate", code="PREF2002")
    missing_first_voter = Voter(
        meeting_id=meeting.id, student_id="510000203", name="MissingFirst", code="PREF2003"
    )
    db_session.add_all([valid_voter, duplicate_voter, missing_first_voter])
    db_session.flush()

    db_session.add_all(
        [
            PreferenceVote(
                voter_id=valid_voter.id,
                motion_id=motion.id,
                option_id=option_a.id,
                preference_rank=1,
            ),
            PreferenceVote(
                voter_id=duplicate_voter.id,
                motion_id=motion.id,
                option_id=option_a.id,
                preference_rank=1,
            ),
            PreferenceVote(
                voter_id=duplicate_voter.id,
                motion_id=motion.id,
                option_id=option_b.id,
                preference_rank=1,
            ),
            PreferenceVote(
                voter_id=missing_first_voter.id,
                motion_id=motion.id,
                option_id=option_b.id,
                preference_rank=2,
            ),
        ]
    )
    db_session.commit()

    result = tally_preference_stv(motion)
    assert result["total_ballots"] == 1
    assert len(result["informal_ballots"]) == 2
    reasons = {entry["reason"] for entry in result["informal_ballots"]}
    assert "Duplicate preference ranks." in reasons
    assert "Missing first preference (no option ranked 1)." in reasons


def test_partial_rankings_allowed_when_rank_starts_at_one(db_session):
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
        title="Preference Vote",
        type="PREFERENCE",
        num_winners=1,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Alice")
    option_b = Option(motion_id=motion.id, text="Bob")
    option_c = Option(motion_id=motion.id, text="Charlie")
    db_session.add_all([option_a, option_b, option_c])
    db_session.flush()

    voter = Voter(meeting_id=meeting.id, student_id="510000301", name="Partial", code="PREF3001")
    db_session.add(voter)
    db_session.flush()

    db_session.add_all(
        [
            PreferenceVote(
                voter_id=voter.id,
                motion_id=motion.id,
                option_id=option_a.id,
                preference_rank=1,
            ),
            PreferenceVote(
                voter_id=voter.id,
                motion_id=motion.id,
                option_id=option_c.id,
                preference_rank=3,
            ),
        ]
    )
    db_session.commit()

    valid, informal = parse_ballots_for_motion(motion)
    assert len(valid) == 1
    assert informal == []
    assert valid[0]["preferences"] == [option_a.id, option_c.id]


def test_stv_guide_example_two_seats():
    options_by_id = {
        1: type("Option", (), {"id": 1, "text": "A"})(),
        2: type("Option", (), {"id": 2, "text": "B"})(),
        3: type("Option", (), {"id": 3, "text": "C"})(),
        4: type("Option", (), {"id": 4, "text": "D"})(),
        5: type("Option", (), {"id": 5, "text": "E"})(),
    }

    ballots = []
    for index in range(60):
        if index < 30:
            ballots.append([1, 2, 3, 4])
        elif index < 50:
            ballots.append([1, 3, 2, 4])
        else:
            ballots.append([1])

    ballots.extend([[2, 3, 4, 5] for _ in range(20)])
    ballots.extend([[3, 4, 5, 2] for _ in range(10)])
    ballots.extend([[4, 5, 2, 3] for _ in range(6)])
    ballots.extend([[5, 4, 3, 2] for _ in range(4)])

    result = count_stv(ballots, 2, options_by_id, rng=random.Random(0))
    assert len(ballots) == 100
    assert result["quota"] == 34
    assert [winner.text for winner in result["winners"]] == ["A", "B"]


def test_elimination_tie_break_uses_lot_when_history_identical():
    options_by_id = {
        1: type("Option", (), {"id": 1, "text": "Alpha"})(),
        2: type("Option", (), {"id": 2, "text": "Beta"})(),
        3: type("Option", (), {"id": 3, "text": "Gamma"})(),
    }
    ballots = [
        [1, 2, 3],
        [2, 3, 1],
        [3, 1, 2],
        [1, 3, 2],
    ]

    result = count_stv(ballots, 1, options_by_id, rng=random.Random(0))
    assert len(result["winners"]) == 1
    assert any("selected by lot" in line for line in result["round_logs"])


def test_exact_quota_election_has_no_surplus_transfer():
    options_by_id = {
        1: type("Option", (), {"id": 1, "text": "A"})(),
        2: type("Option", (), {"id": 2, "text": "B"})(),
        3: type("Option", (), {"id": 3, "text": "C"})(),
    }
    ballots = [[1, 2, 3], [1, 2, 3], [1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2]]

    result = count_stv(ballots, 2, options_by_id, rng=random.Random(0))
    assert [winner.text for winner in result["winners"]] == ["A", "B"]
    assert any("No surplus to distribute" in line for line in result["round_logs"])

def test_example_1():
    options_by_id = {
        1: type("Option", (), {"id": 1, "text": "A"})(),
        2: type("Option", (), {"id": 2, "text": "B"})(),
        3: type("Option", (), {"id": 3, "text": "C"})(),
    }
    ballots = [30 * [1, 2, 3]] + [30 * [2, 1, 3]] + [40 * [3, 1, 2]]

    result = count_stv(ballots, 2, options_by_id, rng=random.Random(0))
    assert [winner.text for winner in result["winners"]] == ["A", "C"]
