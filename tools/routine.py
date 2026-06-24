"""
Adri — Routine tool.
Reads the weekly class schedule from routine.json and provides formatted
information about today's classes and the next upcoming class.
"""

import json
from datetime import datetime, timedelta

from config import ROUTINE_FILE, logger

# Days of the week in order (matching Python's weekday() — Monday=0)
_WEEKDAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


def _load_routine() -> dict:
    """Load the routine JSON file and return the parsed dictionary."""
    if not ROUTINE_FILE.exists():
        raise FileNotFoundError(
            f"Routine file not found at {ROUTINE_FILE}. "
            "Please copy routine_template.json to data/routine.json and fill in your schedule."
        )
    with open(ROUTINE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalise_day(day: str) -> str:
    """Normalise a day name to title-case and validate it.

    Returns the canonical day name (e.g. 'Monday'), or raises ValueError.
    """
    day = day.strip().title()
    if day not in _WEEKDAYS:
        raise ValueError(
            f"'{day}' is not a valid day. "
            f"Valid days: {', '.join(_WEEKDAYS)}."
        )
    return day


def _today_name() -> str:
    """Return the current weekday name (e.g. 'Saturday')."""
    return _WEEKDAYS[datetime.now().weekday()]


def _format_classes(day: str, classes: list[dict]) -> str:
    """Format a list of class dicts into a human-readable schedule string."""
    if not classes:
        return f"No classes scheduled for {day}."

    lines = [f"{day} schedule:"]
    for cls in classes:
        time_str = cls.get("time", "??:??")
        subject = cls.get("subject", "Unknown subject")
        room = cls.get("room", "")
        entry = f"  {time_str} — {subject}"
        if room:
            entry += f" ({room})"
        lines.append(entry)
    return "\n".join(lines)


def get_routine(day: str = "") -> str:
    """Get the class schedule for a specific day of the week.

    If no day is provided, returns today's schedule. The schedule is read
    from data/routine.json.

    Args:
        day: Day of the week (e.g. 'Monday', 'tuesday'). Defaults to today
             if left empty.

    Returns:
        A human-readable formatted schedule string, or a message saying
        there are no classes.
    """
    try:
        routine = _load_routine()
    except FileNotFoundError as e:
        logger.error(str(e))
        return str(e)

    if not day:
        day = _today_name()
        logger.info("No day specified — using today (%s)", day)
    else:
        try:
            day = _normalise_day(day)
        except ValueError as e:
            logger.warning(str(e))
            return str(e)

    logger.info("Fetching routine for %s", day)
    classes = routine.get(day, [])
    # Filter out metadata keys like "_instructions"
    if isinstance(classes, str):
        classes = []
    return _format_classes(day, classes)


def get_next_class() -> str:
    """Find the next upcoming class based on the current day and time.

    Looks at today's remaining classes first. If none are left today,
    checks the following days (up to a full week) and returns the first
    class found.

    Returns:
        A human-readable string describing the next class, its time,
        subject, and room, or a message if no classes are scheduled.
    """
    logger.info("Looking up next class")

    try:
        routine = _load_routine()
    except FileNotFoundError as e:
        logger.error(str(e))
        return str(e)

    now = datetime.now()
    current_time = now.strftime("%H:%M")

    # Check today first, then the next 6 days
    for offset in range(7):
        check_date = now + timedelta(days=offset)
        day_name = _WEEKDAYS[check_date.weekday()]
        classes = routine.get(day_name, [])
        if not isinstance(classes, list):
            continue

        for cls in classes:
            class_time = cls.get("time", "")
            # On the same day, only consider future classes
            if offset == 0 and class_time <= current_time:
                continue

            subject = cls.get("subject", "Unknown")
            room = cls.get("room", "")
            if offset == 0:
                when = f"today at {class_time}"
            elif offset == 1:
                when = f"tomorrow ({day_name}) at {class_time}"
            else:
                when = f"on {day_name} at {class_time}"

            result = f"Next class: {subject} {when}"
            if room:
                result += f" in {room}"
            result += "."
            logger.info(result)
            return result

    logger.info("No upcoming classes found in the next 7 days")
    return "No upcoming classes found in the next 7 days."


if __name__ == "__main__":
    print(get_routine())
    print()
    print(get_next_class())
