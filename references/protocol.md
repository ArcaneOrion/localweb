# LocalWeb 文件协议

LocalWeb 协议是项目级协议。运行时文件放在目标项目的 `.localweb/` 目录下，不能写入 skill 安装目录。

## 目录结构

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

`state.json` 是 shell 读取的当前 UI 快照。

必要字段：

```json
{
  "schema_version": 1,
  "session_id": "cli-main",
  "title": "LocalWeb",
  "status": "idle",
  "active_panel": "panels/main.html",
  "active_choice_id": null,
  "updated_at": "2026-06-05T12:00:00+00:00",
  "context": [{"label": "任务", "value": "理解模块流程"}],
  "choices": [{"id": "source_path", "label": "看源码路径"}]
}
```

规则：

- `active_panel` 必须指向 `.localweb/panels/` 下的文件。
- `choices` 是 CLI agent 建议的可选低风险上下文输入；纯展示 panel 不需要 choices。
- choice ID 是任意安全字符串，不是固定字母。
- `active_choice_id` 用来把浏览器输入关联到 `localweb wait --id`。

## 事件（Events）

`events.jsonl` 是 agent 到 Web 的事件流和审计历史。每行都是一个 JSON 对象，至少包含 `type` 和 `ts` 字段。

`inbox/events.jsonl` 是 Web 到 CLI 的低风险上下文输入流。MVP 的浏览器回传事件格式：

```json
{
  "event_id": "uuid",
  "type": "choice",
  "choice_id": "next",
  "value": "source_path",
  "label": "显示源码路径",
  "session_id": "cli-main",
  "ts": "2026-06-05T12:00:00+00:00"
}
```

默认情况下，`wait` 命令只消费第一个未消费的匹配浏览器输入，并在 `events.jsonl` 中记录 `choice_consumed` 事件。纯展示 panel 不需要发布 `choices`，也不需要 `wait`。

对于需要回到 CLI 的浏览器交互，先发布上下文输入，再在结束 CLI 回合前运行 `localweb wait --id <choice_id>`。浏览器点击或输入是持久化的 inbox 事件；它们不会自动出现在终端中，除非 CLI 命令去读取。

如果用户不想点选，可以显式运行 `localweb wait --id <choice_id> --cli-fallback`，允许交互式 TTY 中的文字输入作为兜底结果。该模式会记录 `cli_override`；管道 stdin 不会被默认当作选择。

## 事件类型

### Choice 生命周期

- `choice_requested`：由 `choice` 命令发布建议型输入，写入 `events.jsonl`
- `choice`：用户在浏览器中提供低风险上下文输入，写入 `inbox/events.jsonl`
- `choice_consumed`：`wait` 读取事件，写入 `events.jsonl`
- `choice_obsoleted`：新的 `choice` 命令使用相同 ID，作废旧的未消费事件，写入 `events.jsonl`
- `cli_override`：显式启用 `--cli-fallback` 时，用户在交互式 CLI 输入文字，写入 `events.jsonl`

### 维护

- `inbox_cleaned`：`clean` 命令从 inbox 移除已消费/已作废事件，写入 `events.jsonl`

## Choice ID 重用

创建新的 `choice --id foo` 会自动作废 inbox 中所有未消费的、相同 `choice_id` 的事件。这防止在多轮交互中重用 ID 时，`wait` 读取到过期的点击。

`wait` 命令会跳过在 `events.jsonl` 中标记为 `choice_consumed` 或 `choice_obsoleted` 的事件。

## Inbox 维护

inbox 会累积所有浏览器点击，直到显式清理。定期运行 `localweb clean` 来移除已消费和已作废的事件。这个操作随时都是安全的，不会影响未消费的事件。
