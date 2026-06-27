import random
from fractions import Fraction

STATUS_CONTINUING = "continuing"
STATUS_ELECTED = "elected"
STATUS_ELIMINATED = "eliminated"


def format_tally(value):
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        return f"{float(value):.6f}".rstrip("0").rstrip(".")
    return str(value)


def parse_ballots_for_motion(motion):
    votes_by_voter = {}
    for vote in motion.preference_votes:
        entry = votes_by_voter.setdefault(
            vote.voter_id,
            {"voter": vote.voter, "votes": []},
        )
        entry["votes"].append(vote)

    valid_ballots = []
    informal_ballots = []
    valid_option_ids = {option.id for option in motion.options}

    for data in votes_by_voter.values():
        voter = data["voter"]
        votes = data["votes"]

        if not votes:
            informal_ballots.append(
                {
                    "voter": voter,
                    "reason": "Blank ballot (no preferences submitted).",
                }
            )
            continue

        ranked = [(vote.preference_rank, vote.option_id) for vote in votes]

        if not any(rank == 1 for rank, _ in ranked):
            informal_ballots.append(
                {
                    "voter": voter,
                    "reason": "Missing first preference (no option ranked 1).",
                }
            )
            continue

        ranks = [rank for rank, _ in ranked]
        if any(rank <= 0 for rank in ranks):
            informal_ballots.append(
                {
                    "voter": voter,
                    "reason": "Invalid preference rank (must be positive).",
                }
            )
            continue

        if len(ranks) != len(set(ranks)):
            informal_ballots.append(
                {
                    "voter": voter,
                    "reason": "Duplicate preference ranks.",
                }
            )
            continue

        sorted_preferences = [
            option_id
            for _, option_id in sorted(ranked, key=lambda item: item[0])
            if option_id in valid_option_ids
        ]

        if not sorted_preferences:
            informal_ballots.append(
                {
                    "voter": voter,
                    "reason": "Blank ballot (no valid options ranked).",
                }
            )
            continue

        valid_ballots.append(
            {
                "voter": voter,
                "preferences": sorted_preferences,
            }
        )

    return valid_ballots, informal_ballots


def build_ballots_for_motion(motion):
    valid_ballots, _informal_ballots = parse_ballots_for_motion(motion)
    return [ballot["preferences"] for ballot in valid_ballots]


class _STVBallot:
    __slots__ = ("preferences", "transfer_value", "active_preference", "exhausted")

    def __init__(self, preferences):
        self.preferences = preferences
        self.transfer_value = Fraction(1, 1)
        self.active_preference = 0
        self.exhausted = False


class _CandidateState:
    __slots__ = (
        "option_id",
        "status",
        "pile",
        "tally_history",
        "elected_round",
        "eliminated_round",
    )

    def __init__(self, option_id):
        self.option_id = option_id
        self.status = STATUS_CONTINUING
        self.pile = []
        self.tally_history = []
        self.elected_round = None
        self.eliminated_round = None


def _dropp_quota(num_ballots, num_seats):
    return num_ballots // (num_seats + 1) + 1


def _compute_tallies(candidates):
    tallies = {}
    for candidate in candidates.values():
        tally = Fraction(0, 1)
        for ballot in candidate.pile:
            tally += ballot.transfer_value
        tallies[candidate.option_id] = tally
        candidate.tally_history.append(tally)
    return tallies


def _next_continuing(ballot, candidates):
    while ballot.active_preference < len(ballot.preferences):
        option_id = ballot.preferences[ballot.active_preference]
        ballot.active_preference += 1
        candidate = candidates.get(option_id)
        if candidate and candidate.status == STATUS_CONTINUING:
            return candidate
    return None


def _snapshot_round(candidates, options_by_id, round_number, quota):
    counts = []
    for option_id in sorted(options_by_id):
        candidate = candidates[option_id]
        tally = candidate.tally_history[-1] if candidate.tally_history else Fraction(0, 1)
        counts.append(
            {
                "option": options_by_id[option_id],
                "count": format_tally(tally),
                "count_value": tally,
                "status": candidate.status,
            }
        )
    return {
        "round_number": round_number,
        "counts": counts,
        "quota": quota,
        "total": sum(
            (row["count_value"] for row in counts if row["status"] == STATUS_CONTINUING),
            Fraction(0, 1),
        ),
    }


def _pick_elimination_loser(tied_ids, candidates, options_by_id, round_logs, rng):
    if len(tied_ids) == 1:
        return tied_ids[0]

    names = ", ".join(options_by_id[cid].text for cid in sorted(tied_ids))
    max_history = max(len(candidates[cid].tally_history) for cid in tied_ids)

    for index in range(max_history - 1, -1, -1):
        values = {cid: candidates[cid].tally_history[index] for cid in tied_ids}
        min_value = min(values.values())
        lowest = [cid for cid, value in values.items() if value == min_value]
        if len(lowest) == 1:
            loser = lowest[0]
            round_logs.append(
                f"Tie for elimination among {names}. "
                f"{options_by_id[loser].text} had the lower tally in an earlier round and is eliminated."
            )
            return loser

    loser = rng.choice(sorted(tied_ids))
    round_logs.append(
        f"Tie for elimination among {names} could not be resolved by prior tallies. "
        f"{options_by_id[loser].text} was selected by lot."
    )
    return loser


def count_stv(valid_ballot_preferences, num_seats, options_by_id, rng=None):
    rng = rng or random.Random()
    round_logs = []
    rounds = []

    if num_seats < 1:
        num_seats = 1

    num_ballots = len(valid_ballot_preferences)
    quota = _dropp_quota(num_ballots, num_seats) if num_ballots else 0

    candidates = {
        option_id: _CandidateState(option_id) for option_id in options_by_id
    }
    ballots = [_STVBallot(preferences) for preferences in valid_ballot_preferences]

    for ballot in ballots:
        option_id = ballot.preferences[0]
        ballot.active_preference = 1
        candidates[option_id].pile.append(ballot)

    round_number = 0
    seats_filled = 0
    pending_surplus = []

    if num_ballots == 0:
        return {
            "winners": [],
            "quota": quota,
            "rounds": rounds,
            "round_logs": round_logs,
            "seats_filled": 0,
        }

    round_logs.append(
        f"Valid ballots (N) = {num_ballots}. Seats to fill (n) = {num_seats}. "
        f"Droop quota = floor({num_ballots} / {num_seats + 1}) + 1 = {quota}."
    )

    while True:
        round_number += 1
        tallies = _compute_tallies(candidates)
        rounds.append(_snapshot_round(candidates, options_by_id, round_number, quota))

        if seats_filled == num_seats:
            round_logs.append("All seats filled. Count complete.")
            break

        continuing = [
            candidate
            for candidate in candidates.values()
            if candidate.status == STATUS_CONTINUING
        ]
        unfilled_seats = num_seats - seats_filled

        if len(continuing) == unfilled_seats:
            for candidate in continuing:
                candidate.status = STATUS_ELECTED
                candidate.elected_round = round_number
                seats_filled += 1
                round_logs.append(
                    f"{options_by_id[candidate.option_id].text} is elected "
                    f"(remaining continuing candidates equal unfilled seats)."
                )
            rounds.append(_snapshot_round(candidates, options_by_id, round_number, quota))
            round_logs.append("All seats filled. Count complete.")
            break

        if pending_surplus:
            pending_surplus.sort(
                key=lambda item: (item["surplus"], item["tally_at_election"]),
                reverse=True,
            )
            tied_groups = {}
            for item in pending_surplus:
                key = (item["surplus"], item["tally_at_election"])
                tied_groups.setdefault(key, []).append(item)

            next_group = tied_groups[max(tied_groups.keys())]
            if len(next_group) > 1:
                names = ", ".join(
                    options_by_id[item["candidate"].option_id].text for item in next_group
                )
                rng.shuffle(next_group)
                round_logs.append(
                    f"Tie for surplus distribution order among {names}. Order determined by lot."
                )

            item = next_group[0]
            pending_surplus.remove(item)
            candidate = item["candidate"]
            surplus = item["surplus"]
            tally = item["tally_at_election"]
            ratio = surplus / tally
            pile = list(candidate.pile)
            candidate.pile.clear()

            for ballot in pile:
                ballot.transfer_value *= ratio
                next_candidate = _next_continuing(ballot, candidates)
                if next_candidate is None:
                    ballot.exhausted = True
                else:
                    next_candidate.pile.append(ballot)

            round_logs.append(
                f"Surplus from {options_by_id[candidate.option_id].text} distributed "
                f"at transfer ratio {format_tally(ratio)}."
            )
            continue

        newly_elected = [
            candidate
            for candidate in continuing
            if tallies[candidate.option_id] >= quota
        ]
        newly_elected.sort(
            key=lambda candidate: tallies[candidate.option_id],
            reverse=True,
        )

        if newly_elected:
            for candidate in newly_elected:
                candidate.status = STATUS_ELECTED
                candidate.elected_round = round_number
                seats_filled += 1
                tally = tallies[candidate.option_id]
                surplus = tally - quota
                round_logs.append(
                    f"{options_by_id[candidate.option_id].text} is elected with "
                    f"tally {format_tally(tally)} (quota {quota}, surplus {format_tally(surplus)})."
                )
                if surplus > 0:
                    pending_surplus.append(
                        {
                            "candidate": candidate,
                            "surplus": surplus,
                            "tally_at_election": tally,
                        }
                    )
                else:
                    round_logs.append(
                        f"No surplus to distribute for {options_by_id[candidate.option_id].text}."
                    )

            if seats_filled == num_seats:
                round_logs.append("All seats filled. Count complete.")
                break
            continue

        if not continuing:
            round_logs.append("No continuing candidates remain. Count stopped.")
            break

        min_tally = min(tallies[candidate.option_id] for candidate in continuing)
        lowest = [
            candidate
            for candidate in continuing
            if tallies[candidate.option_id] == min_tally
        ]
        loser_id = _pick_elimination_loser(
            [candidate.option_id for candidate in lowest],
            candidates,
            options_by_id,
            round_logs,
            rng,
        )
        loser = candidates[loser_id]
        loser.status = STATUS_ELIMINATED
        loser.eliminated_round = round_number

        if len(lowest) == 1:
            round_logs.append(
                f"{options_by_id[loser_id].text} is eliminated with the lowest tally "
                f"({format_tally(min_tally)})."
            )
        else:
            tied_names = ", ".join(
                options_by_id[candidate.option_id].text for candidate in lowest
            )
            round_logs.append(
                f"Tie for lowest tally among {tied_names}. "
                f"{options_by_id[loser_id].text} is eliminated."
            )

        pile = list(loser.pile)
        loser.pile.clear()
        for ballot in pile:
            next_candidate = _next_continuing(ballot, candidates)
            if next_candidate is None:
                ballot.exhausted = True
            else:
                next_candidate.pile.append(ballot)

    winner_ids = [
        candidate.option_id
        for candidate in candidates.values()
        if candidate.status == STATUS_ELECTED
    ]
    winner_ids.sort(
        key=lambda option_id: (
            candidates[option_id].elected_round or 0,
            option_id,
        )
    )
    winners = [options_by_id[option_id] for option_id in winner_ids]

    return {
        "winners": winners,
        "quota": quota,
        "rounds": rounds,
        "round_logs": round_logs,
        "seats_filled": seats_filled,
    }


def tally_preference_stv(motion, rng=None):
    valid_ballots, informal_ballots = parse_ballots_for_motion(motion)
    options_by_id = {option.id: option for option in motion.options}
    num_seats = motion.num_winners or 1

    stv_result = count_stv(
        [ballot["preferences"] for ballot in valid_ballots],
        num_seats,
        options_by_id,
        rng=rng,
    )

    return {
        "winners": stv_result["winners"],
        "num_winners": num_seats,
        "total_ballots": len(valid_ballots),
        "quota": stv_result["quota"],
        "rounds": stv_result["rounds"],
        "round_logs": stv_result["round_logs"],
        "informal_ballots": informal_ballots,
        "seats_filled": stv_result["seats_filled"],
    }


def tally_preference_sequential_irv(motion, rng=None):
    return tally_preference_stv(motion, rng=rng)
