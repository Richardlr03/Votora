from flask import flash, jsonify, redirect, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import (
    ApprovalBallot,
    ApprovalVote,
    CandidateVote,
    CumulativeVote,
    Meeting,
    Motion,
    Option,
    PreferenceBallot,
    PreferenceVote,
    ScoreVote,
    YesNoVote,
)
from app.routes.admin_common import ensure_meeting_owner


MOTION_TYPES = ("YES_NO", "FPTP", "PREFERENCE", "SCORE", "CUMULATIVE", "APPROVAL")


def _approval_settings_from_form(form):
    threshold_type = (form.get("approval_threshold_type") or "percentage").strip()
    percentage_basis = (form.get("approval_percentage_basis") or "ballots_cast").strip()
    raw_value = (form.get("approval_threshold_value") or "").strip()

    if threshold_type not in ("percentage", "absolute"):
        raise ValueError("Choose a percentage or absolute approval threshold.")
    if percentage_basis not in ("ballots_cast", "eligible_voters"):
        raise ValueError("Choose a valid percentage denominator.")
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError("Approval threshold must be a number.") from exc
    if threshold_type == "percentage" and not 0 <= value <= 100:
        raise ValueError("Percentage threshold must be between 0 and 100.")
    if threshold_type == "absolute" and (value < 0 or not value.is_integer()):
        raise ValueError("Absolute threshold must be a whole number of zero or more.")
    return threshold_type, value, percentage_basis


def _form_error(message, meeting_id=None):
    error = {"ok": False, "error": message}
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return error, 400
    flash(message, "error")
    return redirect(url_for("meeting_detail", meeting_id=meeting_id))


def register_admin_motion_routes(app):
    @app.route("/admin/meetings/<int:meeting_id>/motions/new", methods=["GET", "POST"])
    @login_required
    def create_motion(meeting_id):
        meeting = Meeting.query.get_or_404(meeting_id)
        ensure_meeting_owner(meeting)

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            motion_type = request.form.get("type")
            candidate_text = (request.form.get("candidates") or "").strip()
            num_winners_raw = (request.form.get("num_winners") or "").strip()
            approved_threshold_raw = (
                request.form.get("approved_threshold_pct") or ""
            ).strip()

            if not title:
                error = {"ok": False, "error": "Motion title is required."}
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return error, 400
                flash(error["error"], "error")
                return redirect(url_for("meeting_detail", meeting_id=meeting.id))

            if motion_type not in MOTION_TYPES:
                return _form_error("Invalid motion type.", meeting.id)

            candidate_lines = [
                line.strip() for line in candidate_text.splitlines() if line.strip()
            ]
            if motion_type == "APPROVAL" and len(candidate_lines) < 2:
                return _form_error(
                    "Approval voting requires at least two candidates.", meeting.id
                )

            num_winners = None
            if motion_type == "PREFERENCE":
                try:
                    parsed = int(num_winners_raw) if num_winners_raw else 1
                    num_winners = parsed if parsed >= 1 else 1
                except ValueError:
                    num_winners = 1

            approved_threshold_pct = None
            if motion_type == "YES_NO":
                try:
                    parsed_threshold = (
                        float(approved_threshold_raw)
                        if approved_threshold_raw
                        else 50.0
                    )
                    approved_threshold_pct = min(max(parsed_threshold, 0.0), 100.0)
                except ValueError:
                    approved_threshold_pct = 50.0

            approval_threshold_type = None
            approval_threshold_value = None
            approval_percentage_basis = None
            if motion_type == "APPROVAL":
                try:
                    (
                        approval_threshold_type,
                        approval_threshold_value,
                        approval_percentage_basis,
                    ) = _approval_settings_from_form(request.form)
                except ValueError as exc:
                    return _form_error(str(exc), meeting.id)

            score_max = None
            if motion_type == "SCORE":
                score_max_raw = (request.form.get("score_max") or "").strip()
                try:
                    parsed_score_max = int(score_max_raw) if score_max_raw else 10
                    score_max = parsed_score_max if parsed_score_max >= 1 else 1
                except ValueError:
                    score_max = 10

            budget_points = None
            if motion_type == "CUMULATIVE":
                budget_raw = (request.form.get("budget_points") or "").strip()
                try:
                    parsed_budget = int(budget_raw) if budget_raw else 10
                    budget_points = parsed_budget if parsed_budget >= 1 else 1
                except ValueError:
                    budget_points = 10

            motion = Motion(
                meeting_id=meeting.id,
                title=title,
                type=motion_type,
                status="DRAFT",
                num_winners=num_winners,
                approved_threshold_pct=approved_threshold_pct,
                approval_threshold_type=approval_threshold_type,
                approval_threshold_value=approval_threshold_value,
                approval_percentage_basis=approval_percentage_basis,
                score_max=score_max,
                budget_points=budget_points,
            )
            db.session.add(motion)
            db.session.flush()

            if motion_type == "YES_NO":
                for option_text in ("Yes", "No", "Abstain"):
                    db.session.add(Option(motion_id=motion.id, text=option_text))
            elif motion_type in ("FPTP", "PREFERENCE", "SCORE", "CUMULATIVE", "APPROVAL"):
                for name in candidate_lines:
                    db.session.add(Option(motion_id=motion.id, text=name))

            db.session.commit()

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return {
                    "ok": True,
                    "motion": {
                        "id": motion.id,
                        "title": motion.title,
                        "type": motion.type,
                        "num_winners": motion.num_winners,
                        "approved_threshold_pct": motion.approved_threshold_pct,
                        "approval_threshold_type": motion.approval_threshold_type,
                        "approval_threshold_value": motion.approval_threshold_value,
                        "approval_percentage_basis": motion.approval_percentage_basis,
                        "score_max": motion.score_max,
                        "budget_points": motion.budget_points,
                    },
                }

            flash("Motion added successfully.", "success")
            return redirect(url_for("meeting_detail", meeting_id=meeting.id))

        flash("Motion added successfully.", "success")
        return redirect(url_for("meeting_detail", meeting_id=meeting.id))

    @app.route("/admin/motion/<int:motion_id>/update", methods=["POST"])
    @login_required
    def update_motion(motion_id):
        motion = Motion.query.get_or_404(motion_id)
        ensure_meeting_owner(motion.meeting)
        old_type = motion.type
        new_type = request.form.get("type")
        if new_type not in MOTION_TYPES:
            return jsonify({"error": "Invalid motion type."}), 400
        raw_options = request.form.get("options", "")
        option_names = [entry.strip() for entry in raw_options.splitlines() if entry.strip()]
        if new_type == "APPROVAL" and len(option_names) < 2:
            return jsonify({"error": "Approval voting requires at least two candidates."}), 400
        approval_settings = (None, None, None)
        if new_type == "APPROVAL":
            try:
                approval_settings = _approval_settings_from_form(request.form)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

        motion.title = request.form.get("title")
        motion.type = new_type
        motion.num_winners = (
            request.form.get("num_winners", type=int) or 1
            if motion.type == "PREFERENCE"
            else None
        )
        threshold_raw = (request.form.get("approved_threshold_pct") or "").strip()
        if motion.type == "YES_NO":
            try:
                parsed_threshold = float(threshold_raw) if threshold_raw else 50.0
                motion.approved_threshold_pct = min(max(parsed_threshold, 0.0), 100.0)
            except ValueError:
                motion.approved_threshold_pct = 50.0
        else:
            motion.approved_threshold_pct = None

        (
            motion.approval_threshold_type,
            motion.approval_threshold_value,
            motion.approval_percentage_basis,
        ) = approval_settings

        score_max_raw = (request.form.get("score_max") or "").strip()
        if motion.type == "SCORE":
            try:
                parsed_score_max = int(score_max_raw) if score_max_raw else 10
                motion.score_max = parsed_score_max if parsed_score_max >= 1 else 1
            except ValueError:
                motion.score_max = 10
        else:
            motion.score_max = None

        budget_raw = (request.form.get("budget_points") or "").strip()
        if motion.type == "CUMULATIVE":
            try:
                parsed_budget = int(budget_raw) if budget_raw else 10
                motion.budget_points = parsed_budget if parsed_budget >= 1 else 1
            except ValueError:
                motion.budget_points = 10
        else:
            motion.budget_points = None

        new_status = request.form.get("status")
        if new_status:
            allowed_statuses = {
                "DRAFT",
                "PENDING",
                "OPEN",
                "CLOSED",
                "APPROVED",
                "REJECTED",
                "PASSED",
                "FAILED",
            }
            if new_status not in allowed_statuses:
                return jsonify({"error": "Invalid status value"}), 400
            motion.status = new_status

        candidate_types = {"FPTP", "PREFERENCE", "SCORE", "CUMULATIVE", "APPROVAL"}
        if motion.type in candidate_types or old_type != motion.type:
            try:
                YesNoVote.query.filter_by(motion_id=motion.id).delete(
                    synchronize_session=False
                )
                CandidateVote.query.filter_by(motion_id=motion.id).delete(
                    synchronize_session=False
                )
                PreferenceVote.query.filter_by(motion_id=motion.id).delete(
                    synchronize_session=False
                )
                PreferenceBallot.query.filter_by(motion_id=motion.id).delete(
                    synchronize_session=False
                )
                ScoreVote.query.filter_by(motion_id=motion.id).delete(
                    synchronize_session=False
                )
                CumulativeVote.query.filter_by(motion_id=motion.id).delete(
                    synchronize_session=False
                )
                ApprovalVote.query.filter_by(motion_id=motion.id).delete(
                    synchronize_session=False
                )
                ApprovalBallot.query.filter_by(motion_id=motion.id).delete(
                    synchronize_session=False
                )
            except Exception:
                pass

            Option.query.filter_by(motion_id=motion.id).delete(synchronize_session=False)

            if motion.type == "YES_NO":
                for option_text in ("Yes", "No", "Abstain"):
                    db.session.add(Option(text=option_text, motion_id=motion.id))
            else:
                for name in option_names:
                    db.session.add(Option(text=name, motion_id=motion.id))

        try:
            db.session.commit()
            flash("Motion updated successfully.", "success")
            return jsonify({"success": True}), 200
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Database error: Could not update motion"}), 500

    @app.route("/admin/motion/<int:motion_id>/delete", methods=["POST"])
    @login_required
    def delete_motion(motion_id):
        motion = Motion.query.get_or_404(motion_id)
        ensure_meeting_owner(motion.meeting)

        try:
            YesNoVote.query.filter_by(motion_id=motion.id).delete(
                synchronize_session=False
            )
            CandidateVote.query.filter_by(motion_id=motion.id).delete(
                synchronize_session=False
            )
            CumulativeVote.query.filter_by(motion_id=motion.id).delete(
                synchronize_session=False
            )
            PreferenceVote.query.filter_by(motion_id=motion.id).delete(
                synchronize_session=False
            )
            PreferenceBallot.query.filter_by(motion_id=motion.id).delete(
                synchronize_session=False
            )
            ScoreVote.query.filter_by(motion_id=motion.id).delete(
                synchronize_session=False
            )
            ApprovalVote.query.filter_by(motion_id=motion.id).delete(
                synchronize_session=False
            )
            ApprovalBallot.query.filter_by(motion_id=motion.id).delete(
                synchronize_session=False
            )
            Option.query.filter_by(motion_id=motion.id).delete(synchronize_session=False)
            db.session.delete(motion)
            db.session.commit()
            flash("Motion deleted successfully.", "success")
            return jsonify({"success": True}), 200
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Database error: Could not delete motion"}), 500

    @app.route("/update_motion_status/<int:motion_id>", methods=["POST"])
    @login_required
    def update_motion_status(motion_id):
        motion = Motion.query.get_or_404(motion_id)
        ensure_meeting_owner(motion.meeting)
        new_status = request.form.get("status", "").upper()
        allowed_statuses = {"DRAFT", "OPEN", "CLOSED"}

        if new_status in allowed_statuses:
            motion.status = new_status
            db.session.commit()
            flash(f"Status updated to {new_status}", "success")
        else:
            flash("Invalid status selection.", "danger")

        return redirect(url_for("meeting_detail", meeting_id=motion.meeting_id))
