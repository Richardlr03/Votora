def validate_approval_ballot(option_ids, none_above, valid_option_ids):
    """Validate and normalize one approval ballot.

    An empty approval list is a valid ballot. "None of the above" is also valid,
    but it cannot be combined with candidate approvals.
    """
    option_ids = list(option_ids)
    if none_above and option_ids:
        raise ValueError(
            "None of the above cannot be selected with candidate approvals."
        )
    if len(option_ids) != len(set(option_ids)):
        raise ValueError("A candidate can only be approved once per ballot.")
    if not set(option_ids).issubset(set(valid_option_ids)):
        raise ValueError("The ballot contains an invalid candidate.")
    return option_ids


def tally_approval_votes(motion):
    options_by_id = {option.id: option for option in motion.options}
    counts = {option_id: 0 for option_id in options_by_id}
    active_ballots = {
        ballot.voter_id: ballot
        for ballot in motion.approval_ballots
        if ballot.status == "active"
    }

    for vote in motion.approval_votes:
        if (
            vote.status == "active"
            and vote.voter_id in active_ballots
            and not active_ballots[vote.voter_id].none_above
            and vote.option_id in counts
        ):
            counts[vote.option_id] += 1

    ballot_count = len(active_ballots)
    eligible_voters = len(motion.meeting.voters)
    none_above_count = sum(ballot.none_above for ballot in active_ballots.values())
    threshold_type = motion.approval_threshold_type or "percentage"
    threshold_value = float(motion.approval_threshold_value or 0)
    percentage_basis = motion.approval_percentage_basis or "ballots_cast"
    denominator = eligible_voters if percentage_basis == "eligible_voters" else ballot_count

    if threshold_type == "absolute":
        threshold_count = threshold_value
        threshold_percent = (
            threshold_value / denominator * 100 if denominator > 0 else 0
        )
    else:
        threshold_percent = threshold_value
        threshold_count = denominator * threshold_value / 100

    candidate_results = []
    for option in motion.options:
        count = counts[option.id]
        percent = count / denominator * 100 if denominator > 0 else 0
        elected = count >= threshold_count
        if threshold_type == "percentage" and denominator == 0:
            elected = False
        candidate_results.append(
            {
                "option": option,
                "count": count,
                "percent": percent,
                "elected": elected,
            }
        )

    candidate_results.sort(
        key=lambda row: (-row["count"], row["option"].text.lower(), row["option"].id)
    )
    return {
        "ballot_count": ballot_count,
        "eligible_voters": eligible_voters,
        "none_above_count": none_above_count,
        "threshold_type": threshold_type,
        "threshold_value": threshold_value,
        "percentage_basis": percentage_basis,
        "denominator": denominator,
        "threshold_count": threshold_count,
        "threshold_percent": threshold_percent,
        "threshold_line_percent": min(max(threshold_percent, 0), 100),
        "candidate_results": candidate_results,
        "elected": [row["option"] for row in candidate_results if row["elected"]],
    }

