# HTML Companion Skill 设计稿

## 1. 定位

HTML Companion 是一个通过 skill 机制外挂到本地 agent CLI 的可视化伴生界面。

它不试图取代终端，也不接管 agent 的主会话。它的目标是让 agent 在处理学习、代码理解、方案对比、调试、审查、研究总结等任务时，能把结果输出成更高带宽的 HTML 可视化界面。

核心定义：

```text
CLI agent = 主会话、主上下文、主控制面
Web companion = 可视化投影、结构化阅读面、可选上下文输入面
```

第一性原理：

- 人类通过视觉和空间结构吸收复杂信息的效率通常高于线性文本。
- Markdown 适合叙述，但不适合承载复杂布局、图表、状态、对比和交互。
- HTML 是 agent 可以直接生成、浏览器可以直接渲染、用户可以直接交互的通用媒介。
- 本地运行时，权限确认和危险操作继续留在 CLI，Web 只做展示和低风险输入。

## 2. 设计目标

### 必须满足

- 通过 skill 使用，不要求替换 Codex、Claude Code 等现有 CLI。
- CLI 会话上下文为唯一主上下文。
- Web 端展示 agent 生成的 HTML panel，并在需要时承载低风险上下文交互。
- UI shell 与通信协议解耦，未来可以换视觉风格或前端框架。
- 默认只监听 `127.0.0.1`。
- Web 点击必须显式返回 CLI 后，才算进入模型上下文。

### 非目标

- 不做完整 Web 版终端。
- 不在 Web 端处理高风险权限确认。
- 不让 Web studio 自己维护独立 agent 对话上下文。
- 不把某一套 UI 风格写死进通信协议。
- 不强依赖 React、Next.js、复杂构建链路。

## 3. 总体架构

```text
┌────────────────────────────────────────────┐
│ Agent CLI: Codex / Claude Code / etc        │
│ - 用户主要输入仍在这里                       │
│ - 权限确认仍在这里                           │
│ - 模型上下文以这里为准                       │
│ - 通过 skill 调 localweb 脚本                 │
└──────────────────┬─────────────────────────┘
                   │ 写 state / panel / optional inputs
                   ▼
┌────────────────────────────────────────────┐
│ .localweb/ 文件协议层                        │
│ state.json                                  │
│ events.jsonl                                │
│ panels/*.html                               │
│ inbox/events.jsonl                          │
└──────────────────┬─────────────────────────┘
                   │ serve / watch / SSE
                   ▼
┌────────────────────────────────────────────┐
│ LocalWeb Server                             │
│ 127.0.0.1 only                              │
│ 静态服务 + 文件监听 + 输入事件写入 inbox       │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ Browser Companion UI                        │
│ 外层卡通终端框架 + 左侧上下文 + 中间 HTML 舞台 │
└────────────────────────────────────────────┘
```

关键解耦：

```text
信息协议层：state.json / events.jsonl / inbox / panels
服务层：localweb serve / watch / HTTP / SSE
视觉层：shell HTML/CSS/JS
内容层：agent 生成的任意 self-contained HTML panel
```

## 4. 文件协议

### 项目级运行目录

skill 本体和运行产物必须分离：

```text
skill 本体：
  安装在 Codex/Claude 的 skills 目录中，提供 SKILL.md、脚本、shell 模板和协议说明。

项目运行产物：
  写入当前项目根目录下的 .localweb/，跟随项目走，不污染全局 skill 目录。
```

默认项目根目录是 agent CLI 当前所在的 `cwd`。所有命令都应支持 `--project <path>` 覆盖项目根目录，但不传时必须使用当前目录。

默认工作目录：

```text
<project-root>/
└── .localweb/
├── state.json
├── events.jsonl
├── inbox/
│   └── events.jsonl
├── panels/
│   ├── main.html
│   ├── concept-map.html
│   └── diff-review.html
└── assets/
    └── generated/
```

### state.json

`state.json` 表示当前 UI 快照。Web shell 读取它，决定显示哪个 panel、顶部状态、左侧上下文和可选交互区。

示例：

```json
{
  "schema_version": 1,
  "session_id": "codex-main",
  "title": "React Fiber 学习图解",
  "status": "waiting_for_user",
  "active_panel": "panels/main.html",
  "updated_at": "2026-06-05T17:40:00+08:00",
  "context": [
    {"label": "当前任务", "value": "理解 React Fiber"},
    {"label": "当前阶段", "value": "概念解释"},
    {"label": "输入来源", "value": "CLI"}
  ],
  "choices": [
    {"id": "overview", "label": "看整体流程"},
    {"id": "source_path", "label": "看源码路径"},
    {"id": "exercise", "label": "做练习"}
  ]
}
```

### events.jsonl

`events.jsonl` 是 agent 到 Web 的时间线事件。它用于审计、回放和顶部状态提示。

示例：

```jsonl
{"type":"panel_updated","panel":"panels/main.html","ts":"2026-06-05T17:40:00+08:00"}
{"type":"status","status":"waiting_for_user","message":"等待用户选择下一步","ts":"2026-06-05T17:40:10+08:00"}
```

### inbox/events.jsonl

`inbox/events.jsonl` 是 Web 到 CLI 的低风险上下文输入管道。

Web 提供上下文输入后写入：

```jsonl
{"type":"choice","choice_id":"next","value":"source_path","label":"看源码路径","session_id":"codex-main","ts":"2026-06-05T17:40:20+08:00"}
```

agent CLI 只有在显式运行 `localweb wait --id next` 后，Web 输入才进入 CLI 输出，进而进入模型上下文。

## 5. CLI 脚本设计

脚本是 skill 的稳定执行层，负责处理重复、易错、需要确定性的操作。

推荐命令：

```bash
uv run scripts/localweb.py init
uv run scripts/localweb.py serve --port 8765
uv run scripts/localweb.py serve --project /path/to/project --port 8765
uv run scripts/localweb.py panel --id main --file output.html
uv run scripts/localweb.py status --title "学习图解" --state waiting_for_user
uv run scripts/localweb.py choice --id next --option architecture="看架构" --option example="看示例"
uv run scripts/localweb.py wait --id next
```

命令职责：

| 命令 | 作用 |
|---|---|
| `init` | 初始化 `.localweb/` 目录、默认 state 和默认 shell 资源 |
| `serve` | 启动本地 Web 服务，默认监听 `127.0.0.1` |
| `panel` | 写入或注册一个 HTML panel |
| `status` | 更新 `state.json` 的状态、标题、上下文 |
| `choice` | 发布可选的建议型选择或上下文输入 |
| `wait` | 阻塞等待 Web 输入，返回输入值 |
| `emit` | 追加事件到 `events.jsonl` |
| `doctor` | 检查 Python、端口、目录权限和依赖 |

### init 设计

`init` 是项目级初始化命令。它应该只在当前项目下创建或更新 `.localweb/`，不修改 skill 安装目录。

建议行为：

```text
1. 解析项目根目录：
   - 优先使用 --project <path>
   - 否则使用当前 cwd

2. 创建目录：
   - .localweb/
   - .localweb/panels/
   - .localweb/inbox/
   - .localweb/assets/generated/
   - .localweb/shell/ 或 .localweb/.cache/shell/

3. 写入默认文件：
   - state.json
   - events.jsonl
   - inbox/events.jsonl
   - panels/main.html

4. 复制默认 shell 资源：
   - index.html
   - app.js
   - theme.css

5. 不覆盖用户已有 panel：
   - 已存在文件默认保留
   - 需要重置时使用 --force

6. 输出机器可读结果：
   - project_root
   - localweb_dir
   - next_command
```

示例输出：

```json
{
  "status": "ok",
  "project_root": "/home/user/project",
  "localweb_dir": "/home/user/project/.localweb",
  "next_command": "uv run scripts/localweb.py serve --project /home/user/project --port 8765"
}
```

### serve 设计

`serve` 也是项目级命令。它从项目的 `.localweb/` 读取协议文件，并把 `.localweb/panels` 中的 HTML 放入 shell 舞台。

建议行为：

```text
1. 如果 .localweb/ 不存在，提示先运行 init，或使用 --init 自动初始化。
2. 只服务当前项目的 .localweb/ 文件。
3. 默认监听 127.0.0.1，不允许默认 0.0.0.0。
4. 如果端口占用，自动尝试下一个端口，或返回清晰错误。
5. 输出本地 URL。
```

`wait` 的输出应该极简：

```text
source_path
```

这样 agent 可以直接把它当作低风险上下文信号继续推理。

## 6. 技术栈

### MVP 推荐

```text
语言：Python
包管理：uv
后端：FastAPI 或 Starlette
服务：uvicorn
文件监听：watchfiles 可选
前端：原生 HTML/CSS/JS
刷新：SSE 或短轮询
交互：HTTP POST 写入 inbox
```

选择理由：

- Python + uv 贴合当前 NixOS 工作环境。
- 原生前端足够支撑 shell，避免第一版引入复杂构建。
- iframe 加载 panel，shell 与 panel 天然隔离。
- 文件协议是事实来源，HTTP/SSE/WebSocket 只是传输方式。

### 后续可升级

```text
SSE -> WebSocket
原生 JS -> React / Svelte
单 panel -> 多 panel tab
inbox only -> tmux bridge / PTY broker
静态 HTML -> 可编辑 HTML artifact
```

升级顺序应该保护协议稳定，不让 UI 框架反向污染协议。

## 7. Web UI 设计

### 布局

只固定外框，不固定中间内容。

```text
┌─[ LOCALWEB // HTML STAGE ]────────────────────────────────────────────────┐
│ 状态: 等待输入      会话: codex-main      通道: 就绪      面板: main        │
├──────────────────────┬───────────────────────────────────────────────────┤
│ CONTEXT 上下文        │                                                   │
│                       │             HTML STAGE 舞台                       │
│  01 当前任务           │                                                   │
│     React Fiber       │      ┌────────────────────────────────────┐       │
│                       │      │                                    │       │
│  02 当前阶段           │      │     agent 生成的 HTML panel         │       │
│     概念解释           │      │                                    │       │
│                       │      │     图解 / 卡片 / 流程 / 表格        │       │
│  03 交互状态           │      │                                    │       │
│     可选上下文输入       │      └────────────────────────────────────┘       │
│                       │                                                   │
│  04 主会话             │      [ 看整体流程 ] [ 看源码路径 ] [ 做练习 ]       │
│     CLI terminal      │      或隐藏交互区，仅展示 panel                    │
└──────────────────────┴───────────────────────────────────────────────────┘
```

布局区域：

- 顶部状态条：显示 session、status、pipe 状态、active panel、更新时间。
- 左侧上下文栈：显示任务、阶段、来源、等待状态、最近事件。
- 中间 HTML 舞台：iframe 加载 `active_panel`。
- 可选交互区：仅在 agent 需要用户上下文信号时渲染 `choices`，点击后写入 inbox；纯展示时应隐藏或弱化。

### 外层卡通终端风格

视觉方向：

```text
主题：黄黑卡通终端大屏
主色：#ffd43b
背景：#17140b / #231e10
描边：#080808，2px-4px 硬线
辅助色：#ff8f1f 橙、#24d7ff 青、#f7f1d0 奶白
圆角：4px-6px，小圆角
字体：标题粗黑体，正文 monospace
动效：状态灯、轻微扫描线、按钮按压反馈
```

设计纪律：

- 外层 shell 有统一视觉，但中间 panel 不被强制套死。
- panel 可以是学习图、代码图、对比表、流程图、报告、编辑器或局部交互画布。
- shell 不解释 panel 内容，只负责承载、刷新和收集显式低风险上下文输入。
- 不使用大面积柔和渐变，不做软糯卡片堆叠。
- 线条硬，颜色高对比，但信息密度保持清晰。

## 8. HTML Panel 输出规范

agent 生成 panel 时，优先输出 self-contained HTML。

建议约束：

```text
- 单文件 HTML 优先。
- 内联 CSS 和 JS。
- 可以使用 SVG、Canvas、CSS animation。
- 不依赖外网资源，除非用户明确允许。
- 可见文本尽量使用 data-lw-text 标注稳定 key。
- 页面尺寸响应 iframe 容器。
- 不写入危险脚本，不访问本地敏感路径。
```

示例：

```html
<h1 data-lw-text="headline">React Fiber 的核心流程</h1>
<section data-lw-section="render-phase">
  ...
</section>
```

## 9. 上下文交互协议

Web 交互的目标不是替代 CLI 对话，而是让用户更容易提供 CLI 文本里难以表达的上下文。它只处理低风险输入：

- 方向建议卡片，例如“看源码路径”“展开风险点”
- 图上标注、截图框选、diff hunk 聚焦
- 图表筛选、时间范围 brushing、异常点点击
- 表单填写、滑块、排序、优先级标记
- 标记已理解、选择下一步学习路径

纯展示 panel 不需要任何 Web 到 CLI 输入。即使 panel 内部有 tab、hover、局部筛选等交互，只要不需要 agent 继续推理，就不必写入 inbox。

不处理：

- 运行命令确认
- 文件删除确认
- 网络授权
- 大范围代码修改授权
- agent 权限审批

Web 到 CLI 的推荐路径：

```text
用户在 Web 提供上下文输入
  -> POST /api/inbox
  -> append .localweb/inbox/events.jsonl
  -> localweb wait --id next 返回 source_path
  -> CLI agent 看到 source_path
  -> 模型继续推理
```

这保证 Web 输入不会成为“隐形上下文”，也不会绕过 CLI 权限面。

## 10. Skill 文件结构

推荐 skill 名：

```text
html-companion
```

可选名称：

```text
localweb-companion
localweb-visual
html-deck
```

推荐结构：

```text
localweb/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   └── localweb.py
├── assets/
│   └── shell/
│       ├── index.html
│       ├── app.js
│       └── theme.css
├── references/
│   ├── protocol.md
│   ├── html-patterns.md
│   └── visual-style.md
└── design.md
```

`SKILL.md` 放核心流程：

- 何时启动 companion。
- 如何初始化和启动服务。
- 如何生成 HTML panel。
- 如何更新状态和选择项。
- 如何等待 Web 输入返回 CLI。
- CLI 是主上下文的约束。
- 安全边界。

`references/protocol.md` 放协议细节。

`references/html-patterns.md` 放不同任务类型的 panel 模式：

- 学习解释
- 代码理解
- 方案对比
- 代码审查
- 调试时间线
- 研究总结
- 自定义小编辑器

`references/visual-style.md` 放黄黑卡通终端风的视觉规范。

## 11. 典型工作流

### 学习解释

```text
用户在 CLI：用可视化方式解释 React Fiber
agent：
  1. 启动 localweb
  2. 生成 panels/main.html
  3. 更新 state.json
  4. 根据需要提供下一步方向卡；如果只是讲解，可省略
用户在 Web 点“看源码路径”
agent 运行 localweb wait --id next
CLI 返回 source_path
agent 继续讲源码路径
```

### 代码理解

```text
agent 读取仓库结构
生成模块图 HTML
左侧 context 显示当前分析目标
中间显示模块依赖图
Web 可选输入：点击入口节点 / 标记热路径 / 选择测试面 / 聚焦风险
```

### 方案对比

```text
中间 panel 显示三种方案并排
顶部状态显示推荐方案和不确定项
Web 点击“展开迁移成本最低的方案”
CLI 接收到方案 ID 后生成更细计划
```

## 12. MVP 范围

第一版只做六件事：

```text
1. init：创建 .localweb
2. serve：启动本地服务
3. panel：注册/写入 HTML panel
4. status：更新状态和上下文
5. choice：写入可选上下文输入
6. wait：等待 Web 输入并返回 CLI
```

验收条件：

- 能在本地打开 Web shell。
- 能显示左侧上下文和中间 HTML panel。
- 修改 `state.json` 后页面能刷新。
- 纯展示 panel 不需要发布选择项。
- Web 可选上下文输入能写入 inbox。
- `localweb wait` 能返回对应输入值。
- 服务默认只监听 `127.0.0.1`。

## 13. 后续路线

### Phase 1：协议闭环

- 文件协议
- 本地服务
- 默认 shell
- 可选上下文输入返回 CLI

### Phase 2：可视化模板

- 学习解释模板
- 代码理解模板
- 方案对比模板
- 调试时间线模板
- 代码审查模板

### Phase 3：增强交互

- 表单输入
- 多 panel tab
- session replay
- panel 历史
- export HTML bundle

### Phase 4：桥接能力

- tmux bridge
- PTY broker
- WebSocket 实时双向管道
- 可选 Web 输入转 CLI

## 14. 参考项目启发

`html-video` 的可借鉴点：

- agent 通过 CLI 操作工具，不直接 import 内部库。
- HTML 是 agent 输出的核心介质。
- 结构化 fenced block 可以渲染成 Web 交互组件。
- content-graph 可以表达线性文本无法表达的节点和关系。
- 本地 studio 默认监听 `127.0.0.1`。

需要避免直接照搬的点：

- 不让 Web studio 接管 agent 会话。
- 不在 Web 端重新构造主 prompt 和主 history。
- 不把视频生成、渲染、导出 MP4 这些重逻辑带入 MVP。
- 不让 agent runtime 变成当前项目的核心依赖。

## 15. 风险与边界

### 风险

- agent 生成的 HTML 质量不稳定。
- iframe 中 HTML 可能脚本过重或布局溢出。
- Web 输入如果没有显式 wait，用户可能以为已经进入 CLI 上下文。
- 文件协议若过早复杂化，会拖慢 MVP。

### 缓解

- 保持 panel self-contained。
- shell 只加载 `.localweb/panels` 下的文件。
- 顶部明确显示通道状态：`就绪 / 等待输入 / 已发送`。
- `wait` 返回后在 `events.jsonl` 记录 consumed 状态。
- 第一版只支持低风险上下文输入事件，不支持任意命令执行。

## 16. 一句话总结

HTML Companion 的本质不是 Web 终端，而是：

```text
一个让 CLI agent 持续生成、展示、更新 HTML 可视化结果的本地伴生协议和默认卡通终端外壳。
```
