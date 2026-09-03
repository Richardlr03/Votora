from datetime import datetime
from functools import wraps

from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash
from sqlalchemy import or_
import click

from app.extensions import db
from app.models import (AuditLog, CandidateVote, CumulativeVote, Flag, Meeting,
                        Motion, PreferenceVote, ScoreVote, User, YesNoVote)

VOTE_MODELS = (YesNoVote, CandidateVote, PreferenceVote, ScoreVote, CumulativeVote)


def _staff():
    return current_user if current_user.is_authenticated and current_user.is_staff else None


def staff_required(superstaff=False):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            staff = _staff()
            if not staff or staff.status != "active":
                if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                    return jsonify({"error": "Staff authentication required."}), 401
                return redirect(url_for("login"))
            if superstaff and staff.staff_role != "superstaff":
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def _payload():
    return request.get_json(silent=True) or request.form


def _vote_count(meeting_id):
    motion_ids = [item[0] for item in db.session.query(Motion.id).filter_by(meeting_id=meeting_id)]
    if not motion_ids:
        return 0
    return sum(model.query.filter(model.motion_id.in_(motion_ids), model.status == "active").count() for model in VOTE_MODELS)


def _user_summary(user):
    meetings = Meeting.query.filter_by(admin_id=user.id, status="active").all()
    return {"id": user.id, "username": user.username, "email": user.email,
            "status": user.status, "created_at": user.created_at.isoformat() if user.created_at else None,
            "active_meeting_count": len(meetings),
            "meeting_preview": [{"id": m.id, "title": m.title} for m in meetings[:3]]}


def _meeting_summary(meeting):
    host = meeting.admin
    return {"id": meeting.id, "title": meeting.title, "description": meeting.description,
            "status": meeting.status, "created_at": meeting.meeting_date.isoformat() if meeting.meeting_date else None,
            "vote_count": _vote_count(meeting.id),
            "host": {"id": host.id, "email": host.email, "username": host.username} if host else None}


def _flag_summary(flag, include_target=True):
    data = {"id": flag.id, "target_type": flag.target_type, "target_id": flag.target_id,
            "reason": flag.reason, "status": flag.status, "resolution_note": flag.resolution_note,
            "created_at": flag.created_at.isoformat() if flag.created_at else None,
            "resolved_at": flag.resolved_at.isoformat() if flag.resolved_at else None,
            "flagger": {"id": flag.flagger.id, "email": flag.flagger.email} if flag.flagger else None}
    if include_target:
        target = db.session.get(User if flag.target_type == "user" else Meeting, flag.target_id)
        data["target"] = _user_summary(target) if target and flag.target_type == "user" else (_meeting_summary(target) if target else None)
    return data


def _audit(actor_id, action, flag):
    db.session.add(AuditLog(actor_id=actor_id, action=action, target_type=flag.target_type,
                            target_id=flag.target_id, flag_id=flag.id))


def register_staff_routes(app):
    @app.route("/staff")
    @staff_required()
    def staff_dashboard():
        staff = _staff()
        users = [_user_summary(user) for user in User.query.filter_by(status="active").order_by(User.id.desc()).all()]
        meetings = [_meeting_summary(meeting) for meeting in Meeting.query.filter_by(status="active").order_by(Meeting.id.desc()).all()]
        return render_template("staff/dashboard.html", users=users, meetings=meetings, staff=staff)

    @app.route("/staff/users")
    @staff_required()
    def staff_users():
        term = (request.args.get("q") or "").strip()
        query = User.query.filter_by(status="active")
        if term:
            like = f"%{term}%"
            query = query.filter(or_(User.email.ilike(like), User.username.ilike(like)))
        users = [_user_summary(user) for user in query.order_by(User.id.desc()).all()]
        if request.args.get("format") == "json":
            return jsonify({"users": users})
        return render_template("staff/users.html", users=users, query=term, staff=_staff())

    @app.route("/staff/users/<int:user_id>")
    @staff_required()
    def staff_user_detail(user_id):
        user = User.query.filter_by(id=user_id, status="active").first_or_404()
        return jsonify(_user_summary(user))

    @app.route("/staff/meetings")
    @staff_required()
    def staff_meetings():
        term = (request.args.get("q") or "").strip()
        query = Meeting.query.filter_by(status="active")
        if term:
            query = query.filter(Meeting.title.ilike(f"%{term}%"))
        meetings = [_meeting_summary(m) for m in query.order_by(Meeting.id.desc()).all()]
        if request.args.get("format") == "json":
            return jsonify({"meetings": meetings})
        return render_template("staff/meetings.html", meetings=meetings, query=term, staff=_staff())

    @app.route("/staff/meetings/<int:meeting_id>")
    @staff_required()
    def staff_meeting_detail(meeting_id):
        meeting = Meeting.query.filter_by(id=meeting_id, status="active").first_or_404()
        if request.args.get("format") != "json":
            return render_template(
                "staff/meeting_detail.html",
                meeting=meeting,
                summary=_meeting_summary(meeting),
                staff=_staff(),
            )
        return jsonify(_meeting_summary(meeting))

    @app.route("/staff/flags", methods=["POST"])
    @staff_required()
    def create_flag():
        data = _payload()
        target_type, reason = data.get("target_type"), (data.get("reason") or "").strip()
        try:
            target_id = int(data.get("target_id"))
        except (TypeError, ValueError):
            target_id = None
        if target_type not in {"user", "meeting"} or not target_id or not reason:
            return jsonify({"error": "target_type, target_id, and reason are required."}), 400
        model = User if target_type == "user" else Meeting
        target = model.query.filter_by(id=target_id, status="active").first()
        if not target:
            return jsonify({"error": "Flag target does not exist or has already been removed."}), 404
        if Flag.query.filter_by(target_type=target_type, target_id=target_id, status="pending").first():
            return jsonify({"error": "This target already has a pending flag."}), 409
        flag = Flag(target_type=target_type, target_id=target_id, flagged_by=_staff().id, reason=reason)
        try:
            db.session.add(flag)
            db.session.flush()
            _audit(_staff().id, "flag_created", flag)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Could not create flag."}), 500
        return jsonify({"flag": _flag_summary(flag)}), 201

    @app.route("/staff/flags/mine")
    @staff_required()
    def my_flags():
        flags = Flag.query.filter_by(flagged_by=_staff().id).order_by(Flag.id.desc()).all()
        summaries = [_flag_summary(flag) for flag in flags]
        if request.args.get("format") == "json":
            return jsonify({"flags": summaries})
        return render_template("staff/my_flags.html", flags=summaries, staff=_staff())

    @app.route("/staff/flags/pending")
    @staff_required(superstaff=True)
    def pending_flags():
        flags = Flag.query.filter_by(status="pending").order_by(Flag.created_at.asc()).all()
        cards = [_flag_summary(flag) for flag in flags]
        if request.accept_mimetypes.accept_html and not request.is_json:
            return render_template("staff/review_queue.html", flags=cards, staff=_staff())
        return jsonify({"flags": cards})

    @app.route("/staff/review", methods=["GET"])
    @staff_required(superstaff=True)
    def staff_review_queue():
        flags = [_flag_summary(flag) for flag in Flag.query.filter_by(status="pending").order_by(Flag.created_at.asc()).all()]
        return render_template("staff/review_queue.html", flags=flags, staff=_staff())

    @app.route("/staff/flags/<int:flag_id>/approve", methods=["POST"])
    @staff_required(superstaff=True)
    def approve_flag(flag_id):
        flag = Flag.query.filter_by(id=flag_id, status="pending").with_for_update().first_or_404()
        actor = _staff()
        try:
            if flag.target_type == "user":
                user = User.query.filter_by(id=flag.target_id, status="active").with_for_update().first()
                if not user:
                    return jsonify({"error": "Target is already removed."}), 409
                user.status = "removed"
                meetings = Meeting.query.filter_by(admin_id=user.id, status="active").all()
            else:
                meeting = Meeting.query.filter_by(id=flag.target_id, status="active").with_for_update().first()
                if not meeting:
                    return jsonify({"error": "Target is already removed."}), 409
                meetings = [meeting]
            meeting_ids = [meeting.id for meeting in meetings]
            for meeting in meetings:
                meeting.status = "removed"
            if meeting_ids:
                motion_ids = [row[0] for row in db.session.query(Motion.id).filter(Motion.meeting_id.in_(meeting_ids))]
                for model in VOTE_MODELS:
                    if motion_ids:
                        model.query.filter(model.motion_id.in_(motion_ids), model.status == "active").update({"status": "invalidated"}, synchronize_session=False)
            flag.status, flag.resolved_by, flag.resolved_at = "approved", actor.id, datetime.utcnow()
            _audit(actor.id, "flag_approved", flag)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Could not approve flag; no changes were applied."}), 500
        return jsonify({"flag": _flag_summary(flag)})

    @app.route("/staff/flags/<int:flag_id>/reject", methods=["POST"])
    @staff_required(superstaff=True)
    def reject_flag(flag_id):
        note = (_payload().get("resolution_note") or "").strip()
        if not note:
            return jsonify({"error": "resolution_note is required."}), 400
        flag = Flag.query.filter_by(id=flag_id, status="pending").with_for_update().first_or_404()
        try:
            flag.status, flag.resolved_by, flag.resolved_at, flag.resolution_note = "rejected", _staff().id, datetime.utcnow(), note
            _audit(_staff().id, "flag_rejected", flag)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Could not reject flag."}), 500
        return jsonify({"flag": _flag_summary(flag)})

    @app.cli.command("create-staff")
    @click.argument("email")
    @click.argument("password")
    @click.option("--role", type=click.Choice(["staff", "superstaff"]), default="staff")
    @click.option("--username", default=None)
    def create_staff_command(email, password, role, username):
        """Provision an internal staff account (there is no public signup)."""
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            raise click.ClickException("A user account with that email already exists.")
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        username = (username or email.split("@", 1)[0]).strip()
        if User.query.filter_by(username=username).first():
            raise click.ClickException("Choose a unique username with --username.")
        db.session.add(User(email=email, username=username, is_staff=True, staff_role=role,
                            password_hash=generate_password_hash(password, method="pbkdf2:sha256")))
        db.session.commit()
        click.echo(f"Created {role} account for {email}.")
