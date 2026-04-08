---
title: File Over App
type: concept
created: 2024-01-01
last_updated: 2024-01-01
related: ["[[concepts/llm-knowledge-bases]]", "[[concepts/wikilinks]]"]
sources: []
---

# File Over App

File Over App is a philosophy that prioritizes storing data in universal file formats (markdown, images, plain text) rather than proprietary application databases. The principle: files outlast applications. Any tool can read a markdown file. Not every tool can read a database export from a discontinued app.

## Implications

When a knowledge base is stored as files:

- **Portability.** Move it between tools. View in Obsidian, VS Code, a custom web viewer, or plain `cat`.
- **Interoperability.** The Unix toolkit works on files. Agents can natively read and understand them.
- **Ownership.** Data lives on your machine, not in a cloud service. No vendor lock-in.
- **Durability.** Markdown files written today will be readable in 20 years.

## In Practice

This wiki follows File Over App. All articles are `.md` files in a directory structure. [[concepts/wikilinks]] provide the hyperlink layer. Any AI agent can read and operate on the files because they are plain text.

## Trade-offs

The approach requires more setup than purpose-built apps. There is no built-in sync, no mobile app, no collaborative editing. Agents reduce the friction of maintenance, but the user must manage the file system.
