---
name: localweb
description: 为 CLI agent 启动并驱动项目级本地 Web 可视化层。适用于学习讲解、代码理解、计划、调试、审查、研究总结等任务，需要把 agent 输出呈现为结构化、可交互的 HTML panel，同时保持 CLI 作为主会话、主权限面和主控制面。
---

# LocalWeb

LocalWeb 是 CLI agent 的本地 Web 可视化与上下文交互层。

终端始终是主控制面和主上下文来源。浏览器只负责项目级可视化投影，以及可选的低风险上下文输入。

## 快速开始

从本 skill 目录运行命令，除非工具已经在 `PATH` 中：

```bash
uv run scripts/localweb.py init
uv run scripts/localweb.py serve --port 8765
```

为其他项目根目录启动：

```bash
uv run scripts/localweb.py init --project /path/to/project
uv run scripts/localweb.py serve --project /path/to/project --port 8765
```

`serve` 启动后，把输出的 `url` 告诉用户。

如果旧项目启动时报 shell 缺少写入令牌支持，运行：

```bash
uv run scripts/localweb.py init --project /path/to/project --shell-only
```

这只刷新 `.localweb/shell/`，不改 `state.json`、inbox 或 panel。

## 标准流程

1. 初始化项目级运行目录：

```bash
uv run scripts/localweb.py init
```

2. 启动本地服务：

```bash
uv run scripts/localweb.py serve --port 8765
```

3. 为当前任务生成一个 self-contained HTML panel。

优先使用完整 HTML 文档和内联 CSS/JS。临时草稿可以放在项目内任意位置，然后注册：

```bash
uv run scripts/localweb.py panel --id main --file explanation.html --title "功能解释"
```

学习讲解可使用内置 learn 子模式，把结构化 lesson JSON 渲染为概念卡、结构图、例子和问答训练面板：

```bash
uv run scripts/localweb.py learn \
  --id epsilon-delta \
  --file learn/examples/epsilon-delta.json
```

如果 lesson 含 `questions`，`learn` 默认进入等待态并输出精确的 `next_command`。浏览器提交的回答仍通过现有 panel input 进入 inbox，必须按输出运行 `wait --type panel` 才会回到 CLI 上下文。

如果这个 panel 会通过 `postMessage` 返回输入，注册或切状态时必须同时声明 `--wait-id`，让命令输出精确的 `next_command`：

```bash
uv run scripts/localweb.py panel \
  --id review \
  --file review.html \
  --title "补充审查上下文" \
  --wait-id review-context \
  --wait-type panel
```

4. 更新可见状态和左侧上下文：

```bash
uv run scripts/localweb.py status \
  --state working \
  --title "认证流程图解" \
  --context "任务=理解认证流程" \
  --context "阶段=模块地图"
```

如果这次状态更新是在请求浏览器输入，必须带上 `--wait-id`：

```bash
uv run scripts/localweb.py status \
  --state waiting_for_user \
  --title "补充审查上下文" \
  --wait-id review-context \
  --wait-type panel
```

5. 判断这次 Web 更新是否需要回到 CLI：

- **纯展示 panel**：只用于解释、图解或局部浏览器内交互，不需要用户结果回到模型上下文。此时不要发布 `choice`，也不要运行 `wait`。
- **浏览器输入闭环**：只要发布了会写入 inbox 的交互，无论是 panel 内的 `panel_input`，还是底部 `choices`，都必须在发布后立刻运行对应 `wait`，保持 CLI 回合打开直到输入被消费。不要把“稍后再等”留给模型记忆。

6. 只有在能降低用户表达成本时，才提供可选上下文输入。纯展示是有效且常见的路径。

优先把主要交互放在 HTML panel 内部，例如标注、筛选、滑块、小表单、圈选区域或 Markdown 文本框。panel 需要把结果返回 CLI 时，应设计成由用户显式点击发送按钮，再通过 `postMessage` 发出 Markdown 文本：

```js
window.parent.postMessage({
  localweb: true,
  type: "panel_input",
  input_id: "review-context",
  text: "## 用户补充\n\n- 我更关注 auth 模块\n- 请优先检查 token refresh"
}, "*");
```

发布这种 panel、切到等待状态后，CLI agent 必须立刻执行命令输出里的 `next_command`。对应命令形如：

```bash
uv run scripts/localweb.py wait --id review-context --type panel
```

`wait --type panel` 只输出 Markdown 原文。把它当作用户通过 Web 面板补充的低风险上下文，而不是权限确认。

7. 底部 `choices` 是辅助通道，适合少量方向建议或兜底选择，不是固定主交互模式。

```bash
uv run scripts/localweb.py choice \
  --id next \
  --option architecture="看架构" \
  --option source_path="看源码路径" \
  --option exercise="做练习"
```

这些选项是模型建议的方向，不是固定 UI 模式。HTML panel 也可以使用 tab、筛选器、标注、滑块、对比卡片或表单，帮助用户表达终端文字里难以描述的上下文。

如果发布了 `choice`，必须紧跟 `wait`，不要结束 CLI 回合后再等待：

```bash
uv run scripts/localweb.py wait --id next
```

`wait` 只输出被选择的值，例如 `source_path`。把这个值当作低风险用户上下文信号，而不是权限确认。

`choice` 成功发布后会输出 `status: "waiting_for_user"`、`wait_required: true` 和 `next_command`。模型必须把这个 JSON 当作控制流提示，而不是普通完成态。

如果用户更想直接在终端输入文字，可以显式启用 CLI 兜底：

```bash
uv run scripts/localweb.py wait --id next --cli-fallback
```

`--cli-fallback` 只接受交互式 TTY 输入。默认不会把管道 stdin 当成用户选择，避免自动化流程误读。

实时浏览器输入场景中，`panel/status/choice` 的可见更新不是闭环终点，`wait` 才是输入闸门。浏览器输入会存入 `.localweb/inbox/events.jsonl`，只有 `wait` 消费后才进入 CLI 上下文。

8. 定期清理已消费和已作废事件（可选）：

```bash
uv run scripts/localweb.py clean
```

这会从 inbox 中移除已消费和已作废的事件，保持文件精简。可以随时安全运行。

## 关键行为

- **写接口有本地令牌**：shell 从 `state.json` 读取 `write_token`，并在提交 choice 或 panel input 时发送 `X-LocalWeb-Token`。这是本地写入边界，不是权限确认机制。
- **choice ID 可以重复使用**：创建新的 `choice --id foo` 时，会自动作废同 ID 的所有未消费事件，防止 `wait` 读到过期点击。
- **等待态输出 next_command**：`choice` 会自动输出下一条 `wait` 命令；`panel` 和 `status` 在传入 `--wait-id` 时也会输出 `next_command`。
- **Inbox 会累积**：浏览器输入会留在 inbox，直到被消费或清理。定期运行 `clean`。
- **事件类型**：`choice_received` / `panel_input_received`（server 收到浏览器输入）、`choice_consumed` / `panel_input_consumed`（输入被 wait 读取）、`choice_obsoleted` / `panel_input_obsoleted`（同 ID 旧事件被替换）、`cli_override`（显式 CLI 文字兜底）、`inbox_cleaned`（维护操作）。

## 规则

- 所有运行时产物必须写在目标项目的 `.localweb/` 下。
- 不要把运行时状态写进 skill 安装目录。
- CLI 是唯一主模型上下文。
- 发布任何可回传浏览器输入后，必须立刻运行对应 `wait` 并保持本轮 CLI 打开；否则用户在浏览器里说的话只会留在 inbox，不会进入模型上下文。
- Web 交互不能用于危险权限、命令执行、文件删除或网络授权。
- 除非用户明确要求，否则服务只绑定 `127.0.0.1`。
- Web UI 用于可视化理解和上下文收集：图解、对比、时间线、带注释 diff、筛选、排序、小表单和可选方向卡。
- `learn` 只是学习面板生成模式，不是独立学习平台；CLI 仍负责教学判断、错因审计和下一步选择。
- 不依赖某一种 panel 风格。shell 可以替换，文件协议才是稳定契约。

## 参考

- 修改 `.localweb/` 文件形状前，先读 `references/protocol.md`。
- 决定生成哪类 panel 前，先读 `references/html-patterns.md`。
- 修改默认 shell UI 前，先读 `references/visual-style.md`。
