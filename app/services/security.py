import resend
import uuid
from email.message import EmailMessage

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def generate_voter_code():
    return uuid.uuid4().hex[:8].upper()


def generate_join_token():
    return uuid.uuid4().hex


def _reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_reset_token(email):
    return _reset_serializer().dumps(email, salt="password-reset")


def verify_reset_token(token, max_age=1800):
    try:
        return _reset_serializer().loads(token, salt="password-reset", max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None

def send_reset_email(to_email, reset_url):
    api_key = current_app.config["RESEND_API_KEY"]

    if not api_key:
        raise RuntimeError("RESEND_API_KEY is missing.")

    resend.api_key = api_key

    resend.Emails.send({
        "from": "Votora <noreply@votora.me>",
        "to": [to_email],
        "subject": "Reset your Votora password",
        "text": (
            "You requested a password reset for Votora.\n\n"
            f"Reset your password here:\n{reset_url}\n\n"
            "This link expires in 30 minutes.\n"
            "If you did not request this, ignore this email."
        ),
    })

    current_app.logger.info(
        "Password reset email sent to %s",
        to_email
    )
