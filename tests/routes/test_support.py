from unittest.mock import patch


def test_support_page_get(client):
    response = client.get("/support")
    assert response.status_code == 200
    assert b"Report a bug" in response.data

@patch("app.routes.public.send_feedback_report")
def test_support_form_submission(mock_send, client):
    response = client.post(
        "/support",
        data={
            "email": "leader@example.com",
            "role": "admin",
            "page_url": "https://www.votora.me/admin/meetings",
            "browser_device": "Safari on iPhone",
            "description": "Results page did not load.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Thanks" in response.data
    mock_send.assert_called_once()


def test_support_form_rejects_invalid_email(client):
    response = client.post(
        "/support",
        data={
            "email": "not-an-email",
            "role": "voter",
            "description": "Broken",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"valid email" in response.data


def test_admin_support_reply_hidden_for_normal_admin(client, app, admin_user):
    with client.session_transaction() as session:
        session["_user_id"] = str(admin_user.id)
        session["_fresh"] = True

    response = client.get("/admin/support-reply", follow_redirects=True)
    assert response.status_code == 200
    assert b"Support reply access is restricted" in response.data or b"WARNING" in response.data


@patch("app.routes.admin_support.send_support_reply")
def test_admin_support_reply_for_dev_admin(mock_send, client, app, admin_user):
    app.config["DEV_ADMIN_USERNAMES"] = [admin_user.username]

    with client.session_transaction() as session:
        session["_user_id"] = str(admin_user.id)
        session["_fresh"] = True

    response = client.get("/admin/support-reply")
    assert response.status_code == 200
    assert b"Developer mode" in response.data

    response = client.post(
        "/admin/support-reply",
        data={
            "to_email": "user@example.com",
            "subject": "Issue resolved",
            "message": "This should be working now.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Email sent" in response.data
    mock_send.assert_called_once_with(
        "user@example.com",
        "Issue resolved",
        "This should be working now.",
    )


def test_nav_hides_support_reply_for_normal_admin(client, app, admin_user):
    with client.session_transaction() as session:
        session["_user_id"] = str(admin_user.id)
        session["_fresh"] = True

    response = client.get("/admin/meetings")
    assert response.status_code == 200
    assert b"Support reply" not in response.data


def test_nav_shows_support_reply_for_dev_admin(client, app, admin_user):
    app.config["DEV_ADMIN_USERNAMES"] = [admin_user.username]

    with client.session_transaction() as session:
        session["_user_id"] = str(admin_user.id)
        session["_fresh"] = True

    response = client.get("/admin/meetings")
    assert response.status_code == 200
    assert b"Support reply" in response.data
