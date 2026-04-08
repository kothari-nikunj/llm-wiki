#!/usr/bin/env python3
"""
Ingest script for the personal knowledge wiki.
Converts raw data sources into individual markdown entries in raw/entries/.
Idempotent: running twice produces the same output.
"""

import json
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
RAW_ENTRIES = ROOT / "raw" / "entries"
RAW_ENTRIES.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].strip('-')


def write_entry(entry_id: str, date: str, time: str, source_type: str,
                title: str, content: str, extra_frontmatter: dict = None):
    """Write a single entry to raw/entries/."""
    filename = f"{date}_{slugify(entry_id)}.md"
    filepath = RAW_ENTRIES / filename

    lines = ["---"]
    lines.append(f"id: {entry_id}")
    lines.append(f"date: {date}")
    lines.append(f'time: "{time}"')
    lines.append(f"source_type: {source_type}")
    lines.append(f"title: \"{title.replace(chr(34), chr(39))}\"")
    if extra_frontmatter:
        for k, v in extra_frontmatter.items():
            if isinstance(v, list):
                lines.append(f"{k}: {json.dumps(v)}")
            elif isinstance(v, (int, float)):
                lines.append(f"{k}: {v}")
            else:
                lines.append(f"{k}: \"{str(v).replace(chr(34), chr(39))}\"")
    lines.append("tags: []")
    lines.append("---")
    lines.append("")
    lines.append(content)

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def ingest_writing():
    """Ingest writing .md files from data/writing/ (recursive)."""
    writing_dir = ROOT / "data" / "writing"
    if not writing_dir.exists():
        print("  Writing: skipped (no data/writing/ found)")
        return 0

    count = 0
    for md_file in sorted(writing_dir.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")

        # Extract title from first H1
        title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else md_file.stem.replace('-', ' ').title()

        # Use file modification time as date
        mtime = os.path.getmtime(md_file)
        dt = datetime.fromtimestamp(mtime)
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M:%S")

        entry_id = f"writing-{md_file.stem}"
        write_entry(entry_id, date_str, time_str, "writing", title, text)
        count += 1

    print(f"  Writing: {count} entries")
    return count


def ingest_tweets():
    """Ingest tweets from data/tweets/tweets.js (X archive format)."""
    tweets_file = ROOT / "data" / "tweets" / "tweets.js"
    if not tweets_file.exists():
        print("  Tweets: skipped (no tweets.js found)")
        return 0

    raw = tweets_file.read_text(encoding="utf-8")
    # Strip the JS variable assignment prefix
    json_start = raw.index('[')
    tweets = json.loads(raw[json_start:])

    count = 0
    for item in tweets:
        tweet = item.get("tweet", item)
        tweet_id = tweet.get("id_str", tweet.get("id", ""))
        full_text = tweet.get("full_text", tweet.get("text", ""))
        created_at = tweet.get("created_at", "")

        if not full_text or not created_at:
            continue

        # Skip replies and retweets
        if tweet.get("in_reply_to_screen_name"):
            continue
        if full_text.startswith("RT @"):
            continue

        # Parse Twitter date format: "Mon Apr 06 20:47:07 +0000 2026"
        try:
            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            continue

        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M:%S")

        # Check if reply
        reply_to = tweet.get("in_reply_to_screen_name", "")
        is_retweet = full_text.startswith("RT @")

        # Extract media URLs
        media_urls = []
        extended = tweet.get("extended_entities", tweet.get("entities", {}))
        for m in extended.get("media", []):
            media_urls.append(m.get("media_url_https", m.get("media_url", "")))

        # Extract mentioned users
        mentions = []
        entities = tweet.get("entities", {})
        for um in entities.get("user_mentions", []):
            mentions.append(um.get("screen_name", ""))

        extra = {}
        if reply_to:
            extra["reply_to"] = reply_to
        if is_retweet:
            extra["is_retweet"] = True
        if media_urls:
            extra["media"] = media_urls
        if mentions:
            extra["mentions"] = mentions

        # Title: first 80 chars of text
        title = re.sub(r'\s+', ' ', full_text)[:80]

        entry_id = f"tweet-{tweet_id}"
        write_entry(entry_id, date_str, time_str, "twitter", title, full_text, extra)
        count += 1

    print(f"  Tweets: {count} entries")
    return count


def ingest_bookmarks():
    """Ingest X bookmarks from ~/.ft-bookmarks/bookmarks.jsonl."""
    bookmarks_file = Path.home() / ".ft-bookmarks" / "bookmarks.jsonl"
    if not bookmarks_file.exists():
        print("  Bookmarks: skipped (no bookmarks.jsonl found)")
        return 0

    count = 0
    for line in bookmarks_file.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue

        try:
            bm = json.loads(line)
        except json.JSONDecodeError:
            continue

        text = bm.get("text", "")
        if not text:
            continue

        tweet_id = bm.get("tweetId", bm.get("id", ""))
        author = bm.get("authorHandle", "unknown")
        author_name = bm.get("authorName", "")
        url = bm.get("url", "")
        posted_at = bm.get("postedAt", "")

        # Parse date: "Sun Apr 05 06:06:36 +0000 2026"
        try:
            dt = datetime.strptime(posted_at, "%a %b %d %H:%M:%S %z %Y")
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            date_str = "2025-01-01"
            time_str = "00:00:00"

        # Engagement stats
        engagement = bm.get("engagement", {})
        extra = {
            "author": author,
            "author_name": author_name,
            "url": url,
            "likes": engagement.get("likeCount", 0),
            "reposts": engagement.get("repostCount", 0),
            "bookmarks": engagement.get("bookmarkCount", 0),
        }

        # Media
        media = bm.get("media", [])
        if media:
            extra["media"] = media

        title = f"@{author}: {re.sub(r's+', ' ', text)[:70]}"
        content = f"**@{author}** ({author_name}):\n\n{text}"
        if url:
            content += f"\n\nSource: {url}"

        entry_id = f"bookmark-{tweet_id}"
        write_entry(entry_id, date_str, time_str, "x-bookmark", title, content, extra)
        count += 1

    print(f"  Bookmarks: {count} entries")
    return count


def main():
    print("Wiki Ingest")
    print("=" * 40)
    print(f"Output: {RAW_ENTRIES}")
    print()

    total = 0
    total += ingest_writing()
    total += ingest_tweets()
    total += ingest_bookmarks()

    print()
    print(f"Total: {total} entries written to raw/entries/")


if __name__ == "__main__":
    main()
