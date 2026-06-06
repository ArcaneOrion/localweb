---
name: html-companion
description: Start and drive a project-level local HTML companion interface for CLI agents. Use when a user wants agent output presented as visual, structured, interactive local HTML panels for learning, code understanding, planning, debugging, reviews, research summaries, or optional low-risk context interactions while keeping the terminal CLI as the primary conversation, permission, and control surface.
---

# HTML Companion

Use HTML Companion to attach a local browser-based visual layer to the current CLI agent session.

The terminal remains the control plane and source of conversation context. The browser is only a project-level visual projection plus an optional low-risk context surface.

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

5. Offer optional context interactions only when they reduce user friction. Pure display is valid and often preferable.

```bash
uv run scripts/localweb.py choice \
  --id next \
  --option architecture="Show architecture" \
  --option source_path="Show source path" \
  --option exercise="Make exercise"
```

Choices are model-suggested directions, not a required UI pattern. Rich panels may use tabs, filters, annotations, sliders, comparison cards, or forms when those help the user provide context that would be awkward in terminal prose.

6. Read the user's browser input only when the CLI flow needs it:

```bash
uv run scripts/localweb.py wait --id next
```

`wait` prints only the selected value, such as `source_path`. Treat that printed value as a low-risk user context signal in the CLI flow.

If the user may prefer typing directly in the terminal instead of clicking, opt in explicitly:

```bash
uv run scripts/localweb.py wait --id next --cli-fallback
```

`--cli-fallback` only accepts interactive TTY input. Piped stdin is ignored by default so automation cannot accidentally become a user choice.

For a live browser input, run `wait` immediately after publishing the context request and keep the CLI turn open while the user responds. Do not end the turn expecting browser input to appear in the terminal automatically; it is stored in `.localweb/inbox/events.jsonl` until `wait` consumes it.

7. 定期清理已消费事件（可选）：

```bash
uv run scripts/localweb.py clean
```

这会从 inbox 中移除已消费和已作废的事件，保持文件精简。可以随时安全运行。

## 关键行为

- **choice ID 可以重复使用**：创建新的 `choice --id foo` 时，会自动作废同 ID 的所有未消费事件。这防止 `wait` 读取到过期的点击。
- **Inbox 增长**：inbox 会累积所有点击，直到被清理。定期运行 `clean` 来移除已消费的事件。
- **事件类型**：`choice_consumed`（被 wait 读取）、`choice_obsoleted`（被新 choice 替换）、`cli_override`（显式 CLI 文字兜底）、`inbox_cleaned`（维护操作）。

## 规则

- Keep all runtime artifacts under the target project's `.localweb/`.
- Do not write runtime state into the skill installation directory.
- Keep CLI as the only primary model context.
- Do not use Web interactions for dangerous permissions, command execution, file deletion, or network approval.
- Bind local servers to `127.0.0.1` unless the user explicitly asks otherwise.
- Use the Web UI for visual comprehension and context collection: diagrams, comparisons, timelines, annotated diffs, filters, rankings, small forms, and optional direction cards.
- Do not depend on a specific panel style. The shell is replaceable; the protocol is the stable contract.

## References

- Read `references/protocol.md` before changing `.localweb/` file shapes.
- Read `references/html-patterns.md` when deciding what kind of panel to generate.
- Read `references/visual-style.md` before editing the default shell UI.
