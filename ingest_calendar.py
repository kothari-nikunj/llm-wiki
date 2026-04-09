#!/usr/bin/env python3
"""
Ingest Google Calendar events into wiki entries.

Requires a Google OAuth token with Calendar read scope. Setup is the same
as ingest_gmail.py — if you already authorized Gmail, add the Calendar scope.

Usage:
    python3 ingest_calendar.py                 # Ingest last 30 days
    python3 ingest_calendar.py --days 90       # Ingest last 90 days
    python3 ingest_calendar.py --auth          # Set up OAuth credentials
"""

import os
import re
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
RAW_ENTRIES = ROOT / "raw" / "entries"
RAW_ENTRIES.mkdir(parents=True, exist_ok=True)

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]
TOKEN_PATH = os.environ.get("GMAIL_TOKEN_PATH", str(ROOT / "gmail_token.json"))
CREDS_PATH = str(ROOT / "credentials.json")


def get_calendar_service():
    """Authenticate and return Calendar API service."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                print(f"No credentials found at {CREDS_PATH}")
                print("See ingest_gmail.py docstring for setup instructions.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        Path(TOKEN_PATH).write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text[:60].strip('-')


def parse_datetime(dt_obj):
    """Parse Google Calendar dateTime or date field."""
    dt_str = dt_obj.get("dateTime") or dt_obj.get("date")
    if not dt_str:
        return None, None, None

    # Full datetime: 2026-04-09T10:00:00+08:00
    if "T" in dt_str:
        # Strip timezone offset for simple parsing
        clean = re.sub(r'[+-]\d{2}:\d{2}$', '', dt_str).replace('Z', '')
        try:
            dt = datetime.fromisoformat(clean)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"), dt
        except ValueError:
            pass

    # Date only: 2026-04-09 (all-day event)
    return dt_str[:10], "all-day", None


def ingest_events(service, days_back, max_results=500):
    """Fetch and ingest calendar events."""
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days_back)).isoformat()
    time_max = now.isoformat()

    count = 0
    page_token = None

    while True:
        kwargs = {
            "calendarId": "primary",
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": min(250, max_results - count),
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if page_token:
            kwargs["pageToken"] = page_token

        results = service.events().list(**kwargs).execute()
        events = results.get("items", [])

        for event in events:
            if count >= max_results:
                break

            summary = event.get("summary", "(no title)")
            description = event.get("description", "")
            location = event.get("location", "")
            start = event.get("start", {})
            end = event.get("end", {})
            attendees = event.get("attendees", [])
            creator = event.get("creator", {})

            date, start_time, _ = parse_datetime(start)
            _, end_time, _ = parse_datetime(end)

            if not date:
                continue

            # Build attendee list
            attendee_names = []
            for a in attendees:
                name = a.get("displayName") or a.get("email", "")
                status = a.get("responseStatus", "")
                attendee_names.append(f"{name} ({status})")

            entry_id = f"cal-{event.get('id', '')[:12]}"
            filename = f"{date}_{slugify(entry_id)}.md"
            filepath = RAW_ENTRIES / filename

            lines = [
                "---",
                f"id: {entry_id}",
                f"date: {date}",
                f'time: "{start_time}"',
                f"source_type: calendar",
                f'title: "{summary.replace(chr(34), chr(39))}"',
                "tags: []",
                "---",
                "",
                f"**Event**: {summary}",
                f"**Date**: {date} {start_time}" + (f" - {end_time}" if end_time else ""),
            ]

            if location:
                lines.append(f"**Location**: {location}")
            if attendee_names:
                lines.append(f"**Attendees**: {', '.join(attendee_names[:10])}")
            if creator.get("email"):
                lines.append(f"**Organizer**: {creator.get('displayName', creator['email'])}")

            if description:
                lines.append("")
                lines.append(description[:2000])

            filepath.write_text("\n".join(lines), encoding="utf-8")
            count += 1

        page_token = results.get("nextPageToken")
        if not page_token or count >= max_results:
            break

    return count


def main():
    parser = argparse.ArgumentParser(description="Ingest Google Calendar into wiki entries")
    parser.add_argument("--days", type=int, default=30, help="How many days back to fetch (default: 30)")
    parser.add_argument("--max", type=int, default=500, help="Maximum events to fetch (default: 500)")
    parser.add_argument("--auth", action="store_true", help="Run OAuth setup flow")
    args = parser.parse_args()

    if not HAS_GOOGLE:
        print("Google API client not installed. Run:")
        print("  pip install google-auth-oauthlib google-api-python-client")
        return

    if args.auth:
        service = get_calendar_service()
        if service:
            print("Authentication successful. Token saved.")
        return

    service = get_calendar_service()
    if not service:
        return

    print(f"Calendar Ingest: last {args.days} days, max={args.max}")
    count = ingest_events(service, args.days, args.max)
    print(f"Done: {count} calendar entries written to raw/entries/")


if __name__ == "__main__":
    main()
