from app.models import Meeting, Motion, Option, PreferenceVote, User, Voter
from app.services.voting.preference import irv_tie_break_loser
from app.services.voting import tally_preference_sequential_irv


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

    voter_1 = Voter(meeting_id=meeting.id, name="V1", code="PREF0001")
    voter_2 = Voter(meeting_id=meeting.id, name="V2", code="PREF0002")
    voter_3 = Voter(meeting_id=meeting.id, name="V3", code="PREF0003")
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

    result = tally_preference_sequential_irv(motion)
    assert result["total_ballots"] == 3
    assert result["num_winners"] == 1
    assert len(result["winners"]) == 1
    assert result["winners"][0].id == option_a.id
    assert len(result["seats"]) == 1
    assert result["seats"][0]["winner"].id == option_a.id


def test_preference_tally_two_winners(db_session):
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
        Voter(meeting_id=meeting.id, name="V1", code="PREF1001"),
        Voter(meeting_id=meeting.id, name="V2", code="PREF1002"),
        Voter(meeting_id=meeting.id, name="V3", code="PREF1003"),
        Voter(meeting_id=meeting.id, name="V4", code="PREF1004"),
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

    result = tally_preference_sequential_irv(motion)
    assert result["total_ballots"] == 4
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

    result = tally_preference_sequential_irv(motion)
    assert result["total_ballots"] == 0
    assert result["num_winners"] == 1
    assert len(result["winners"]) == 0
    assert len(result["seats"]) == 0


def test_irv_tie_break_restricted_rankings_narrow_then_eliminate(db_session):
    admin = User(
        username="svc_admin_tie",
        email="svc_admin_tie@example.com",
        password_hash="hashed-password",
    )
    db_session.add(admin)
    db_session.flush()

    meeting = Meeting(title="Svc Tie Meeting", admin_id=admin.id)
    db_session.add(meeting)
    db_session.flush()

    motion = Motion(
        meeting_id=meeting.id,
        title="Preference Tie Break Vote",
        type="PREFERENCE",
        num_winners=1,
    )
    db_session.add(motion)
    db_session.flush()

    option_a = Option(motion_id=motion.id, text="Alice")
    option_b = Option(motion_id=motion.id, text="Bob")
    option_c = Option(motion_id=motion.id, text="Charlie")
    option_d = Option(motion_id=motion.id, text="Diana")
    db_session.add_all([option_a, option_b, option_c, option_d])
    db_session.flush()

    ballots = [
        [option_a.id, option_b.id, option_c.id, option_d.id],
        [option_a.id, option_c.id, option_b.id, option_d.id],
        [option_a.id, option_d.id, option_b.id, option_c.id],
        [option_b.id, option_a.id, option_c.id, option_d.id],
        [option_b.id, option_c.id, option_a.id, option_d.id],
        [option_c.id, option_a.id, option_b.id, option_d.id],
        [option_d.id, option_a.id, option_b.id, option_c.id],
    ]
    tied_candidates = [option_a.id, option_b.id, option_c.id, option_d.id]
    options_by_id = {
        option_a.id: option_a,
        option_b.id: option_b,
        option_c.id: option_c,
        option_d.id: option_d,
    }

    loser, logs = irv_tie_break_loser(ballots, tied_candidates, options_by_id)

    assert loser == option_d.id
    assert any("narrowing tie to this subset" in line for line in logs)
    assert any("is eliminated by tie-break (restricted rankings)" in line for line in logs)
