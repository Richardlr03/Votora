from datetime import date, time

from app.models import Meeting, Motion, Option, Voter, YesNoVote


def test_admin_meetings_sorted_by_date_then_time(db_session, auth_client, admin_user):
    db_session.add_all(
        [
            Meeting(
                title="Late Meeting",
                admin_id=admin_user.id,
                meeting_date=date(2026, 3, 2),
                start_time=time(15, 0),
                end_time=time(16, 0),
            ),
            Meeting(
                title="Early Meeting",
                admin_id=admin_user.id,
                meeting_date=date(2026, 3, 1),
                start_time=time(9, 0),
                end_time=time(10, 0),
            ),
            Meeting(
                title="No Date Meeting",
                admin_id=admin_user.id,
            ),
        ]
    )
    db_session.commit()

    response = auth_client.get("/admin/meetings")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    early_pos = html.find("Early Meeting")
    late_pos = html.find("Late Meeting")
    no_date_pos = html.find("No Date Meeting")
    assert -1 not in (early_pos, late_pos, no_date_pos)
    assert early_pos < late_pos < no_date_pos


def test_meeting_detail_for_other_admin_returns_403(
    db_session, auth_client, other_admin_user
):
    meeting = Meeting(
        title="Other Admin Meeting",
        admin_id=other_admin_user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    response = auth_client.get(f"/admin/meetings/{meeting.id}")
    assert response.status_code == 403


def test_delete_meeting_removes_related_rows(db_session, auth_client, admin_user):
    meeting = Meeting(title="Delete Me", admin_id=admin_user.id)
    db_session.add(meeting)
    db_session.flush()

    motion = Motion(meeting_id=meeting.id, title="Approve Budget", type="YES_NO")
    voter = Voter(
        meeting_id=meeting.id,
        student_id="SID123",
        name="Test Voter",
        code="delete-meeting-voter",
    )
    db_session.add_all([motion, voter])
    db_session.flush()

    option = Option(motion_id=motion.id, text="Yes")
    db_session.add(option)
    db_session.flush()

    vote = YesNoVote(voter_id=voter.id, motion_id=motion.id, option_id=option.id)
    db_session.add(vote)
    db_session.commit()
    meeting_id = meeting.id
    motion_id = motion.id
    voter_id = voter.id
    option_id = option.id
    vote_id = vote.id

    response = auth_client.post(
        f"/admin/meetings/{meeting_id}/delete",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert Meeting.query.get(meeting_id) is None
    assert Motion.query.filter_by(id=motion_id).first() is None
    assert Voter.query.filter_by(id=voter_id).first() is None
    assert Option.query.filter_by(id=option_id).first() is None
    assert YesNoVote.query.filter_by(id=vote_id).first() is None


def test_create_meeting_schedule_validation_returns_single_error(auth_client):
    response = auth_client.post(
        "/admin/meetings/new",
        data={
            "title": "Bad Schedule Meeting",
            "start_time": "16:00",
            "end_time": "15:00",
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert (
        payload["error"] == "Meeting date is required when start/end time is set."
    )


def test_generate_meeting_join_token_sets_registration_open(
    db_session, auth_client, admin_user
):
    meeting = Meeting(
        title="QR Meeting",
        admin_id=admin_user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    response = auth_client.post(
        f"/admin/meetings/{meeting.id}/join-token",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["meeting_id"] == meeting.id
    assert payload["registration_open"] is True
    assert payload["join_token"]
    assert payload["join_url"].endswith(f"/join/meeting/{payload['join_token']}")

    db_session.refresh(meeting)
    assert meeting.registration_open is True
    assert meeting.join_token == payload["join_token"]


def test_generate_meeting_join_token_reuses_existing_token(
    db_session, auth_client, admin_user
):
    meeting = Meeting(
        title="Existing Token Meeting",
        admin_id=admin_user.id,
        join_token="existingtoken123",
        registration_open=False,
    )
    db_session.add(meeting)
    db_session.commit()

    response = auth_client.post(f"/admin/meetings/{meeting.id}/join-token")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["join_token"] == "existingtoken123"
    assert payload["registration_open"] is True

    db_session.refresh(meeting)
    assert meeting.join_token == "existingtoken123"
    assert meeting.registration_open is True


def test_generate_meeting_join_token_for_other_admin_returns_403(
    db_session, auth_client, other_admin_user
):
    meeting = Meeting(
        title="Other Admin QR Meeting",
        admin_id=other_admin_user.id,
    )
    db_session.add(meeting)
    db_session.commit()

    response = auth_client.post(f"/admin/meetings/{meeting.id}/join-token")
    assert response.status_code == 403
