from flask import Response, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for

from app.extensions import db
from app.models import (
    CandidateVote,
    CumulativeVote,
    Meeting,
    Motion,
    PreferenceVote,
    ScoreVote,
    Voter,
    YesNoVote,
)
from app.services.db_integrity import commit_session
from app.services.security import generate_voter_code
from app.services.support_email import is_valid_email, send_feedback_report
from app.services.voting.simple_vote import upsert_single_option_vote

PUBLIC_SITEMAP_ENDPOINTS = (
    "index",
    "login",
    "signup",
    "join_meeting",
    "voting_systems",
    "forgot_password",
    "support",
    "privacy_policy",
    "terms_and_conditions",
)

JOIN_QR_FORM_SESSION_KEY = "join_qr_form"


def _normalize_join_name(name):
    return " ".join((name or "").split()).casefold()


def _voter_name_matches(voter, submitted_name):
    return _normalize_join_name(voter.name) == _normalize_join_name(submitted_name)


def _login_voter(voter, welcome_back=False):
    if welcome_back:
        flash("Welcome back! Redirecting to your voting dashboard.", "success")
    session["voter_id"] = voter.id
    session["voter_name"] = voter.name
    session["voter_code"] = voter.code
    return redirect(url_for("voter_dashboard", code=voter.code))


def _redirect_join_qr_error(token, error_message, student_id="", name=""):
    flash(error_message, "join_error")
    session[JOIN_QR_FORM_SESSION_KEY] = {
        "token": token,
        "student_id": student_id,
        "name": name,
    }
    return redirect(url_for("join_meeting_by_token", token=token))


def _handle_existing_voter_sign_in(
    existing_voter, token, member_id_label, form_student_id, form_name
):
    if _voter_name_matches(existing_voter, form_name):
        return _login_voter(existing_voter, welcome_back=True)
    return _redirect_join_qr_error(
        token,
        f"This {member_id_label.lower()} has already joined the meeting.",
        form_student_id,
        form_name,
    )


def register_public_routes(app):
    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            app.static_folder,
            "Votora_Favicon.png",
            mimetype="image/png",
        )

    @app.route("/robots.txt")
    def robots_txt():
        sitemap_url = url_for("sitemap_xml", _external=True)
        lines = [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /vote/",
            "Disallow: /join/meeting/",
            "Disallow: /check-username",
            "Disallow: /reset-password/",
            "Disallow: /update_motion_status/",
            "",
            f"Sitemap: {sitemap_url}",
        ]
        return Response("\n".join(lines) + "\n", mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap_xml():
        url_entries = []
        for endpoint in PUBLIC_SITEMAP_ENDPOINTS:
            loc = url_for(endpoint, _external=True)
            url_entries.append(f"  <url><loc>{loc}</loc></url>")

        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(url_entries)
            + "\n</urlset>\n"
        )
        return Response(xml, mimetype="application/xml")

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/join", methods=["GET", "POST"])
    def join_meeting():
        if request.method == "POST":
            raw_code = request.form.get("voter_code") or ""
            code = raw_code.strip().upper()

            if not code:
                flash("Please enter a private key.", "join_error")
                return redirect(url_for("join_meeting"))

            voter = Voter.query.filter_by(code=code).first()
            if voter:
                session["voter_id"] = voter.id
                session["voter_name"] = voter.name
                session["voter_code"] = voter.code
                return redirect(url_for("voter_dashboard", code=voter.code))

            flash("Invalid private key. Please try again.", "join_error")
            return redirect(url_for("join_meeting"))

        return render_template("voter/join.html")

    @app.route("/join/meeting/<token>", methods=["GET", "POST"])
    def join_meeting_by_token(token):
        meeting = Meeting.query.filter_by(join_token=token).first_or_404()

        form_student_id = ""
        form_name = ""

        saved_form = session.pop(JOIN_QR_FORM_SESSION_KEY, None)
        if saved_form and saved_form.get("token") == token:
            form_student_id = saved_form.get("student_id", "")
            form_name = saved_form.get("name", "")

        if request.method == "POST":
            form_student_id = (request.form.get("student_id") or "").strip().upper()
            form_name = (request.form.get("name") or "").strip()
            member_id_label = meeting.member_id_label

            if not form_student_id:
                return _redirect_join_qr_error(
                    token,
                    f"{member_id_label} is required.",
                    form_student_id,
                    form_name,
                )
            if not form_name:
                return _redirect_join_qr_error(
                    token,
                    "Full name is required.",
                    form_student_id,
                    form_name,
                )

            existing_voter = Voter.query.filter_by(
                meeting_id=meeting.id, student_id=form_student_id
            ).first()
            if existing_voter:
                return _handle_existing_voter_sign_in(
                    existing_voter,
                    token,
                    member_id_label,
                    form_student_id,
                    form_name,
                )

            if not meeting.registration_open:
                return _redirect_join_qr_error(
                    token,
                    "Registration is closed for this meeting.",
                    form_student_id,
                    form_name,
                )

            voter = Voter(
                meeting_id=meeting.id,
                student_id=form_student_id,
                name=form_name,
                code=generate_voter_code(),
            )
            db.session.add(voter)
            if commit_session(db.session):
                return _login_voter(voter)

            existing_voter = Voter.query.filter_by(
                meeting_id=meeting.id, student_id=form_student_id
            ).first()
            if existing_voter:
                return _handle_existing_voter_sign_in(
                    existing_voter,
                    token,
                    member_id_label,
                    form_student_id,
                    form_name,
                )

            return _redirect_join_qr_error(
                token,
                "Could not complete check-in due to a concurrent request. Please try again.",
                form_student_id,
                form_name,
            )

        return render_template(
            "voter/join_qr.html",
            meeting=meeting,
            registration_open=meeting.registration_open,
            form_student_id=form_student_id,
            form_name=form_name,
        )

    @app.route("/voter-logout")
    def voter_logout():
        session.pop("voter_id", None)
        session.pop("voter_name", None)
        session.pop("voter_code", None)
        return redirect(url_for("join_meeting"))

    @app.route("/voting-systems")
    def voting_systems():
        return render_template("voting_systems.html")

    @app.route("/support", methods=["GET", "POST"])
    def support():
        if request.method == "POST":
            reporter_email = (request.form.get("email") or "").strip().lower()
            role = (request.form.get("role") or "").strip()
            page_url = (request.form.get("page_url") or "").strip()
            browser_device = (request.form.get("browser_device") or "").strip()
            description = (request.form.get("description") or "").strip()

            if not is_valid_email(reporter_email):
                flash("Please enter a valid email address.", "support_error")
                return redirect(url_for("support"))

            if role not in {"admin", "voter", "other"}:
                flash("Please select your role.", "support_error")
                return redirect(url_for("support"))

            if not description:
                flash("Please describe what happened.", "support_error")
                return redirect(url_for("support"))

            if len(description) > 8000:
                flash("Description must be 8000 characters or fewer.", "support_error")
                return redirect(url_for("support"))

            if len(page_url) > 500:
                flash("Page / URL must be 500 characters or fewer.", "support_error")
                return redirect(url_for("support"))

            if len(browser_device) > 200:
                flash("Browser / device must be 200 characters or fewer.", "support_error")
                return redirect(url_for("support"))

            try:
                send_feedback_report(
                    reporter_email=reporter_email,
                    role=role,
                    page_url=page_url,
                    browser_device=browser_device,
                    description=description,
                )
            except Exception as exc:
                current_app.logger.exception(exc)
                flash(
                    "We could not send your report right now. Please try again shortly.",
                    "support_error",
                )
                return redirect(url_for("support"))

            flash(
                "Thanks — your report was sent. We'll get back to you by email if needed.",
                "success",
            )
            return redirect(url_for("support"))

        return render_template("support.html")

    @app.route("/privacy-policy")
    def privacy_policy():
        return render_template("privacy_policy.html")

    @app.route("/terms-and-conditions")
    def terms_and_conditions():
        return render_template("terms_and_conditions.html")

    @app.route("/vote/<code>")
    def voter_dashboard(code):
        voter = Voter.query.filter_by(code=code).first()

        if not voter:
            return render_template(
                "voter/motion_list.html",
                invalid=True,
                voter=None,
                meeting=None,
                motions=None,
                voted_motion_ids=set(),
            )

        meeting = voter.meeting
        motions = meeting.motions
        voted_motion_ids = {
            *{vote.motion_id for vote in voter.yes_no_votes},
            *{vote.motion_id for vote in voter.candidate_votes},
            *{vote.motion_id for vote in voter.preference_votes},
            *{vote.motion_id for vote in voter.score_votes},
            *{vote.motion_id for vote in voter.cumulative_votes},
        }

        return render_template(
            "voter/motion_list.html",
            invalid=False,
            voter=voter,
            meeting=meeting,
            motions=motions,
            voted_motion_ids=voted_motion_ids,
        )

    @app.route("/vote/<code>/motion/<int:motion_id>", methods=["GET", "POST"])
    def vote_motion(code, motion_id):
        voter = Voter.query.filter_by(code=code).first()

        if not voter:
            return render_template(
                "voter/vote_motion.html",
                invalid=True,
                voter=None,
                meeting=None,
                motion=None,
                simple_vote=None,
                preference_ranks=None,
                score_values=None,
            )

        meeting = voter.meeting
        motion = Motion.query.filter_by(id=motion_id, meeting_id=meeting.id).first_or_404()

        simple_vote = None
        preference_ranks = {}
        score_values = {}
        cumulative_values = {}
        if motion.type == "PREFERENCE":
            votes_for_motion = [
                vote for vote in voter.preference_votes if vote.motion_id == motion.id
            ]
            for vote in votes_for_motion:
                preference_ranks[vote.option_id] = vote.preference_rank
        elif motion.type == "FPTP":
            simple_vote = next(
                (vote for vote in voter.candidate_votes if vote.motion_id == motion.id),
                None,
            )
        elif motion.type == "SCORE":
            votes_for_motion = [
                vote for vote in voter.score_votes if vote.motion_id == motion.id
            ]
            for vote in votes_for_motion:
                score_values[vote.option_id] = vote.score
        elif motion.type == "CUMULATIVE":
            votes_for_motion = [
                vote for vote in voter.cumulative_votes if vote.motion_id == motion.id
            ]
            for vote in votes_for_motion:
                cumulative_values[vote.option_id] = vote.points
        else:
            simple_vote = next(
                (vote for vote in voter.yes_no_votes if vote.motion_id == motion.id),
                None,
            )

        if request.method == "POST":
            if motion.type == "PREFERENCE":
                existing_pref_votes = PreferenceVote.query.filter_by(
                    voter_id=voter.id, motion_id=motion.id
                ).all()
                for existing in existing_pref_votes:
                    db.session.delete(existing)

                ranks = []
                for option in motion.options:
                    value = request.form.get(f"opt_{option.id}_rank")
                    if not value:
                        continue
                    try:
                        rank = int(value)
                    except ValueError:
                        continue
                    if rank <= 0:
                        continue
                    ranks.append((rank, option.id))

                for rank, option_id in ranks:
                    db.session.add(
                        PreferenceVote(
                            voter_id=voter.id,
                            motion_id=motion.id,
                            option_id=option_id,
                            preference_rank=rank,
                        )
                    )
            elif motion.type == "SCORE":
                existing_score_votes = ScoreVote.query.filter_by(
                    voter_id=voter.id, motion_id=motion.id
                ).all()
                for existing in existing_score_votes:
                    db.session.delete(existing)

                for option in motion.options:
                    value = request.form.get(f"opt_{option.id}_score")
                    if value is None or value == "":
                        continue
                    try:
                        score_value = round(float(value), 1)
                    except ValueError:
                        continue
                    if score_value < 0:
                        continue
                    if motion.score_max is not None and score_value > motion.score_max:
                        score_value = float(motion.score_max)

                    db.session.add(
                        ScoreVote(
                            voter_id=voter.id,
                            motion_id=motion.id,
                            option_id=option.id,
                            score=score_value,
                        )
                    )
            elif motion.type == "CUMULATIVE":
                existing_votes = CumulativeVote.query.filter_by(
                    voter_id=voter.id, motion_id=motion.id
                ).all()
                for existing in existing_votes:
                    db.session.delete(existing)

                budget = motion.budget_points
                if budget is None:
                    flash("Budget is not set for this motion.", "danger")
                    return render_template(
                        "voter/vote_motion.html",
                        invalid=False,
                        voter=voter,
                        meeting=meeting,
                        motion=motion,
                        simple_vote=simple_vote,
                        preference_ranks=preference_ranks,
                        score_values=score_values,
                        cumulative_values=cumulative_values,
                    )

                total_points = 0.0
                cumulative_values = {}
                for option in motion.options:
                    raw_value = request.form.get(f"opt_{option.id}_points")
                    if raw_value is None or raw_value == "":
                        points_value = 0.0
                    else:
                        try:
                            points_value = float(raw_value)
                        except ValueError:
                            points_value = 0.0
                    if points_value < 0:
                        flash("Points cannot be negative.", "danger")
                        cumulative_values[option.id] = points_value
                        return render_template(
                            "voter/vote_motion.html",
                            invalid=False,
                            voter=voter,
                            meeting=meeting,
                            motion=motion,
                            simple_vote=simple_vote,
                            preference_ranks=preference_ranks,
                            score_values=score_values,
                            cumulative_values=cumulative_values,
                        )

                    total_points += points_value
                    cumulative_values[option.id] = points_value

                if abs(total_points - float(budget)) > 1e-6:
                    flash(
                        f"You must allocate exactly {budget} points.\nCurrent total: {total_points}.",
                        "danger",
                    )
                    return render_template(
                        "voter/vote_motion.html",
                        invalid=False,
                        voter=voter,
                        meeting=meeting,
                        motion=motion,
                        simple_vote=simple_vote,
                        preference_ranks=preference_ranks,
                        score_values=score_values,
                        cumulative_values=cumulative_values,
                    )

                for option in motion.options:
                    points_value = cumulative_values.get(option.id, 0.0)
                    db.session.add(
                        CumulativeVote(
                            voter_id=voter.id,
                            motion_id=motion.id,
                            option_id=option.id,
                            points=points_value,
                        )
                    )
            else:
                selected_option_id = request.form.get("option")
                if selected_option_id:
                    try:
                        option_id_int = int(selected_option_id)
                    except ValueError:
                        option_id_int = None

                    if option_id_int is not None:
                        vote_model = CandidateVote if motion.type == "FPTP" else YesNoVote
                        upsert_single_option_vote(
                            db.session,
                            vote_model,
                            voter.id,
                            motion.id,
                            option_id_int,
                        )

            commit_session(db.session)
            flash("Your vote for this motion has been recorded.", "success")
            return redirect(url_for("voter_dashboard", code=voter.code))

        return render_template(
            "voter/vote_motion.html",
            invalid=False,
            voter=voter,
            meeting=meeting,
            motion=motion,
            simple_vote=simple_vote,
            preference_ranks=preference_ranks,
            score_values=score_values,
            cumulative_values=cumulative_values,
        )
