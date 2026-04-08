from datetime import date, time

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import (
    CandidateVote,
    CumulativeVote,
    Meeting,
    Motion,
    Option,
    PreferenceVote,
    ScoreVote,
    Voter,
    YesNoVote,
)
from app.routes.admin_common import ensure_meeting_owner, validate_meeting_schedule
from app.services.security import generate_join_token


def register_admin_meeting_routes(app):
    @app.route("/admin/meetings")
    @login_required
    def admin_meetings():
        meetings = Meeting.query.filter_by(admin_id=current_user.id).all()
        meetings.sort(
            key=lambda meeting: (
                meeting.meeting_date is None,
                meeting.meeting_date or date.max,
                meeting.start_time is None,
                meeting.start_time or time.max,
                meeting.id,
            )
        )
        return render_template("admin/meetings.html", meetings=meetings)

    @app.route("/admin/meetings/new", methods=["GET", "POST"])
    @login_required
    def create_meeting():
        if request.method == "GET":
            return redirect(url_for("admin_meetings"))

        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip() or None
        meeting_date_raw = (request.form.get("meeting_date") or "").strip()
        start_time_raw = (request.form.get("start_time") or "").strip()
        end_time_raw = (request.form.get("end_time") or "").strip()

        meeting_date, start_time, end_time, schedule_error = validate_meeting_schedule(
            meeting_date_raw, start_time_raw, end_time_raw
        )

        if not title:
            error_message = "Meeting title is required."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return {"ok": False, "error": error_message}, 400
            flash(error_message, "danger")
            return redirect(url_for("admin_meetings"))

        if schedule_error:
            error_message = schedule_error
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return {"ok": False, "error": error_message}, 400
            flash(error_message, "danger")
            return redirect(url_for("admin_meetings"))

        new_meeting = Meeting(
            title=title,
            description=description,
            meeting_date=meeting_date,
            start_time=start_time,
            end_time=end_time,
            admin_id=current_user.id,
        )
        db.session.add(new_meeting)
        db.session.commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {
                "ok": True,
                "meeting": {
                    "id": new_meeting.id,
                    "title": new_meeting.title,
                    "description": new_meeting.description,
                    "meeting_date": (
                        new_meeting.meeting_date.isoformat()
                        if new_meeting.meeting_date
                        else None
                    ),
                    "start_time": (
                        new_meeting.start_time.strftime("%H:%M")
                        if new_meeting.start_time
                        else None
                    ),
                    "end_time": (
                        new_meeting.end_time.strftime("%H:%M")
                        if new_meeting.end_time
                        else None
                    ),
                },
            }

        flash("Meeting created successfully.", "success")
        return redirect(url_for("admin_meetings"))

    @app.route("/admin/meetings/<int:meeting_id>")
    @login_required
    def meeting_detail(meeting_id):
        meeting = Meeting.query.get_or_404(meeting_id)
        ensure_meeting_owner(meeting)
        return render_template("admin/meeting_detail.html", meeting=meeting)

    @app.route("/admin/meetings/<int:meeting_id>/join-token", methods=["POST"])
    @login_required
    def generate_meeting_join_token(meeting_id):
        meeting = Meeting.query.get_or_404(meeting_id)
        ensure_meeting_owner(meeting)

        if not meeting.join_token:
            meeting.join_token = generate_join_token()

        meeting.registration_open = True
        db.session.commit()

        join_url = url_for(
            "join_meeting_by_token",
            token=meeting.join_token,
            _external=True,
        )

        return jsonify(
            {
                "ok": True,
                "meeting_id": meeting.id,
                "join_token": meeting.join_token,
                "join_url": join_url,
                "registration_open": meeting.registration_open,
            }
        )

    @app.route("/admin/meetings/<int:meeting_id>/delete", methods=["POST"])
    @login_required
    def delete_meeting(meeting_id):
        meeting = Meeting.query.get_or_404(meeting_id)
        ensure_meeting_owner(meeting)

        motion_ids = [motion.id for motion in meeting.motions]
        voter_ids = [voter.id for voter in meeting.voters]

        if motion_ids:
            YesNoVote.query.filter(YesNoVote.motion_id.in_(motion_ids)).delete(
                synchronize_session=False
            )
            CandidateVote.query.filter(CandidateVote.motion_id.in_(motion_ids)).delete(
                synchronize_session=False
            )
            CumulativeVote.query.filter(
                CumulativeVote.motion_id.in_(motion_ids)
            ).delete(synchronize_session=False)
            PreferenceVote.query.filter(PreferenceVote.motion_id.in_(motion_ids)).delete(
                synchronize_session=False
            )
            ScoreVote.query.filter(ScoreVote.motion_id.in_(motion_ids)).delete(
                synchronize_session=False
            )
            Option.query.filter(Option.motion_id.in_(motion_ids)).delete(
                synchronize_session=False
            )
            Motion.query.filter(Motion.id.in_(motion_ids)).delete(
                synchronize_session=False
            )

        if voter_ids:
            YesNoVote.query.filter(YesNoVote.voter_id.in_(voter_ids)).delete(
                synchronize_session=False
            )
            CandidateVote.query.filter(CandidateVote.voter_id.in_(voter_ids)).delete(
                synchronize_session=False
            )
            CumulativeVote.query.filter(
                CumulativeVote.voter_id.in_(voter_ids)
            ).delete(synchronize_session=False)
            PreferenceVote.query.filter(PreferenceVote.voter_id.in_(voter_ids)).delete(
                synchronize_session=False
            )
            ScoreVote.query.filter(ScoreVote.voter_id.in_(voter_ids)).delete(
                synchronize_session=False
            )
            Voter.query.filter(Voter.id.in_(voter_ids)).delete(synchronize_session=False)

        db.session.delete(meeting)
        db.session.commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": True}

        flash("Meeting deleted successfully.", "success")
        return redirect(url_for("admin_meetings"))

    @app.route("/admin/meetings/<int:meeting_id>/update", methods=["POST"])
    @login_required
    def update_meeting(meeting_id):
        meeting = Meeting.query.get_or_404(meeting_id)
        ensure_meeting_owner(meeting)

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        meeting_date_raw = (request.form.get("meeting_date") or "").strip()
        start_time_raw = (request.form.get("start_time") or "").strip()
        end_time_raw = (request.form.get("end_time") or "").strip()

        meeting_date, start_time, end_time, schedule_error = validate_meeting_schedule(
            meeting_date_raw, start_time_raw, end_time_raw
        )

        if not title:
            error_message = "Title is required."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"ok": False, "error": error_message}), 400
            flash(error_message, "danger")
            return redirect(url_for("admin_meetings"))

        if schedule_error:
            error_message = schedule_error
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"ok": False, "error": error_message}), 400
            flash(error_message, "danger")
            return redirect(url_for("admin_meetings"))

        meeting.title = title
        meeting.description = description
        meeting.meeting_date = meeting_date
        meeting.start_time = start_time
        meeting.end_time = end_time

        db.session.commit()
        flash("Meeting updated successfully.", "success")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {
                    "ok": True,
                    "meeting": {
                        "id": meeting.id,
                        "title": meeting.title,
                        "description": meeting.description,
                        "meeting_date": (
                            meeting.meeting_date.isoformat()
                            if meeting.meeting_date
                            else None
                        ),
                        "start_time": (
                            meeting.start_time.strftime("%H:%M")
                            if meeting.start_time
                            else None
                        ),
                        "end_time": (
                            meeting.end_time.strftime("%H:%M")
                            if meeting.end_time
                            else None
                        ),
                    },
                }
            )
        return redirect(url_for("meeting_detail", meeting_id=meeting_id))
