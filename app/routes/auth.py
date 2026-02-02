from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User
from app.services.security import (
    generate_reset_token,
    send_reset_email,
    verify_reset_token,
)


def register_auth_routes(app):
    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")

            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
            )

            try:
                db.session.add(new_user)
                db.session.commit()
                flash("Account created successfully! Please log in.", "success")
                return redirect(url_for("login"))
            except Exception:
                db.session.rollback()
                flash("Database error: Could not register user.", "danger")
                return redirect(url_for("signup"))

        return render_template("login_signup/signup.html")

    @app.route("/check-username", methods=["POST"])
    def check_username():
        data = request.get_json()
        username = data.get("username", "").strip()
        user = User.query.filter_by(username=username).first()
        return jsonify({"exists": user is not None})

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None

        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            remember = bool(request.form.get("remember"))

            user = User.query.filter_by(username=username).first()
            if not user or not check_password_hash(user.password_hash, password):
                error = "Invalid username or password."
            else:
                login_user(user, remember=remember)
                return redirect(url_for("admin_meetings"))

        return render_template("login_signup/login.html", error=error)

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            if not email:
                flash("Please enter your email address.", "reset_error")
                return redirect(url_for("forgot_password"))

            user = User.query.filter_by(email=email).first()
            if user:
                reset_token = generate_reset_token(user.email)
                reset_url = url_for("reset_password", token=reset_token, _external=True)
                try:
                    send_reset_email(user.email, reset_url)
                except Exception:
                    flash(
                        "Email service is not configured. Please contact the administrator.",
                        "reset_error",
                    )
                    return redirect(url_for("forgot_password"))
            else:
                current_app.logger.warning(
                    "Password reset requested for unknown email: %s", email
                )

            flash("A reset link has been sent.", "success")
            return redirect(url_for("login"))

        return render_template("login_signup/forgot_password.html")

    @app.route("/reset-password/<token>", methods=["GET", "POST"])
    def reset_password(token):
        email = verify_reset_token(token, max_age=1800)
        if not email:
            flash("This reset link is invalid or has expired.", "reset_error")
            return redirect(url_for("forgot_password"))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("This reset link is invalid or has expired.", "reset_error")
            return redirect(url_for("forgot_password"))

        if request.method == "POST":
            new_password = request.form.get("password")
            confirm_password = request.form.get("confirm_password")

            if not new_password or not confirm_password:
                flash("Please provide a new password and confirm it.", "reset_error")
                return redirect(url_for("reset_password", token=token))

            if new_password != confirm_password:
                flash("Passwords do not match.", "reset_error")
                return redirect(url_for("reset_password", token=token))

            if len(new_password) < 8:
                flash("Password must be at least 8 characters long.", "reset_error")
                return redirect(url_for("reset_password", token=token))

            user.password_hash = generate_password_hash(
                new_password, method="pbkdf2:sha256"
            )
            db.session.commit()
            flash("Password reset successfully!", "success")
            return redirect(url_for("login"))

        return render_template("login_signup/reset_password.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))
