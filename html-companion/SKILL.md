---
name: html-companion
description: Start and drive a project-level local HTML companion interface for CLI agents. Use when a user wants agent output presented as visual, structured, interactive local HTML panels for learning, code understanding, planning, debugging, reviews, research summaries, or A/B/C/D lightweight choices while keeping the terminal CLI as the primary conversation and permission surface.
---

# HTML Companion

Use HTML Companion to attach a local browser-based visual layer to the current CLI agent session.

The terminal remains the control plane and source of conversation context. The browser is only a project-level visual projection plus a low-risk choice surface.

## Quick Start

Run commands from this skill directory unless the tool is already on PATH:

```bash
uv run scripts/localweb.py init
uv run scripts/localweb.py serve --port 8765
```

For another project root:

```bash
uv run scripts/localweb.py init --project /path/to/project
uv run scripts/localweb.py serve --project /path/to/project --port 8765
```

When `serve` starts, give the user the printed `url`.

## Standard Workflow

1. Initialize the project-level runtime directory:

```bash
uv run scripts/localweb.py init
```

2. Start the local server:

```bash
uv run scripts/localweb.py serve --port 8765
```

3. Generate a self-contained HTML panel for the current task.

Prefer full HTML documents with inline CSS/JS. Store temporary panel drafts anywhere in the project, then register them:

```bash
uv run scripts/localweb.py panel --id main --file explanation.html --title "Feature explainer"
```

4. Update visible state and left-side context:

```bash
uv run scripts/localweb.py status \
  --state waiting_for_user \
  --title "Choose the next view" \
  --context "Task=Understand auth flow" \
  --context "Stage=Module map"
```

5. Offer lightweight choices when useful:

```bash
uv run scripts/localweb.py choice \
  --id next \
  --option A="Show architecture" \
  --option B="Show source path" \
  --option C="Make exercise" \
  --option D="Return"
```

6. Read the user's browser click only when the CLI flow needs it:

```bash
uv run scripts/localweb.py wait --id next
```

`wait` prints only the selected value, such as `B`. Treat that printed value as the user response in the CLI context.

For a live choice, run `wait` immediately after publishing the choices and keep the CLI turn open while the user clicks. Do not end the turn expecting a browser click to appear in the terminal automatically; the click is stored in `.localweb/inbox/events.jsonl` until `wait` consumes it.

## Rules

- Keep all runtime artifacts under the target project's `.localweb/`.
- Do not write runtime state into the skill installation directory.
- Keep CLI as the only primary model context.
- Do not use Web choices for dangerous permissions, command execution, file deletion, or network approval.
- Bind local servers to `127.0.0.1` unless the user explicitly asks otherwise.
- Use the Web UI for visual comprehension: diagrams, comparisons, timelines, annotated diffs, learning panels, and small choice cards.
- Do not depend on a specific panel style. The shell is replaceable; the protocol is the stable contract.

## References

- Read `references/protocol.md` before changing `.localweb/` file shapes.
- Read `references/html-patterns.md` when deciding what kind of panel to generate.
- Read `references/visual-style.md` before editing the default shell UI.
