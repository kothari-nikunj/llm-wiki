#!/usr/bin/env python3
"""
Ingest any document format into wiki entries using Microsoft's MarkItDown.

Supports: PDF, PowerPoint, Word, Excel, Images (OCR), Audio (transcription),
HTML, CSV, JSON, XML, ZIP, EPUB, YouTube URLs, and more.

Requires: pip install 'markitdown[all]'

Usage:
    # Ingest all supported files from data/documents/
    python3 ingest_documents.py

    # Ingest a single file
    python3 ingest_documents.py --file path/to/document.pdf

    # Ingest with OCR for images in documents (requires OpenAI API key)
    python3 ingest_documents.py --ocr

    # Ingest YouTube video transcripts
    python3 ingest_documents.py --youtube "https://youtube.com/watch?v=..."
"""

import os
import re
import hashlib
import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data" / "documents"
RAW_ENTRIES = ROOT / "raw" / "entries"
RAW_ENTRIES.mkdir(parents=True, exist_ok=True)

# Extensions markitdown can handle
SUPPORTED_EXTS = {
    ".pdf", ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls",
    ".html", ".htm", ".csv", ".json", ".xml", ".zip",
    ".epub", ".mobi",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    ".wav", ".mp3", ".m4a",
    ".txt", ".md", ".rst", ".rtf",
}


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text[:60].strip('-')


def convert_file(file_path, use_ocr=False):
    """Convert a file to markdown using markitdown."""
    from markitdown import MarkItDown

    kwargs = {}
    if use_ocr:
        try:
            from openai import OpenAI
            kwargs["llm_client"] = OpenAI()
            kwargs["llm_model"] = "gpt-4o"
        except ImportError:
            print("  Warning: openai not installed, skipping OCR")

    md = MarkItDown(**kwargs)
    result = md.convert(str(file_path))
    return result.text_content


def convert_youtube(url):
    """Convert a YouTube video transcript to markdown."""
    from markitdown import MarkItDown
    md = MarkItDown()
    result = md.convert(url)
    return result.text_content


def write_entry(entry_id, date, time_str, source_type, title, content, extra=None):
    """Write a single entry to raw/entries/."""
    filename = f"{date}_{slugify(entry_id)}.md"
    filepath = RAW_ENTRIES / filename

    lines = [
        "---",
        f"id: {entry_id}",
        f"date: {date}",
        f'time: "{time_str}"',
        f"source_type: {source_type}",
        f'title: "{title.replace(chr(34), chr(39))}"',
    ]
    if extra:
        for k, v in extra.items():
            lines.append(f'{k}: "{str(v).replace(chr(34), chr(39))}"')
    lines.extend(["tags: []", "---", "", content])

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def ingest_directory(data_dir, use_ocr=False):
    """Ingest all supported files from a directory."""
    if not data_dir.exists():
        print(f"  Documents: skipped (no {data_dir} found)")
        print(f"  Create it and drop files there: mkdir -p {data_dir}")
        return 0

    count = 0
    for file_path in sorted(data_dir.rglob("*")):
        if file_path.is_dir():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTS:
            continue

        print(f"  Processing: {file_path.name}")

        try:
            content = convert_file(file_path, use_ocr=use_ocr)
        except Exception as e:
            print(f"  Error converting {file_path.name}: {e}")
            continue

        if not content or len(content.strip()) < 50:
            print(f"  Skipped (too short or empty): {file_path.name}")
            continue

        # Use file modification time as date
        mtime = os.path.getmtime(file_path)
        dt = datetime.fromtimestamp(mtime)
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M:%S")

        # Generate entry ID from filename
        file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
        entry_id = f"doc-{slugify(file_path.stem)}-{file_hash}"

        # Determine source type from extension
        ext = file_path.suffix.lower()
        source_map = {
            ".pdf": "pdf", ".pptx": "presentation", ".ppt": "presentation",
            ".docx": "document", ".doc": "document",
            ".xlsx": "spreadsheet", ".xls": "spreadsheet",
            ".epub": "ebook", ".html": "webpage", ".htm": "webpage",
            ".jpg": "image", ".jpeg": "image", ".png": "image",
            ".wav": "audio", ".mp3": "audio", ".m4a": "audio",
        }
        source_type = source_map.get(ext, "document")

        # Extract title from first heading or filename
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file_path.stem.replace('-', ' ').replace('_', ' ').title()

        write_entry(entry_id, date_str, time_str, source_type, title,
                    content, {"original_file": file_path.name})
        count += 1

    return count


def ingest_single_file(file_path, use_ocr=False):
    """Ingest a single file."""
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return 0

    # Create a temp directory with just this file and process it
    print(f"  Processing: {file_path.name}")

    try:
        content = convert_file(file_path, use_ocr=use_ocr)
    except Exception as e:
        print(f"  Error: {e}")
        return 0

    if not content or len(content.strip()) < 50:
        print(f"  Skipped (too short or empty)")
        return 0

    mtime = os.path.getmtime(file_path)
    dt = datetime.fromtimestamp(mtime)

    file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
    entry_id = f"doc-{slugify(file_path.stem)}-{file_hash}"

    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else file_path.stem.replace('-', ' ').title()

    write_entry(entry_id, dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S"),
                "document", title, content, {"original_file": file_path.name})
    return 1


def ingest_youtube_url(url):
    """Ingest a YouTube video transcript."""
    print(f"  Processing YouTube: {url}")

    try:
        content = convert_youtube(url)
    except Exception as e:
        print(f"  Error: {e}")
        return 0

    if not content or len(content.strip()) < 50:
        print(f"  Skipped (no transcript available)")
        return 0

    now = datetime.now()
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    entry_id = f"youtube-{url_hash}"

    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else f"YouTube {url_hash}"

    write_entry(entry_id, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                "youtube", title, content, {"url": url})
    return 1


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into wiki entries via MarkItDown")
    parser.add_argument("--file", help="Ingest a single file")
    parser.add_argument("--youtube", help="Ingest a YouTube video transcript")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR for images (requires OpenAI API key)")
    parser.add_argument("--dir", default=str(DATA_DIR), help=f"Directory to scan (default: {DATA_DIR})")
    args = parser.parse_args()

    try:
        from markitdown import MarkItDown
    except ImportError:
        print("markitdown not installed. Run:")
        print("  pip install 'markitdown[all]'")
        return

    print("Document Ingest (via MarkItDown)")
    print("=" * 40)

    total = 0

    if args.youtube:
        total += ingest_youtube_url(args.youtube)
    elif args.file:
        total += ingest_single_file(args.file, use_ocr=args.ocr)
    else:
        total += ingest_directory(Path(args.dir), use_ocr=args.ocr)

    print()
    print(f"Done: {total} entries written to raw/entries/")


if __name__ == "__main__":
    main()
