from app.models import Meeting, Motion, Option, Voter, YesNoVote


def test_voter_dashboard_invalid_code_renders_invalid_page(client):
    response = client.get("/vote/INVALID01")
    assert response.status_code == 200
    html = response.get_data(as_text=True).lower()
    assert "invalid voting link" in html


def test_qr_join_page_renders_for_open_meeting(client, db_session):
    meeting = Meeting(
        title="QR Join Meeting",
        join_token="join-token-123",
        registration_open=True,
    )
    db_session.add(meeting)
    db_session.commit()

    response = client.get("/join/meeting/join-token-123")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "QR Join Meeting" in html
    assert "Member ID" in html
    assert "Full name" in html


def test_qr_join_page_renders_custom_member_id_label(client, db_session):
    meeting = Meeting(
        title="Custom Label Meeting",
        join_token="join-token-custom",
        registration_open=True,
        member_id_label="Employee number",
    )
    db_session.add(meeting)
    db_session.commit()

    response = client.get("/join/meeting/join-token-custom")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Employee number" in html


def test_qr_join_creates_voter_and_redirects_to_dashboard(client, db_session):
    meeting = Meeting(
        title="Registration Meeting",
        join_token="join-token-abc",
        registration_open=True,
    )
    db_session.add(meeting)
    db_session.commit()

    response = client.post(
        "/join/meeting/join-token-abc",
        data={"student_id": "500123456", "name": "Taylor Smith"},
    )

    assert response.status_code == 302

    voter = Voter.query.filter_by(meeting_id=meeting.id, student_id="500123456").first()
    assert voter is not None
    assert voter.name == "Taylor Smith"
    assert response.headers["Location"].endswith(f"/vote/{voter.code}")


def test_qr_join_rejects_duplicate_student_id(client, db_session):
    meeting = Meeting(
        title="Duplicate Meeting",
        join_token="join-token-dup",
        registration_open=True,
    )
    db_session.add(meeting)
    db_session.commit()

    existing = Voter(
        meeting_id=meeting.id,
        student_id="500123456",
        name="Existing User",
        code="EXIST123",
    )
    db_session.add(existing)
    db_session.commit()

    response = client.post(
        "/join/meeting/join-token-dup",
        data={"student_id": "500123456", "name": "New User"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "already joined the meeting" in html


def test_qr_join_error_clears_after_reload(client, db_session):
    meeting = Meeting(
        title="Reload Meeting",
        join_token="join-token-reload",
        registration_open=True,
    )
    db_session.add(meeting)
    db_session.flush()

    existing = Voter(
        meeting_id=meeting.id,
        student_id="500123456",
        name="Existing User",
        code="RELOAD01",
    )
    db_session.add(existing)
    db_session.commit()

    client.post(
        "/join/meeting/join-token-reload",
        data={"student_id": "500123456", "name": "New User"},
        follow_redirects=True,
    )

    response = client.get("/join/meeting/join-token-reload")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "already joined the meeting" not in html


def test_qr_join_blocks_closed_registration(client, db_session):
    meeting = Meeting(
        title="Closed Meeting",
        join_token="join-token-closed",
        registration_open=False,
    )
    db_session.add(meeting)
    db_session.commit()

    response = client.post(
        "/join/meeting/join-token-closed",
        data={"student_id": "500123456", "name": "Taylor Smith"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Registration is closed for this meeting." in html


def _failed_commit(session):
    session.rollback()
    return False


def test_qr_join_handles_concurrent_integrity_error(client, db_session, monkeypatch):
    meeting = Meeting(
        title="Concurrent Join Meeting",
        join_token="join-token-race",
        registration_open=True,
    )
    db_session.add(meeting)
    db_session.flush()

    existing = Voter(
        meeting_id=meeting.id,
        student_id="500123456",
        name="Existing User",
        code="RACE1234",
    )
    db_session.add(existing)
    db_session.commit()

    monkeypatch.setattr("app.routes.public.commit_session", _failed_commit)

    response = client.post(
        "/join/meeting/join-token-race",
        data={"student_id": "500123456", "name": "New User"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "already joined the meeting" in html


def test_qr_join_integrity_error_without_existing_voter_shows_retry_message(
    client, db_session, monkeypatch
):
    meeting = Meeting(
        title="Retry Join Meeting",
        join_token="join-token-retry",
        registration_open=True,
    )
    db_session.add(meeting)
    db_session.commit()

    monkeypatch.setattr("app.routes.public.commit_session", _failed_commit)

    response = client.post(
        "/join/meeting/join-token-retry",
        data={"student_id": "500999999", "name": "New User"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Please try again" in html


def test_vote_motion_handles_concurrent_integrity_error(client, db_session, monkeypatch):
    meeting = Meeting(title="Vote Race Meeting")
    db_session.add(meeting)
    db_session.flush()

    voter = Voter(
        meeting_id=meeting.id,
        student_id="500888888",
        name="Vote Race Voter",
        code="VOTERACE",
    )
    motion = Motion(meeting_id=meeting.id, title="Approve budget", type="YES_NO", status="OPEN")
    db_session.add_all([voter, motion])
    db_session.flush()

    yes_option = Option(motion_id=motion.id, text="Yes")
    no_option = Option(motion_id=motion.id, text="No")
    db_session.add_all([yes_option, no_option])
    db_session.commit()

    monkeypatch.setattr("app.routes.public.commit_session", _failed_commit)

    response = client.post(
        f"/vote/{voter.code}/motion/{motion.id}",
        data={"option": str(yes_option.id)},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/vote/{voter.code}")


def test_yes_no_vote_upsert_last_choice_wins(client, db_session):
    meeting = Meeting(title="Upsert Route Meeting")
    db_session.add(meeting)
    db_session.flush()

    voter = Voter(
        meeting_id=meeting.id,
        student_id="610000002",
        name="Route Upsert Voter",
        code="UPSERT02",
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

    vote_url = f"/vote/{voter.code}/motion/{motion.id}"
    client.post(vote_url, data={"option": str(yes_option.id)})
    client.post(vote_url, data={"option": str(no_option.id)})

    votes = YesNoVote.query.filter_by(voter_id=voter.id, motion_id=motion.id).all()
    assert len(votes) == 1
    assert votes[0].option_id == no_option.id

