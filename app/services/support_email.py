import re

import resend
from flask import current_app

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(value):
    return bool(value and _EMAIL_RE.match(value.strip()))


def _send_via_resend(payload):
    api_key = current_app.config["RESEND_API_KEY"]
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is missing.")

    resend.api_key = api_key
    resend.Emails.send(payload)


def send_feedback_report(
    reporter_email,
    role,
    page_url,
    browser_device,
    description,
):
    notify_email = (current_app.config.get("SUPPORT_NOTIFY_EMAIL") or "").strip()
    if not notify_email:
        raise RuntimeError("SUPPORT_NOTIFY_EMAIL is missing.")

    from_email = current_app.config.get("SUPPORT_FROM_EMAIL") or "Votora Support <support@votora.me>"
    role_label = role or "Not specified"
    page_label = page_url or "Not provided"
    browser_label = browser_device or "Not provided"

    text = (
        "New Votora feedback / bug report\n"
        "--------------------------------\n"
        f"From: {reporter_email}\n"
        f"Role: {role_label}\n"
        f"Page / URL: {page_label}\n"
        f"Browser / device: {browser_label}\n\n"
        "Description:\n"
        f"{description.strip()}\n"
    )

    _send_via_resend(
        {
            "from": from_email,
            "to": [notify_email],
            "reply_to": [reporter_email],
            "subject": f"[Votora Feedback] Report from {reporter_email}",
            "text": text,
        }
    )

    current_app.logger.info("Feedback report sent from %s", reporter_email)


def send_support_reply(to_email, subject, message):
    from_email = current_app.config.get("SUPPORT_FROM_EMAIL") or "Votora Support <support@votora.me>"

    _send_via_resend(
        {
            "from": from_email,
            "to": [to_email],
            "subject": subject.strip(),
            "text": message.strip(),
        }
    )

    current_app.logger.info("Support reply sent to %s", to_email)
