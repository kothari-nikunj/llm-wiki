---
title: Wikilinks
type: concept
created: 2024-01-01
last_updated: 2024-01-01
related: ["[[concepts/llm-knowledge-bases]]", "[[concepts/file-over-app]]"]
sources: []
---

# Wikilinks

Wikilinks are internal cross-references between wiki articles using the `[[double bracket]]` syntax. They form the connective tissue of the knowledge base.

## Syntax

Two formats are supported:

- `[[concepts/file-over-app]]` links to the article and displays the slug as text
- `[[concepts/file-over-app|File Over App]]` links to the article and displays custom text

## Purpose

Wikilinks serve two functions:

1. **Navigation.** Readers follow links to explore related topics.
2. **Backlinks.** The system tracks which articles link to which, creating a reverse index stored in `_backlinks.json`. This surfaces connections the author may not have explicitly made.

## In the Web Viewer

The web viewer renders wikilinks as clickable HTML links with a dotted blue underline to distinguish them from external links. Each article page shows a "Linked from" section listing all articles that reference it.

## Agent Use

When the LLM creates or updates articles, it inserts wikilinks wherever a reference to another article is relevant. The `_backlinks.json` index is rebuilt periodically to keep reverse references current.
