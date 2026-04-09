#!/usr/bin/env python3
"""
Compile wiki articles using a local LLM via Ollama instead of Claude Code.

Zero-cost alternative to the Claude Code skill. Runs entirely on your machine.
Requires Ollama (https://ollama.com) with a capable model installed.

Usage:
    # Install a model first
    ollama pull qwen3:8b

    # Run the local compiler
    python3 ingest_ollama.py [--model qwen3:8b] [--date-range "last 30 days"]

Supported models (tested):
    - qwen3:8b          — Good balance of speed and quality
    - qwen3:32b         — Better quality, slower
    - llama3.3:70b      — Best quality, requires 48GB+ RAM
    - gemma3:27b        — Good alternative

The script reads entries from raw/entries/, understands them, and writes
wiki articles to wiki/. It maintains _index.md and _backlinks.json.
"""

import re
import json
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
RAW_ENTRIES = ROOT / "raw" / "entries"
WIKI_DIR = ROOT / "wiki"
INDEX_FILE = WIKI_DIR / "_index.md"
BACKLINKS_FILE = WIKI_DIR / "_backlinks.json"
ABSORB_LOG = WIKI_DIR / "_absorb_log.json"

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:8b"
CHECKPOINT_INTERVAL = 15

SKIP_FILES = {"_index.md", "_backlinks.json", "_absorb_log.json"}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{ts} {msg}")


def ask_ollama(prompt, model, temperature=0.3, max_tokens=1500):
    """Send a prompt to Ollama and return the response text."""
    resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens}
    }, timeout=180)
    resp.raise_for_status()
    text = resp.json().get("response", "")
    # Strip thinking tags if model uses them (e.g. qwen3)
    if "</think>" in text:
        text = text.split("</think>", 1)[-1].strip()
    return text


def load_absorb_log():
    """Track which entries have been absorbed."""
    if ABSORB_LOG.exists():
        return json.loads(ABSORB_LOG.read_text())
    return {"absorbed": []}


def save_absorb_log(data):
    ABSORB_LOG.write_text(json.dumps(data, indent=2))


def get_entries(date_range=None):
    """Get entries from raw/entries/, filtered by date range."""
    if not RAW_ENTRIES.exists():
        log("No raw/entries/ directory found. Run ingest.py first.")
        return []

    entries = []
    for md_file in sorted(RAW_ENTRIES.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        # Extract date from filename (YYYY-MM-DD_slug.md)
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", md_file.name)
        date_str = date_match.group(1) if date_match else "2025-01-01"
        entries.append({
            "file": md_file,
            "date": date_str,
            "content": text,
            "id": md_file.stem,
        })

    if date_range:
        entries = filter_by_date(entries, date_range)

    # Sort chronologically
    entries.sort(key=lambda e: e["date"])
    return entries


def filter_by_date(entries, date_range):
    """Filter entries by date range string."""
    now = datetime.now()

    if date_range == "all":
        return entries

    if date_range.startswith("last "):
        parts = date_range.replace("last ", "").split()
        n = int(parts[0])
        unit = parts[1] if len(parts) > 1 else "days"
        cutoff = now - timedelta(days=n if "day" in unit else n * 30)
        return [e for e in entries if e["date"] >= cutoff.strftime("%Y-%m-%d")]

    if re.match(r"^\d{4}$", date_range):
        return [e for e in entries if e["date"].startswith(date_range)]

    if re.match(r"^\d{4}-\d{2}$", date_range):
        return [e for e in entries if e["date"].startswith(date_range)]

    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_range):
        return [e for e in entries if e["date"] == date_range]

    return entries


def load_wiki_index():
    """Read current wiki article titles for context."""
    if not INDEX_FILE.exists():
        return "No articles yet."
    return INDEX_FILE.read_text()[:2000]


def absorb_entry(entry, model, wiki_index):
    """Ask the LLM to absorb one entry into a wiki article."""
    prompt = f"""You are compiling a personal knowledge wiki. Read this entry and write a wiki article.

Current wiki index (for context on existing articles):
{wiki_index}

Entry (id: {entry['id']}, date: {entry['date']}):
---
{entry['content'][:3000]}
---

Output format (strictly follow this):
Line 1: DIRECTORY: <directory name, e.g. people, concepts, projects, eras, patterns>
Line 2: FILENAME: <kebab-case filename without .md, e.g. john-doe>
Line 3: CONTENT:
Then the article content in markdown with YAML frontmatter:

---
title: Article Title
type: person | concept | project | era | pattern | place | event
created: {entry['date']}
last_updated: {entry['date']}
related: ["[[other-article]]"]
sources: ["{entry['id']}"]
---

# Article Title

Content organized by theme. Use [[wikilinks]] to reference other articles.
Write like Wikipedia: flat, factual, no AI editorial voice.
Lead with what matters. Connect to patterns."""

    return ask_ollama(prompt, model, max_tokens=2000)


def parse_article(response, entry_id):
    """Parse LLM response into directory, filename, and content."""
    lines = response.strip().split("\n")
    directory = ""
    filename = ""
    content_lines = []
    in_content = False

    for line in lines:
        if line.startswith("DIRECTORY:"):
            directory = line.replace("DIRECTORY:", "").strip().lower()
            directory = re.sub(r'[^a-z0-9_-]', '', directory)
        elif line.startswith("FILENAME:"):
            filename = line.replace("FILENAME:", "").strip().lower()
            filename = re.sub(r'[^a-z0-9_-]', '', filename)
        elif line.startswith("CONTENT:"):
            in_content = True
        elif in_content:
            content_lines.append(line)

    if directory and filename and content_lines:
        return directory, filename, "\n".join(content_lines)
    return None, None, None


def rebuild_backlinks():
    """Scan all [[wikilinks]] and build reverse index."""
    backlinks = defaultdict(list)

    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        if md_file.name in SKIP_FILES or md_file.name.startswith("."):
            continue
        rel = str(md_file.relative_to(WIKI_DIR))
        content = md_file.read_text()

        for link in re.findall(r'\[\[([^\]|#]+)\]\]', content):
            link = link.strip().rstrip("/")
            if link != rel.replace(".md", ""):
                if rel not in backlinks[link]:
                    backlinks[link].append(rel)

    result = {k: sorted(v) for k, v in backlinks.items()}
    BACKLINKS_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    log(f"Backlinks: {len(result)} targets tracked")
    return result


def rebuild_index():
    """Regenerate _index.md from wiki articles."""
    articles = []
    for md_file in sorted(WIKI_DIR.rglob("*.md")):
        if md_file.name in SKIP_FILES or md_file.name.startswith("_"):
            continue
        rel = str(md_file.relative_to(WIKI_DIR))
        content = md_file.read_text()

        # Extract title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else md_file.stem

        # Extract directory
        parts = rel.split("/")
        directory = parts[0] if len(parts) > 1 else "uncategorized"

        articles.append((directory, rel, title))

    # Group by directory
    by_dir = defaultdict(list)
    for d, rel, title in articles:
        by_dir[d].append((rel, title))

    lines = [
        f"# Wiki Index\n",
        f"*Auto-generated. {len(articles)} articles. "
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n",
    ]

    for d in sorted(by_dir.keys()):
        lines.append(f"## {d}/\n")
        for rel, title in sorted(by_dir[d]):
            slug = rel.replace(".md", "")
            lines.append(f"- [[{slug}]] -- {title}\n")
        lines.append("\n")

    INDEX_FILE.write_text("".join(lines))
    log(f"Index: {len(articles)} articles")


def main():
    parser = argparse.ArgumentParser(description="Compile wiki with local LLM via Ollama")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--date-range", default="last 30 days", help="Date range: 'all', 'last 30 days', '2024', '2024-03'")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without writing")
    args = parser.parse_args()

    # Verify Ollama is running
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    except requests.ConnectionError:
        log("Ollama is not running. Start it with: ollama serve")
        return

    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    entries = get_entries(args.date_range)
    absorb_log = load_absorb_log()
    already = set(absorb_log["absorbed"])

    pending = [e for e in entries if e["id"] not in already]
    log(f"Entries: {len(entries)} total, {len(pending)} pending, model={args.model}")

    if args.dry_run:
        for e in pending:
            print(f"  Would process: {e['id']} ({e['date']})")
        return

    if not pending:
        log("Nothing to absorb.")
        rebuild_index()
        rebuild_backlinks()
        return

    new_articles = 0
    for i, entry in enumerate(pending, 1):
        log(f"[{i}/{len(pending)}] {entry['id']}")

        try:
            wiki_index = load_wiki_index()
            response = absorb_entry(entry, args.model, wiki_index)
            directory, filename, content = parse_article(response, entry["id"])

            if directory and filename and content:
                target_dir = WIKI_DIR / directory
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / f"{filename}.md"

                if target.exists():
                    # Merge: append new content to existing article
                    existing = target.read_text()
                    # Simple merge: if article exists, let LLM handle it next time
                    log(f"  Exists: {directory}/{filename}.md (skipped merge)")
                else:
                    target.write_text(content)
                    new_articles += 1
                    log(f"  Created: {directory}/{filename}.md")

                absorb_log["absorbed"].append(entry["id"])
                save_absorb_log(absorb_log)
            else:
                log(f"  Parse failed for {entry['id']}")

        except Exception as e:
            log(f"  Error: {e}")

        # Checkpoint every N entries
        if i % CHECKPOINT_INTERVAL == 0:
            log(f"--- Checkpoint at {i} entries ({new_articles} new articles) ---")
            rebuild_index()
            rebuild_backlinks()

    # Final rebuild
    rebuild_index()
    rebuild_backlinks()
    log(f"Done. {new_articles} new articles created.")


if __name__ == "__main__":
    main()
