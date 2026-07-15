# Demo

Visual tours of the agent, one page per slide. **Every screenshot is real output from
a real run** — the agent driven the way you'd drive it, not a script calling internals.
Reproduce any of them with **[`../EXAMPLES.md`](../EXAMPLES.md)**.

## [`carousel.pdf`](carousel.pdf) — 8 things it does

Running locally on a 7B model (Ollama), with **no cloud, no API keys, and $0
per-token cost**:

1. Build a working file from one sentence
2. Fix its own mistakes (reflexion)
3. Refuse dangerous commands (guardrails)
4. Stream a live web dashboard
5. Read 11+ languages (tree-sitter)
6. Semantic go-to-definition (LSP)
7. Whole-repo symbol graph + impact analysis
8. Full run telemetry at $0 cost

## [`carousel_post2.pdf`](carousel_post2.pdf) — "I gave an AI agent shell access"

The six layers between a language model and your filesystem, each shown firing inside
a real run in the [VS Code extension](../vscode-extension/):

1. **Refuses** — told to run `rm -rf /`, it plans it, tries it, and blocks itself
2. **No disguises** — asked with the command disguised as `s"u"do`, it still never runs
3. **Confined** — it can't read `../../etc/passwd`; it's locked to its workspace
4. **No leaks** — reads a file full of API keys; every secret is `[REDACTED]` before
   the model sees it
5. **You decide** — nothing risky runs until a human clicks Approve
6. **Audited** — every decision lands in an append-only JSON audit log

> The guardrails sit **outside** the model, in code you own. That matters: while
> building these demos the agent sometimes refused a dangerous command on its own and
> sometimes didn't. A model's judgement is not a security boundary.

Companion code for the book *Building a Local AI Coding Agent* by Natarajan Ramasamy.
