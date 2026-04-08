#!/usr/bin/env python3
"""
iMessage ingest for the personal knowledge wiki.
Extracts top N DM contacts, messages >15 chars.
Groups by conversation + day into raw/entries/.

macOS only. Requires Full Disk Access for your terminal app.
"""

import sqlite3
import os
import re
import glob
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

IMESSAGE_DB = os.path.expanduser("~/Library/Messages/chat.db")
ADDRESSBOOK_DIR = os.path.expanduser("~/Library/Application Support/AddressBook")
ROOT = Path(__file__).parent
RAW_ENTRIES = ROOT / "raw" / "entries"
RAW_ENTRIES.mkdir(parents=True, exist_ok=True)

# Configure these for your needs
TS_START = int(datetime(2016, 1, 1, tzinfo=timezone.utc).timestamp())  # How far back to go
TOP_N = 100  # Number of top contacts to process
MIN_MSG_LEN = 15  # Minimum message length to include
YOUR_NAME = "Me"  # Change this to your name


def extract_text_from_blob(ab):
    """Extract text from NSAttributedString blob (attributedBody column)."""
    if not ab:
        return None
    blob = ab if isinstance(ab, bytes) else bytes(ab)
    decoded = blob.decode('utf-8', errors='replace')
    match = re.search(r'\+(.{2,2000}?)(?:iI|(?:\x00){2})', decoded)
    if match:
        text = match.group(1).strip()
        text = re.sub(r'^[^\x20-\x7e]*', '', text)
        text = text.rstrip('\ufffd').strip()
        if len(text) > 3:
            return text
    return None


def normalize_phone(phone):
    if not phone:
        return None
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else (digits if len(digits) >= 7 else None)


def extract_contacts():
    contacts = {}
    db_paths = glob.glob(os.path.join(ADDRESSBOOK_DIR, "Sources", "*", "AddressBook-v22.abcddb"))
    main_db = os.path.join(ADDRESSBOOK_DIR, "AddressBook-v22.abcddb")
    if os.path.exists(main_db):
        db_paths.append(main_db)

    for db_path in db_paths:
        try:
            conn = sqlite3.connect(db_path)
            people = {}
            for row in conn.execute("SELECT ROWID, ZFIRSTNAME, ZLASTNAME FROM ZABCDRECORD WHERE ZFIRSTNAME IS NOT NULL OR ZLASTNAME IS NOT NULL"):
                name = f"{row[1] or ''} {row[2] or ''}".strip()
                if name:
                    people[row[0]] = name
            for owner, phone in conn.execute("SELECT ZOWNER, ZFULLNUMBER FROM ZABCDPHONENUMBER WHERE ZFULLNUMBER IS NOT NULL"):
                if owner in people:
                    norm = normalize_phone(phone)
                    if norm:
                        contacts[norm] = people[owner]
            for owner, email in conn.execute("SELECT ZOWNER, ZADDRESS FROM ZABCDEMAILADDRESS WHERE ZADDRESS IS NOT NULL"):
                if owner in people:
                    contacts[email.lower().strip()] = people[owner]
            conn.close()
        except Exception:
            pass
    return contacts


def get_name(handle, contacts):
    lookup = handle.lower().strip() if '@' in handle else normalize_phone(handle)
    if lookup and lookup in contacts:
        return contacts[lookup]
    return handle.split('@')[0] if '@' in handle else handle


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:60].strip('-')


def main():
    print("iMessage Ingest")
    print("=" * 40)

    contacts = extract_contacts()
    print(f"Loaded {len(contacts)} contacts from AddressBook")

    conn = sqlite3.connect(IMESSAGE_DB)

    # Find top N contacts by message volume (DMs only, since TS_START)
    top_contacts = conn.execute(f"""
        SELECT c.chat_identifier, COUNT(*) as cnt
        FROM message m, chat_message_join cmj, chat c
        WHERE cmj.message_id = m.ROWID
          AND c.ROWID = cmj.chat_id
          AND c.chat_identifier NOT LIKE 'chat%'
          AND (m.date/1000000000 + 978307200) > {TS_START}
        GROUP BY c.chat_identifier
        ORDER BY cnt DESC
        LIMIT {TOP_N}
    """).fetchall()

    print(f"Top {len(top_contacts)} contacts since {datetime.fromtimestamp(TS_START).year}:")
    for handle, cnt in top_contacts[:10]:
        name = get_name(handle, contacts)
        print(f"  {name:<25} {cnt:>6} msgs")
    if len(top_contacts) > 10:
        print(f"  ... and {len(top_contacts) - 10} more")

    # For each top contact, pull messages and group by day
    total_entries = 0
    total_messages = 0

    for handle_id, _ in top_contacts:
        name = get_name(handle_id, contacts)
        name_slug = slugify(name)

        messages = conn.execute(f"""
            SELECT
                datetime(m.date/1000000000 + 978307200, 'unixepoch', 'localtime') as msg_date,
                m.text,
                m.attributedBody,
                m.is_from_me
            FROM message m
            JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
            JOIN chat c ON c.ROWID = cmj.chat_id
            WHERE c.chat_identifier = ?
              AND (m.date/1000000000 + 978307200) > {TS_START}
              AND (m.text IS NOT NULL OR m.attributedBody IS NOT NULL)
            ORDER BY m.date
        """, (handle_id,)).fetchall()

        if not messages:
            continue

        # Group by date
        by_day = defaultdict(list)
        for msg_date, text, attributed_body, is_from_me in messages:
            msg_text = text or extract_text_from_blob(attributed_body)
            if not msg_text or len(msg_text) < MIN_MSG_LEN:
                continue
            # Skip tapback reactions
            if msg_text.startswith(('Liked "', 'Loved "', 'Laughed at "', 'Emphasized "', 'Disliked "', 'Questioned "')):
                continue
            day = msg_date[:10]
            sender = YOUR_NAME if is_from_me else name
            by_day[day].append((msg_date[11:19], sender, msg_text))

        # Write one entry per day
        for day, day_msgs in sorted(by_day.items()):
            if len(day_msgs) < 2:
                continue

            entry_id = f"imessage-{name_slug}-{day}"
            filename = f"{day}_{slugify(entry_id)}.md"
            filepath = RAW_ENTRIES / filename

            lines = ["---"]
            lines.append(f"id: {entry_id}")
            lines.append(f"date: {day}")
            lines.append(f'time: "{day_msgs[0][0]}"')
            lines.append("source_type: imessage")
            lines.append(f'title: "Conversation with {name}"')
            lines.append(f'participant: "{name}"')
            lines.append(f"message_count: {len(day_msgs)}")
            lines.append("tags: []")
            lines.append("---")
            lines.append("")
            lines.append(f"# Conversation with {name} ({day})")
            lines.append("")

            for time_str, sender, text in day_msgs:
                lines.append(f"**{sender}** ({time_str}): {text}")
                lines.append("")

            filepath.write_text("\n".join(lines), encoding="utf-8")
            total_entries += 1
            total_messages += len(day_msgs)

    conn.close()

    print(f"\nTotal: {total_entries} conversation-day entries")
    print(f"Total: {total_messages} messages across entries")
    print(f"Output: {RAW_ENTRIES}")


if __name__ == "__main__":
    main()
