# HTML Companion Protocol

The protocol is project-level. Runtime files live under the target project's `.localweb/` directory, never under the skill installation directory.

## Directory

```text
.localweb/
├── state.json
├── events.jsonl
├── inbox/events.jsonl
├── panels/*.html
├── shell/{index.html,app.js,theme.css}
└── assets/generated/
```

## `state.json`

`state.json` is the current UI snapshot read by the shell.

Required fields:

```json
{
  "schema_version": 1,
  "session_id": "cli-main",
  "title": "HTML Companion",
  "status": "idle",
  "active_panel": "panels/main.html",
  "active_choice_id": null,
  "updated_at": "2026-06-05T12:00:00+00:00",
  "context": [{"label": "Task", "value": "Understand module flow"}],
  "choices": [{"id": "A", "label": "Show architecture"}]
}
```

Rules:

- `active_panel` must point to a file below `.localweb/panels/`.
- `choices` are low-risk user choices only.
- `active_choice_id` links browser clicks to `localweb wait --id`.

## Events

`events.jsonl` is agent-to-Web and audit history. Each line is a JSON object with at least `type` and `ts`.

`inbox/events.jsonl` is Web-to-CLI. Choice events use:

```json
{
  "event_id": "uuid",
  "type": "choice",
  "choice_id": "next",
  "value": "B",
  "label": "Show source path",
  "session_id": "cli-main",
  "ts": "2026-06-05T12:00:00+00:00"
}
```

`wait` consumes the first unconsumed matching choice and records a `choice_consumed` event in `events.jsonl`.

For live browser interaction, publish choices and then run `localweb wait --id <choice_id>` before ending the CLI turn. Browser clicks are durable inbox events; they do not automatically appear in the terminal unless a CLI command reads them.
