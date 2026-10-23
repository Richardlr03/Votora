import pytest

from app.models import ApprovalBallot, ApprovalVote, Meeting, Motion, Option, Voter
from app.services.voting.approval import (
    tally_approval_votes,
    validate_approval_ballot,
)


def _approval_setup(db_session, *, threshold_type="percentage", value=50, basis="ballots_cast"):
    meeting = Meeting(title="Approval Meeting")
    db_session.add(meeting)
    db_session.flush()
    motion = Motion(
        meeting_id=meeting.id,
        title="Elect committee",
        type="APPROVAL",
        status="OPEN",
        approval_threshold_type=threshold_type,
        approval_threshold_value=value,
        approval_percentage_basis=basis,
    )
    voters = [
        Voter(meeting_id=meeting.id, student_id=str(index), name=f"Voter {index}", code=f"APPR{index}")
        for index in range(1, 5)
    ]
    db_session.add_all([motion, *voters])
    db_session.flush()
    alice = Option(motion_id=motion.id, text="Alice")
    bob = Option(motion_id=motion.id, text="Bob")
    db_session.add_all([alice, bob])
    db_session.flush()
    return motion, voters, alice, bob


def test_percentage_threshold_counts_none_above_and_elects_at_exact_threshold(db_session):
    motion, voters, alice, bob = _approval_setup(db_session)
    db_session.add_all(
        [
            ApprovalBallot(voter_id=voters[0].id, motion_id=motion.id),
            ApprovalBallot(voter_id=voters[1].id, motion_id=motion.id),
            ApprovalBallot(voter_id=voters[2].id, motion_id=motion.id, none_above=True),
            ApprovalVote(voter_id=voters[0].id, motion_id=motion.id, option_id=alice.id),
            ApprovalVote(voter_id=voters[1].id, motion_id=motion.id, option_id=alice.id),
            ApprovalVote(voter_id=voters[0].id, motion_id=motion.id, option_id=bob.id),
        ]
    )
    db_session.commit()

    result = tally_approval_votes(motion)

    assert result["ballot_count"] == 3
    assert result["none_above_count"] == 1
    assert result["threshold_count"] == 1.5
    by_name = {row["option"].text: row for row in result["candidate_results"]}
    assert by_name["Alice"]["elected"] is True
    assert by_name["Alice"]["percent"] == pytest.approx(66.6667, rel=1e-3)
    assert by_name["Bob"]["elected"] is False


def test_eligible_voter_basis_and_absolute_threshold(db_session):
    motion, voters, alice, _bob = _approval_setup(
        db_session, threshold_type="percentage", value=50, basis="eligible_voters"
    )
    db_session.add_all(
        [
            ApprovalBallot(voter_id=voters[0].id, motion_id=motion.id),
            ApprovalBallot(voter_id=voters[1].id, motion_id=motion.id),
            ApprovalVote(voter_id=voters[0].id, motion_id=motion.id, option_id=alice.id),
            ApprovalVote(voter_id=voters[1].id, motion_id=motion.id, option_id=alice.id),
        ]
    )
    db_session.commit()
    result = tally_approval_votes(motion)
    assert result["denominator"] == 4
    assert result["threshold_count"] == 2
    assert result["candidate_results"][0]["elected"] is True

    motion.approval_threshold_type = "absolute"
    motion.approval_threshold_value = 3
    assert tally_approval_votes(motion)["candidate_results"][0]["elected"] is False


def test_ballot_validation_rejects_none_above_with_candidates():
    with pytest.raises(ValueError, match="cannot be selected"):
        validate_approval_ballot([1], True, {1, 2})


def test_ballot_validation_allows_empty_some_and_all():
    assert validate_approval_ballot([], False, {1, 2}) == []
    assert validate_approval_ballot([1], False, {1, 2}) == [1]
    assert validate_approval_ballot([1, 2], False, {1, 2}) == [1, 2]
    assert validate_approval_ballot([], True, {1, 2}) == []

