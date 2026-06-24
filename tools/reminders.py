"""
Adri — Reminders tool.
Manages persistent reminders stored as JSON with support for natural-language
time parsing and recurring daily reminders.
"""

import json
import threading
import uuid
from datetime import datetime, timedelta

import dateparser

from config import REMINDERS_FILE, logger

# Thread lock for safe file access
_file_lock = threading.Lock()


# ── Internal helpers (not exposed as tools) ─────────────────────────────────

def load_reminders() -> list[dict]:
    """Load reminders from the JSON file.

    Returns an empty list if the file doesn't exist or is unreadable.
    """
    with _file_lock:
        if not REMINDERS_FILE.exists():
            return []
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.warning("Reminders file has unexpected format — resetting")
                return []
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load reminders: %s", e)
            return []


def save_reminders(reminders: list[dict]) -> None:
    """Save the full reminders list to the JSON file."""
    with _file_lock:
        try:
            with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(reminders, f, indent=2, default=str)
        except OSError as e:
            logger.error("Failed to save reminders: %s", e)


def check_due_reminders() -> list[dict]:
    """Return reminders that are due right now (within a 60-second window).

    For recurring daily reminders, the due_time is automatically rescheduled
    to the next day after being returned. Non-recurring reminders are marked
    as completed.

    Returns:
        A list of reminder dicts that are currently due.
    """
    reminders = load_reminders()
    now = datetime.now()
    due: list[dict] = []
    changed = False

    for reminder in reminders:
        if reminder.get("completed", False):
            continue

        try:
            due_time = datetime.fromisoformat(reminder["due_time"])
        except (KeyError, ValueError):
            continue

        # Check if within 60-second window
        diff = (now - due_time).total_seconds()
        if 0 <= diff <= 60:
            due.append(reminder)
            changed = True

            if reminder.get("recurring") == "daily":
                # Reschedule to the same time tomorrow
                new_due = due_time + timedelta(days=1)
                reminder["due_time"] = new_due.isoformat()
                logger.info(
                    "Recurring reminder '%s' rescheduled to %s",
                    reminder.get("message", ""), new_due,
                )
            else:
                reminder["completed"] = True
                logger.info(
                    "Reminder '%s' marked as completed",
                    reminder.get("message", ""),
                )

    if changed:
        save_reminders(reminders)

    return due


# ── Tool functions (exposed to Gemini) ──────────────────────────────────────

def set_reminder(message: str, time_str: str, recurring: str = "") -> str:
    """Create a new reminder with natural-language time parsing.

    Parses time expressions like 'in 30 minutes', 'at 5pm',
    'tomorrow at 9am', etc. using the dateparser library.

    Args:
        message: The reminder message (e.g. 'Take medicine', 'Call mom').
        time_str: When the reminder should fire, in natural language
                  (e.g. 'in 30 minutes', 'at 5pm', 'tomorrow at 9am').
        recurring: Set to 'daily' for a daily recurring reminder.
                   Leave empty for a one-time reminder.

    Returns:
        A confirmation message with the parsed time and reminder ID,
        or an error message if the time could not be parsed.
    """
    logger.info("Setting reminder: '%s' at '%s' (recurring=%s)", message, time_str, recurring or "no")

    parsed_time = dateparser.parse(
        time_str,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )

    if parsed_time is None:
        logger.warning("Could not parse time: '%s'", time_str)
        return f"Sorry, I couldn't understand the time '{time_str}'. Try something like 'in 30 minutes' or 'tomorrow at 9am'."

    # Don't allow reminders in the past
    if parsed_time < datetime.now():
        logger.warning("Parsed time is in the past: %s", parsed_time)
        return f"The time '{time_str}' seems to be in the past ({parsed_time.strftime('%Y-%m-%d %H:%M')}). Please specify a future time."

    reminder_id = uuid.uuid4().hex[:8]
    reminder = {
        "id": reminder_id,
        "message": message,
        "due_time": parsed_time.isoformat(),
        "recurring": recurring if recurring in ("daily",) else None,
        "completed": False,
    }

    reminders = load_reminders()
    reminders.append(reminder)
    save_reminders(reminders)

    recurring_label = " (recurring daily)" if recurring == "daily" else ""
    formatted_time = parsed_time.strftime("%A, %B %d at %I:%M %p")
    logger.info("Reminder set: id=%s, due=%s", reminder_id, formatted_time)

    return (
        f"Reminder set{recurring_label}: '{message}' — "
        f"{formatted_time}. (ID: {reminder_id})"
    )


def list_reminders() -> str:
    """List all active (non-completed) reminders.

    Returns:
        A formatted list of active reminders showing their message, due
        time, and ID. Returns 'No active reminders.' if there are none.
    """
    logger.info("Listing reminders")
    reminders = load_reminders()
    active = [r for r in reminders if not r.get("completed", False)]

    if not active:
        return "No active reminders."

    lines = [f"Active reminders ({len(active)}):\n"]
    for r in active:
        try:
            due = datetime.fromisoformat(r["due_time"])
            time_str = due.strftime("%A, %B %d at %I:%M %p")
        except (KeyError, ValueError):
            time_str = "unknown time"

        recurring_tag = " 🔁 daily" if r.get("recurring") == "daily" else ""
        lines.append(f"  • {r.get('message', '?')} — {time_str}{recurring_tag}")
        lines.append(f"    ID: {r.get('id', '?')}")

    return "\n".join(lines)


def delete_reminder(reminder_id: str) -> str:
    """Delete (complete) a reminder by its ID.

    Marks the reminder as completed so it will no longer appear in the
    active reminders list or trigger notifications.

    Args:
        reminder_id: The unique ID of the reminder to delete
                     (shown when the reminder was created or listed).

    Returns:
        A confirmation message, or an error if the reminder was not found.
    """
    logger.info("Deleting reminder: %s", reminder_id)
    reminders = load_reminders()
    target_id = reminder_id.strip().lower()

    for reminder in reminders:
        if reminder.get("id", "").lower() == target_id:
            if reminder.get("completed", False):
                return f"Reminder '{reminder.get('message', '')}' is already completed."
            reminder["completed"] = True
            save_reminders(reminders)
            logger.info("Reminder '%s' deleted", reminder.get("message", ""))
            return f"Done — reminder '{reminder.get('message', '')}' has been deleted."

    logger.warning("Reminder with ID '%s' not found", reminder_id)
    return f"No reminder found with ID '{reminder_id}'. Use the list reminders function to see active reminders."


if __name__ == "__main__":
    # Quick standalone test
    print(set_reminder("Test reminder", "in 5 minutes"))
    print()
    print(list_reminders())
    print()
    due = check_due_reminders()
    print(f"Due now: {due}")
