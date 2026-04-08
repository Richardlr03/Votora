from flask import render_template
from flask_login import login_required

from app.models import Meeting
from app.routes.admin_common import ensure_meeting_owner
from app.services.voting import (
    tally_candidate_election,
    tally_cumulative_votes,
    tally_preference_sequential_irv,
    tally_score_votes,
    tally_yes_no_abstain,
)


def register_admin_result_routes(app):
    @app.route("/admin/meetings/<int:meeting_id>/results")
    @login_required
    def meeting_results(meeting_id):
        meeting = Meeting.query.get_or_404(meeting_id)
        ensure_meeting_owner(meeting)
        results = []

        for motion in meeting.motions:
            if motion.type == "PREFERENCE":
                pref_result = tally_preference_sequential_irv(motion)
                results.append(
                    {
                        "motion": motion,
                        "result_type": motion.type,
                        "pref": pref_result,
                    }
                )
                continue

            if motion.type == "FPTP":
                candidate_result = tally_candidate_election(motion)
                results.append(
                    {
                        "motion": motion,
                        "result_type": motion.type,
                        "fptp": candidate_result,
                    }
                )
                continue

            if motion.type == "SCORE":
                score_result = tally_score_votes(motion)
                results.append(
                    {
                        "motion": motion,
                        "result_type": motion.type,
                        "score": score_result,
                    }
                )
                continue

            if motion.type == "CUMULATIVE":
                cumulative_result = tally_cumulative_votes(motion)
                results.append(
                    {
                        "motion": motion,
                        "result_type": motion.type,
                        "cumulative": cumulative_result,
                    }
                )
                continue

            results.append(
                {
                    "motion": motion,
                    "result_type": motion.type,
                    "yes_no": tally_yes_no_abstain(motion),
                }
            )

        return render_template(
            "admin/meeting_results.html",
            meeting=meeting,
            results=results,
        )

    @app.route("/admin/meetings/<int:meeting_id>/votes")
    @login_required
    def meeting_votes(meeting_id):
        meeting = Meeting.query.get_or_404(meeting_id)
        ensure_meeting_owner(meeting)
        motions_detail = []

        for motion in meeting.motions:
            voter_map = {}
            if motion.type == "PREFERENCE":
                votes_for_motion = motion.preference_votes
            elif motion.type == "FPTP":
                votes_for_motion = motion.candidate_votes
            elif motion.type == "CUMULATIVE":
                votes_for_motion = motion.cumulative_votes
            elif motion.type == "SCORE":
                votes_for_motion = motion.score_votes
            else:
                votes_for_motion = motion.yes_no_votes

            for vote in votes_for_motion:
                voter_map.setdefault(vote.voter_id, {"voter": vote.voter, "votes": []})
                voter_map[vote.voter_id]["votes"].append(vote)

            rows = []
            for data in voter_map.values():
                voter = data["voter"]
                vote_list = data["votes"]

                if motion.type == "PREFERENCE":
                    sorted_votes = sorted(vote_list, key=lambda item: item.preference_rank)
                    parts = []
                    for item in sorted_votes:
                        parts.append(f"{item.preference_rank}: {item.option.text}")
                    choice_display = ", ".join(parts)
                elif motion.type == "CUMULATIVE":
                    choice_display = ", ".join(
                        f"{item.option.text}: {item.points:g}" for item in vote_list
                    )
                elif motion.type == "SCORE":
                    choice_display = ", ".join(
                        f"{item.option.text}: {item.score}" for item in vote_list
                    )
                else:
                    choice_display = ", ".join(item.option.text for item in vote_list)

                rows.append({"voter": voter, "choice_display": choice_display})

            rows.sort(key=lambda row: row["voter"].name.lower())

            motions_detail.append(
                {
                    "motion": motion,
                    "rows": rows,
                    "num_voters_voted": len(voter_map),
                    "num_possible_voters": len(meeting.voters),
                }
            )

        return render_template(
            "admin/meeting_votes.html",
            meeting=meeting,
            motions_detail=motions_detail,
        )
