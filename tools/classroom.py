"""
Adri — Google Classroom tool.
Fetches course updates (assignments, announcements) from Google Classroom
using the Classroom API with OAuth2 authentication.
"""

import os
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import (
    CLASSROOM_CREDENTIALS_FILE,
    CLASSROOM_TOKEN_FILE,
    CLASSROOM_SCOPES,
    logger,
)


def _get_classroom_service():
    """Authenticate and return a Google Classroom API service object.

    Loads cached credentials from token.json. If they are expired, refreshes
    them. If no valid credentials exist, starts the OAuth2 browser flow
    to obtain new ones and caches them for future use.

    Returns:
        A googleapiclient Resource object for the Classroom API (v1).

    Raises:
        FileNotFoundError: If credentials.json is not found.
        Exception: If authentication or service creation fails.
    """
    creds = None

    # Load cached token
    if CLASSROOM_TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(CLASSROOM_TOKEN_FILE), CLASSROOM_SCOPES,
            )
            logger.info("Loaded cached Classroom credentials")
        except Exception as e:
            logger.warning("Failed to load cached token: %s", e)
            creds = None

    # Refresh or re-authenticate
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            logger.info("Refreshed expired Classroom credentials")
        except Exception as e:
            logger.warning("Token refresh failed — re-authenticating: %s", e)
            creds = None

    if not creds or not creds.valid:
        if not CLASSROOM_CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"OAuth credentials file not found at {CLASSROOM_CREDENTIALS_FILE}. "
                "Please download credentials.json from the Google Cloud Console "
                "and place it in the credentials/ directory."
            )
        logger.info("Starting OAuth2 browser flow for Classroom")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLASSROOM_CREDENTIALS_FILE), CLASSROOM_SCOPES,
        )
        creds = flow.run_local_server(port=0)
        logger.info("OAuth2 authentication successful")

    # Cache the credentials
    try:
        with open(CLASSROOM_TOKEN_FILE, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())
        logger.info("Saved Classroom credentials to %s", CLASSROOM_TOKEN_FILE)
    except OSError as e:
        logger.warning("Could not cache token: %s", e)

    service = build("classroom", "v1", credentials=creds)
    logger.info("Classroom API service created")
    return service


def _format_date(date_dict: dict) -> str:
    """Convert a Classroom API date object {year, month, day} to a readable string."""
    if not date_dict:
        return "no due date"
    try:
        year = date_dict.get("year", 0)
        month = date_dict.get("month", 1)
        day = date_dict.get("day", 1)
        return datetime(year, month, day).strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return "unknown date"


def get_classroom_updates(course_name: str = "") -> str:
    """Get recent updates from Google Classroom courses.

    Fetches the latest coursework (assignments) and announcements from
    your Google Classroom courses. Optionally filter by course name.

    Args:
        course_name: Filter results to a specific course by name
                     (case-insensitive partial match). Leave empty to
                     get updates from all courses.

    Returns:
        A natural-language summary of recent assignments and announcements,
        or an error message if something goes wrong.
    """
    logger.info("Fetching Classroom updates (filter: '%s')", course_name or "all courses")

    try:
        service = _get_classroom_service()
    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        logger.error("Classroom authentication failed: %s", e)
        return f"Error: Could not authenticate with Google Classroom — {e}"

    # ── Fetch courses ───────────────────────────────────────────────────────
    try:
        logger.info("Listing Classroom courses")
        courses_response = service.courses().list(
            courseStates=["ACTIVE"],
            pageSize=20,
        ).execute()
    except HttpError as e:
        logger.error("Classroom API error (courses): %s", e)
        return f"Error: Google Classroom API error — {e}"
    except Exception as e:
        logger.error("Network error fetching courses: %s", e)
        return f"Error: Could not reach Google Classroom — {e}"

    courses = courses_response.get("courses", [])
    if not courses:
        return "No active courses found in your Google Classroom."

    # Optionally filter by name
    if course_name:
        filter_lower = course_name.strip().lower()
        courses = [
            c for c in courses
            if filter_lower in c.get("name", "").lower()
        ]
        if not courses:
            return f"No course matching '{course_name}' found in your Google Classroom."

    # ── Fetch updates per course ────────────────────────────────────────────
    output_sections: list[str] = []

    for course in courses:
        course_id = course["id"]
        name = course.get("name", "Unknown Course")
        section_lines: list[str] = [f"📚 {name}:"]
        has_updates = False

        # Coursework (assignments)
        try:
            logger.info("Fetching coursework for '%s'", name)
            cw_response = service.courses().courseWork().list(
                courseId=course_id,
                orderBy="updateTime desc",
                pageSize=5,
            ).execute()
            coursework = cw_response.get("courseWork", [])
        except HttpError as e:
            logger.warning("Could not fetch coursework for '%s': %s", name, e)
            coursework = []
        except Exception as e:
            logger.warning("Network error for coursework '%s': %s", name, e)
            coursework = []

        if coursework:
            has_updates = True
            section_lines.append("  Assignments:")
            for cw in coursework:
                title = cw.get("title", "Untitled")
                due_date = _format_date(cw.get("dueDate", {}))
                state = cw.get("state", "")
                section_lines.append(f"    • \"{title}\" — due {due_date}")

        # Announcements
        try:
            logger.info("Fetching announcements for '%s'", name)
            ann_response = service.courses().announcements().list(
                courseId=course_id,
                orderBy="updateTime desc",
                pageSize=5,
            ).execute()
            announcements = ann_response.get("announcements", [])
        except HttpError as e:
            logger.warning("Could not fetch announcements for '%s': %s", name, e)
            announcements = []
        except Exception as e:
            logger.warning("Network error for announcements '%s': %s", name, e)
            announcements = []

        if announcements:
            has_updates = True
            section_lines.append("  Announcements:")
            for ann in announcements:
                text = ann.get("text", "")
                # Truncate long announcements
                preview = text[:150].replace("\n", " ")
                if len(text) > 150:
                    preview += "…"
                section_lines.append(f"    • \"{preview}\"")

        if not has_updates:
            section_lines.append("  No recent updates.")

        output_sections.append("\n".join(section_lines))

    result = "\n\n".join(output_sections)
    logger.info("Classroom updates fetched for %d course(s)", len(courses))
    return result


if __name__ == "__main__":
    print(get_classroom_updates())
