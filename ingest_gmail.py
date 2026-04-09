#!/usr/bin/env python3
"""
Ingest Gmail messages into wiki entries.

Requires a Google OAuth token with Gmail read scope. Two ways to set up:

Option A: Use an existing OAuth token (if you have one from another app)
    export GMAIL_TOKEN_PATH=~/.config/gmail/token.json

Option B: Create credentials via Google Cloud Console
    1. Create a project at console.cloud.google.com
    2. Enable the Gmail API
    3. Create OAuth 2.0 credentials (Desktop app)
    4. Download as credentials.json to this directory
    5. Run: python3 ingest_gmail.py --auth
    6. Follow the browser flow to authorize

Usage:
    python3 ingest_gmail.py                    # Ingest last 30 days
    python3 ingest_gmail.py --days 90          # Ingest last 90 days
    python3 ingest_gmail.py --query "from:boss" # Custom Gmail search query
    python3 ingest_gmail.py --auth             # Set up OAuth credentials
"""

import os
import re
import json
import base64
import argparse
import email.utils
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
RAW_ENTRIES = ROOT / "raw" / "entries"
RAW_ENTRIES.mkdir(parents=True, exist_ok=True)

# Try to import Google API client
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = os.environ.get("GMAIL_TOKEN_PATH", str(ROOT / "gmail_token.json"))
CREDS_PATH = str(ROOT / "credentials.json")


def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                print(f"No credentials found at {CREDS_PATH}")
                print("See the docstring at the top of this file for setup instructions.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        Path(TOKEN_PATH).write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text[:60].strip('-')


def extract_body(payload):
    """Extract plain text body from Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        # Recurse into multipart
        if part.get("parts"):
            result = extract_body(part)
            if result:
                return result

    return ""


def get_header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def ingest_messages(service, query, max_results=200):
    """Fetch and ingest Gmail messages matching query."""
    count = 0
    page_token = None

    while True:
        kwargs = {"userId": "me", "q": query, "maxResults": min(50, max_results - count)}
        if page_token:
            kwargs["pageToken"] = page_token

        results = service.users().messages().list(**kwargs).execute()
        messages = results.get("messages", [])

        if not messages:
            break

        for msg_meta in messages:
            if count >= max_results:
                break

            msg = service.users().messages().get(
                userId="me", id=msg_meta["id"], format="full"
            ).execute()

            headers = msg.get("payload", {}).get("headers", [])
            subject = get_header(headers, "Subject") or "(no subject)"
            from_addr = get_header(headers, "From")
            to_addr = get_header(headers, "To")
            date_str = get_header(headers, "Date")

            # Parse date
            try:
                parsed = email.utils.parsedate_to_datetime(date_str)
                date = parsed.strftime("%Y-%m-%d")
                time = parsed.strftime("%H:%M:%S")
            except Exception:
                date = datetime.now().strftime("%Y-%m-%d")
                time = "00:00:00"

            body = extract_body(msg.get("payload", {}))
            if not body or len(body) < 20:
                continue

            # Truncate very long emails
            body = body[:5000]

            # Extract sender name
            sender_match = re.match(r'"?([^"<]+)"?\s*<?', from_addr)
            sender = sender_match.group(1).strip() if sender_match else from_addr

            entry_id = f"gmail-{msg_meta['id'][:12]}"
            filename = f"{date}_{slugify(entry_id)}.md"
            filepath = RAW_ENTRIES / filename

            content = [
                "---",
                f"id: {entry_id}",
                f"date: {date}",
                f'time: "{time}"',
                f"source_type: gmail",
                f'title: "{subject.replace(chr(34), chr(39))}"',
                f'from: "{sender.replace(chr(34), chr(39))}"',
                f'to: "{to_addr[:80].replace(chr(34), chr(39))}"',
                "tags: []",
                "---",
                "",
                f"**From**: {sender}",
                f"**Subject**: {subject}",
                f"**Date**: {date}",
                "",
                body,
            ]

            filepath.write_text("\n".join(content), encoding="utf-8")
            count += 1

        page_token = results.get("nextPageToken")
        if not page_token or count >= max_results:
            break

    return count


def main():
    parser = argparse.ArgumentParser(description="Ingest Gmail into wiki entries")
    parser.add_argument("--days", type=int, default=30, help="How many days back to fetch (default: 30)")
    parser.add_argument("--query", default=None, help="Custom Gmail search query (overrides --days)")
    parser.add_argument("--max", type=int, default=200, help="Maximum messages to fetch (default: 200)")
    parser.add_argument("--auth", action="store_true", help="Run OAuth setup flow")
    args = parser.parse_args()

    if not HAS_GOOGLE:
        print("Google API client not installed. Run:")
        print("  pip install google-auth-oauthlib google-api-python-client")
        return

    if args.auth:
        service = get_gmail_service()
        if service:
            print("Authentication successful. Token saved.")
        return

    service = get_gmail_service()
    if not service:
        return

    if args.query:
        query = args.query
    else:
        cutoff = (datetime.now() - timedelta(days=args.days)).strftime("%Y/%m/%d")
        query = f"after:{cutoff}"

    print(f"Gmail Ingest: query='{query}', max={args.max}")
    count = ingest_messages(service, query, args.max)
    print(f"Done: {count} email entries written to raw/entries/")


if __name__ == "__main__":
    main()
