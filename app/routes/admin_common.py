from datetime import datetime

from flask import abort
from flask_login import current_user


def parse_time_value(raw_value):
    if not raw_value:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(raw_value, fmt).time()
        except ValueError:
            continue
    return None


def parse_date_value(raw_value):
    if not raw_value:
        return None
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d").date()
    except ValueError:
        return None


def validate_meeting_schedule(meeting_date_raw, start_time_raw, end_time_raw):
    meeting_date = parse_date_value(meeting_date_raw)
    start_time = parse_time_value(start_time_raw)
    end_time = parse_time_value(end_time_raw)

    if meeting_date_raw and meeting_date is None:
        return meeting_date, start_time, end_time, "Invalid meeting date format."
    if start_time_raw and start_time is None:
        return meeting_date, start_time, end_time, "Invalid start time format."
    if end_time_raw and end_time is None:
        return meeting_date, start_time, end_time, "Invalid end time format."

    if bool(start_time_raw) != bool(end_time_raw):
        return (
            meeting_date,
            start_time,
            end_time,
            "Start time and end time must both be provided.",
        )

    if (start_time_raw or end_time_raw) and not meeting_date_raw:
        return (
            meeting_date,
            start_time,
            end_time,
            "Meeting date is required when start/end time is set.",
        )

    if start_time and end_time and end_time <= start_time:
        return (
            meeting_date,
            start_time,
            end_time,
            "End time must be later than start time.",
        )

    return meeting_date, start_time, end_time, None


def ensure_meeting_owner(meeting):
    if meeting.admin_id != current_user.id:
        abort(403)
