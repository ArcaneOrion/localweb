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
  "write_token": "local-random-token",
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
- `write_token` 是项目级本地写入令牌，由 shell 对 `/api/choice` 和 `/api/panel-input` 发送 `X-LocalWeb-Token` 时使用；不要把它用于权限确认或远程访问。

## 写入边界

LocalWeb 默认只绑定 `127.0.0.1`，写接口还要求 `X-LocalWeb-Token`。这可以阻止普通外部网页直接向本机 LocalWeb 注入 choice 或 panel input。

`/api/choice` 只接受当前 `active_choice_id`，且 `value` 必须属于当前 `state.choices`。panel input 不强制结构化内容；服务端只校验合法 `input_id` 和非空文本，显式提交按钮属于 panel 编写约束。

## 事件（Events）

`events.jsonl` 是 agent 到 Web 的事件流和审计历史。每行都是一个 JSON 对象，至少包含 `type` 和 `ts` 字段。

`inbox/events.jsonl` 是 Web 到 CLI 的低风险上下文输入流。底部辅助选择事件格式：

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

panel 内嵌交互需要返回 CLI 时，通过 shell bridge 写入 Markdown 输入事件：

```json
{
  "event_id": "uuid",
  "type": "panel_input",
  "input_id": "review-context",
  "text": "## 用户补充\n\n- 我更关注 auth 模块",
  "label": "风险关注点",
  "panel_id": "panels/review.html",
  "meta": {},
  "session_id": "cli-main",
  "ts": "2026-06-05T12:00:00+00:00"
}
```

默认情况下，`wait` 命令只消费第一个未消费的匹配浏览器输入，并在 `events.jsonl` 中记录 consumed 事件。纯展示 panel 不需要发布 `choices`，也不需要 `wait`。

对于需要回到 CLI 的浏览器交互，必须先发布上下文输入，再立刻运行对应 `localweb wait`，并保持本轮 CLI 打开直到输入被消费。浏览器点击或输入是持久化的 inbox 事件；它们不会自动出现在终端中，除非 CLI 命令去读取。`panel/status/choice` 只完成可见更新，`wait` 才把浏览器输入带回模型上下文。

```bash
# 底部辅助 choices：stdout 是短值，如 source_path
uv run scripts/localweb.py wait --id next

# panel 主交互：stdout 是 Markdown 原文
uv run scripts/localweb.py wait --id review-context --type panel
```

发布可回传输入的命令应把等待态写进 stdout JSON。`choice` 会自动输出精确的 `next_command`；`panel` 或 `status` 只有在调用方声明 `--wait-id` 时输出精确命令。

```json
{
  "status": "waiting_for_user",
  "command_status": "ok",
  "wait_required": true,
  "wait": {"id": "next", "type": "choice"},
  "next_command": "uv run scripts/localweb.py wait --id next"
}
```

`--type any` 可用于少数不关心来源的兼容场景；推荐 agent 默认明确选择 `choice` 或 `panel`。

如果用户不想点选，可以显式运行 `localweb wait --id <choice_id> --cli-fallback`，允许交互式 TTY 中的文字输入作为兜底结果。该模式会记录 `cli_override`；管道 stdin 不会被默认当作选择。

## 事件类型

### Choice 生命周期

- `choice_requested`：由 `choice` 命令发布建议型输入，写入 `events.jsonl`
- `choice`：用户在浏览器中提供低风险上下文输入，写入 `inbox/events.jsonl`
- `choice_received`：server 收到 choice，写入 `events.jsonl`
- `choice_consumed`：`wait` 读取事件，写入 `events.jsonl`
- `choice_obsoleted`：新的 `choice` 命令使用相同 ID，作废旧的未消费事件，写入 `events.jsonl`
- `cli_override`：显式启用 `--cli-fallback` 时，用户在交互式 CLI 输入文字，写入 `events.jsonl`

### Panel Input 生命周期

- `panel_input`：panel 通过 `postMessage` 显式发送 Markdown，上游 shell 写入 `inbox/events.jsonl`
- `panel_input_received`：server 收到 panel 输入，写入 `events.jsonl`
- `panel_input_consumed`：`wait --type panel` 读取事件，写入 `events.jsonl`
- `panel_input_obsoleted`：同 `input_id` 的新 panel 输入作废旧的未消费事件，写入 `events.jsonl`

### 维护

- `inbox_cleaned`：`clean` 命令从 inbox 移除已消费/已作废事件，写入 `events.jsonl`

## Choice ID 重用

创建新的 `choice --id foo` 会自动作废 inbox 中所有未消费的、相同 `choice_id` 的事件。这防止在多轮交互中重用 ID 时，`wait` 读取到过期的点击。

`wait` 命令会跳过在 `events.jsonl` 中标记为 `choice_consumed`、`choice_obsoleted`、`panel_input_consumed` 或 `panel_input_obsoleted` 的事件。LocalWeb 假设同一个输入 ID 同时只有一个 CLI consumer 在等待；并发运行多个同 ID 的 `wait` 不属于推荐用法。

同一个 `input_id` 收到新的 `panel_input` 时，旧的未消费 panel 输入会被标记为 `panel_input_obsoleted`，避免 CLI 读到用户后来已经替换掉的 Markdown 草稿。

## Inbox 维护

inbox 会累积所有浏览器点击和 panel 输入，直到显式清理。定期运行 `localweb clean` 来移除已消费和已作废的事件。`clean` 会用文件锁和原子替换重写 inbox，不会移除未消费事件。
