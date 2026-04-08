#!/usr/bin/env python3
"""
WhatsApp ingest for the personal knowledge wiki.
Extracts top N DM contacts, messages >15 chars.
Groups by conversation + day into raw/entries/.

macOS only. Requires WhatsApp desktop app with synced messages.
"""

import sqlite3
import os
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

WA_DB = os.path.expanduser("~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite")
ROOT = Path(__file__).parent
RAW_ENTRIES = ROOT / "raw" / "entries"
RAW_ENTRIES.mkdir(parents=True, exist_ok=True)

# Configure these for your needs
TOP_N = 30  # Number of top contacts to process
MIN_MSG_LEN = 15  # Minimum message length to include
YOUR_NAME = "Me"  # Change this to your name


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:60].strip('-')


def main():
    print("WhatsApp Ingest")
    print("=" * 40)

    if not os.path.exists(WA_DB):
        print("WhatsApp database not found")
        return

    conn = sqlite3.connect(WA_DB)

    # Top N DM contacts by message volume
    top_contacts = conn.execute(f"""
        SELECT cs.Z_PK, cs.ZPARTNERNAME, cs.ZCONTACTJID, COUNT(*) as cnt
        FROM ZWAMESSAGE m
        JOIN ZWACHATSESSION cs ON m.ZCHATSESSION = cs.Z_PK
        WHERE cs.ZPARTNERNAME IS NOT NULL
          AND cs.ZCONTACTJID NOT LIKE '%@g.us'
        GROUP BY cs.Z_PK
        ORDER BY cnt DESC
        LIMIT {TOP_N}
    """).fetchall()

    print(f"Top {len(top_contacts)} WhatsApp contacts:")
    for _, name, jid, cnt in top_contacts[:10]:
        print(f"  {name:<25} {cnt:>5} msgs")
    if len(top_contacts) > 10:
        print(f"  ... and {len(top_contacts) - 10} more")

    total_entries = 0
    total_messages = 0

    for chat_pk, name, jid, _ in top_contacts:
        name_slug = slugify(name)

        messages = conn.execute("""
            SELECT
                datetime(m.ZMESSAGEDATE + 978307200, 'unixepoch', 'localtime') as msg_date,
                m.ZTEXT,
                m.ZISFROMME
            FROM ZWAMESSAGE m
            WHERE m.ZCHATSESSION = ?
              AND m.ZTEXT IS NOT NULL
              AND LENGTH(m.ZTEXT) > ?
            ORDER BY m.ZMESSAGEDATE
        """, (chat_pk, MIN_MSG_LEN)).fetchall()

        if not messages:
            continue

        by_day = defaultdict(list)
        for msg_date, text, is_from_me in messages:
            if not msg_date:
                continue
            day = msg_date[:10]
            sender = YOUR_NAME if is_from_me else name
            by_day[day].append((msg_date[11:19], sender, text))

        for day, day_msgs in sorted(by_day.items()):
            if len(day_msgs) < 2:
                continue

            entry_id = f"whatsapp-{name_slug}-{day}"
            filename = f"{day}_{slugify(entry_id)}.md"
            filepath = RAW_ENTRIES / filename

            lines = ["---"]
            lines.append(f"id: {entry_id}")
            lines.append(f"date: {day}")
            lines.append(f'time: "{day_msgs[0][0]}"')
            lines.append("source_type: whatsapp")
            lines.append(f'title: "WhatsApp with {name}"')
            lines.append(f'participant: "{name}"')
            lines.append(f"message_count: {len(day_msgs)}")
            lines.append("tags: []")
            lines.append("---")
            lines.append("")
            lines.append(f"# WhatsApp with {name} ({day})")
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


if __name__ == "__main__":
    main()
