---
title: LLM Knowledge Bases
type: concept
created: 2024-01-01
last_updated: 2024-01-01
related: ["[[concepts/file-over-app]]", "[[concepts/wikilinks]]"]
sources: []
---

# LLM Knowledge Bases

An LLM knowledge base is a personal wiki maintained by a language model. Raw data from various sources (writing, tweets, messages, bookmarks) is ingested and compiled into interconnected markdown articles. The LLM acts as a librarian: filing information, finding connections, and maintaining the structure.

## Architecture

The system has three layers:

1. **Raw sources** are immutable original documents stored in `data/`. These are never modified after ingest.
2. **The wiki** is a collection of compiled markdown articles with frontmatter, wikilinks, and thematic organization. The LLM writes and maintains all of this.
3. **The schema** is a configuration document (the skill file) that defines wiki structure and agent workflows.

## How It Works

The LLM processes entries one at a time, chronologically. For each entry it reads the text, understands what it means, matches it against existing articles, and either updates existing pages or creates new ones. Every 15 entries it runs a checkpoint to rebuild indexes and audit quality.

## Key Insight

The tedious part of maintaining a knowledge base is not the reading or the thinking. It is the bookkeeping: updating cross-references, filing things correctly, maintaining consistency. LLMs handle this without fatigue or forgetfulness.

## Origins

The approach was popularized by Andrej Karpathy in 2025, drawing on the [[concepts/file-over-app]] philosophy and Vannevar Bush's 1945 Memex concept of personal, curated knowledge stores with associative document trails.
