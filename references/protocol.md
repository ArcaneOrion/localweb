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

## 事件（Events）

`events.jsonl` 是 agent 到 Web 的事件流和审计历史。每行都是一个 JSON 对象，至少包含 `type` 和 `ts` 字段。

`inbox/events.jsonl` 是 Web 到 CLI 的事件流。选择事件格式：

```json
{
  "event_id": "uuid",
  "type": "choice",
  "choice_id": "next",
  "value": "B",
  "label": "显示源码路径",
  "session_id": "cli-main",
  "ts": "2026-06-05T12:00:00+00:00"
}
```

`wait` 命令消费第一个未消费的匹配事件，并在 `events.jsonl` 中记录 `choice_consumed` 事件。

对于实时浏览器交互，先发布 choices，然后在结束 CLI 回合前运行 `localweb wait --id <choice_id>`。浏览器点击是持久化的 inbox 事件；它们不会自动出现在终端中，除非 CLI 命令去读取。

## 事件类型

### Choice 生命周期

- `choice_requested`：由 `choice` 命令发布，写入 `events.jsonl`
- `choice`：用户在浏览器中点击，写入 `inbox/events.jsonl`
- `choice_consumed`：`wait` 读取事件，写入 `events.jsonl`
- `choice_obsoleted`：新的 `choice` 命令使用相同 ID，作废旧的未消费事件，写入 `events.jsonl`

### 维护

- `inbox_cleaned`：`clean` 命令从 inbox 移除已消费/已作废事件，写入 `events.jsonl`

## Choice ID 重用

创建新的 `choice --id foo` 会自动作废 inbox 中所有未消费的、相同 `choice_id` 的事件。这防止在多轮交互中重用 ID 时，`wait` 读取到过期的点击。

`wait` 命令会跳过在 `events.jsonl` 中标记为 `choice_consumed` 或 `choice_obsoleted` 的事件。

## Inbox 维护

inbox 会累积所有浏览器点击，直到显式清理。定期运行 `localweb clean` 来移除已消费和已作废的事件。这个操作随时都是安全的，不会影响未消费的事件。
