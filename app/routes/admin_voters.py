from flask import flash, jsonify, redirect, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import (
    CandidateVote,
    CumulativeVote,
    Meeting,
    PreferenceVote,
    ScoreVote,
    Voter,
    YesNoVote,
)
from app.routes.admin_common import ensure_meeting_owner
from app.services.security import generate_voter_code


def register_admin_voter_routes(app):
    @app.route("/admin/meetings/<int:meeting_id>/voters/new", methods=["GET", "POST"])
    @login_required
    def create_voter(meeting_id):
        meeting = Meeting.query.get_or_404(meeting_id)
        ensure_meeting_owner(meeting)

        if request.method == "POST":
            student_id = (request.form.get("student_id") or "").strip()
            name = (request.form.get("name") or "").strip()
            if not student_id:
                error = {"ok": False, "error": "Student ID is required."}
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return error, 400
                flash(error["error"], "error")
                return redirect(url_for("meeting_detail", meeting_id=meeting.id))

            if not name:
                error = {"ok": False, "error": "Voter name is required."}
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return error, 400
                flash(error["error"], "error")
                return redirect(url_for("meeting_detail", meeting_id=meeting.id))

            existing_voter = Voter.query.filter_by(
                meeting_id=meeting.id, student_id=student_id
            ).first()
            if existing_voter:
                error = {
                    "ok": False,
                    "error": "Voter with the Stdudent ID has already joined",
                }
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return error, 400
                flash(error["error"], "error")
                return redirect(url_for("meeting_detail", meeting_id=meeting.id))

            voter = Voter(
                meeting_id=meeting.id,
                student_id=student_id,
                name=name,
                code=generate_voter_code(),
            )
            db.session.add(voter)
            db.session.commit()

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return {
                    "ok": True,
                    "voter": {
                        "id": voter.id,
                        "student_id": voter.student_id,
                        "name": voter.name,
                        "code": voter.code,
                    },
                }

            flash("Voter added successfully.", "success")
            return redirect(url_for("meeting_detail", meeting_id=meeting.id))

        flash("Voter added successfully.", "success")
        return redirect(url_for("meeting_detail", meeting_id=meeting.id))

    @app.route("/admin/voter/<int:voter_id>/update", methods=["POST"])
    @login_required
    def update_user(voter_id):
        voter = Voter.query.get_or_404(voter_id)
        ensure_meeting_owner(voter.meeting)
        new_student_id = (request.form.get("student_id") or "").strip()
        new_name = (request.form.get("name") or "").strip()

        if not new_student_id:
            return jsonify({"error": "Student ID is required"}), 400

        if not new_name:
            return jsonify({"error": "Voter name is required"}), 400

        existing_voter = Voter.query.filter(
            Voter.meeting_id == voter.meeting_id,
            Voter.student_id == new_student_id,
            Voter.id != voter.id,
        ).first()
        if existing_voter:
            return jsonify({"error": "Student ID has already joined this meeting"}), 400

        try:
            voter.student_id = new_student_id
            voter.name = new_name
            db.session.commit()
            flash("Voter updated successfully.", "success")
            return jsonify({"success": True}), 200
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Database error: Could not update voter"}), 500

    @app.route("/admin/voter/<int:voter_id>/delete", methods=["POST"])
    @login_required
    def delete_user(voter_id):
        voter = Voter.query.get_or_404(voter_id)
        ensure_meeting_owner(voter.meeting)

        try:
            YesNoVote.query.filter_by(voter_id=voter.id).delete(synchronize_session=False)
            CandidateVote.query.filter_by(voter_id=voter.id).delete(
                synchronize_session=False
            )
            PreferenceVote.query.filter_by(voter_id=voter.id).delete(
                synchronize_session=False
            )
            ScoreVote.query.filter_by(voter_id=voter.id).delete(
                synchronize_session=False
            )
            CumulativeVote.query.filter_by(voter_id=voter.id).delete(
                synchronize_session=False
            )
            db.session.delete(voter)
            db.session.commit()
            flash("Voter deleted successfully.", "success")
            return jsonify({"success": True}), 200
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Database error: Could not delete voter"}), 500
