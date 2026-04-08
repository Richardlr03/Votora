from app.models import Meeting, Voter


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
    assert "Student ID" in html
    assert "Full name" in html


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
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "already joined the meeting" in html


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
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Registration is closed for this meeting." in html
