import smtplib
import uuid
from email.message import EmailMessage

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def generate_voter_code():
    return uuid.uuid4().hex[:8].upper()


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
    if not current_app.config["MAIL_USERNAME"] or not current_app.config["MAIL_PASSWORD"]:
        raise RuntimeError("Email credentials are not configured.")

    msg = EmailMessage()
    msg["Subject"] = "Reset your Votora password"
    msg["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    msg["To"] = to_email
    msg.set_content(
        "You requested a password reset for Votora.\n\n"
        f"Reset your password here: {reset_url}\n\n"
        "This link will expire in 30 minutes. If you did not request this, ignore this email."
    )

    with smtplib.SMTP(
        current_app.config["MAIL_SERVER"], current_app.config["MAIL_PORT"]
    ) as server:
        if current_app.config["MAIL_USE_TLS"]:
            server.starttls()
        server.login(
            current_app.config["MAIL_USERNAME"], current_app.config["MAIL_PASSWORD"]
        )
        server.send_message(msg)
        current_app.logger.info("Password reset email sent to %s", to_email)
