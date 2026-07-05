from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.routes.admin_common import is_dev_admin
from app.services.support_email import is_valid_email, send_support_reply


def register_admin_support_routes(app):
    @app.route("/admin/support-reply", methods=["GET", "POST"])
    @login_required
    def admin_support_reply():
        if not is_dev_admin():
            allowed = current_app.config.get("DEV_ADMIN_USERNAMES") or []
            if not allowed:
                flash(
                    "Support reply is not configured yet. Set DEV_ADMIN_USERNAMES on the server "
                    f"to include your username ({current_user.username}).",
                    "warning",
                )
            else:
                flash(
                    f"Support reply access is restricted. Your username is '{current_user.username}'. "
                    "Ask the site owner to add it to DEV_ADMIN_USERNAMES.",
                    "warning",
                )
            return redirect(url_for("admin_meetings"))

        prefill_to = (request.args.get("to") or "").strip()

        if request.method == "POST":
            to_email = (request.form.get("to_email") or "").strip().lower()
            subject = (request.form.get("subject") or "").strip()
            message = (request.form.get("message") or "").strip()

            if not is_valid_email(to_email):
                flash("Please enter a valid recipient email address.", "support_error")
                return redirect(url_for("admin_support_reply", to=to_email))

            if not subject:
                flash("Subject is required.", "support_error")
                return redirect(url_for("admin_support_reply", to=to_email))

            if not message:
                flash("Message is required.", "support_error")
                return redirect(url_for("admin_support_reply", to=to_email))

            if len(subject) > 200:
                flash("Subject must be 200 characters or fewer.", "support_error")
                return redirect(url_for("admin_support_reply", to=to_email))

            if len(message) > 8000:
                flash("Message must be 8000 characters or fewer.", "support_error")
                return redirect(url_for("admin_support_reply", to=to_email))

            try:
                send_support_reply(to_email, subject, message)
            except Exception as exc:
                current_app.logger.exception(exc)
                flash(f"Email failed: {exc}", "support_error")
                return redirect(url_for("admin_support_reply", to=to_email))

            flash(f"Email sent to {to_email}.", "success")
            return redirect(url_for("admin_support_reply"))

        return render_template(
            "admin/support_reply.html",
            prefill_to=prefill_to,
        )
