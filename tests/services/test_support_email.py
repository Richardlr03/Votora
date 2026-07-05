from unittest.mock import patch

import pytest

from app.services.support_email import is_valid_email, send_feedback_report, send_support_reply


def test_is_valid_email():
    assert is_valid_email("user@example.com")
    assert not is_valid_email("not-an-email")
    assert not is_valid_email("")


def test_send_feedback_report(app):
    with app.app_context():
        with patch("app.services.support_email.resend.Emails.send") as send_mock:
            send_feedback_report(
                reporter_email="reporter@example.com",
                role="voter",
                page_url="https://www.votora.me/join/meeting/abc",
                browser_device="Chrome on Windows",
                description="The vote button did nothing.",
            )

    send_mock.assert_called_once()
    payload = send_mock.call_args[0][0]
    assert payload["to"] == ["notify@example.com"]
    assert payload["reply_to"] == ["reporter@example.com"]
    assert payload["from"] == "Votora Support <support@votora.me>"
    assert "reporter@example.com" in payload["text"]
    assert "The vote button did nothing." in payload["text"]


def test_send_feedback_report_requires_notify_email(app):
    with app.app_context():
        app.config["SUPPORT_NOTIFY_EMAIL"] = ""
        with pytest.raises(RuntimeError, match="SUPPORT_NOTIFY_EMAIL"):
            send_feedback_report(
                reporter_email="reporter@example.com",
                role="admin",
                page_url="",
                browser_device="",
                description="Help",
            )


def test_send_support_reply(app):
    with app.app_context():
        with patch("app.services.support_email.resend.Emails.send") as send_mock:
            send_support_reply(
                "user@example.com",
                "Re: Your Votora feedback",
                "Thanks — this should be fixed now.",
            )

    send_mock.assert_called_once()
    payload = send_mock.call_args[0][0]
    assert payload["to"] == ["user@example.com"]
    assert payload["from"] == "Votora Support <support@votora.me>"
    assert payload["subject"] == "Re: Your Votora feedback"
    assert "fixed now" in payload["text"]
