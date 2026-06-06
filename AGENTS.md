# Repository Guidelines

## 项目结构与模块组织

LocalWeb 是面向 CLI agent 的项目级 HTML 伴生界面。核心使用说明在 `SKILL.md`，项目概览在 `README.md`，架构和设计取舍在 `design.md`。CLI 入口是 `scripts/localweb.py`。浏览器壳资源位于 `assets/shell/`，包括 `index.html`、`app.js` 和 `theme.css`。协议、HTML panel 模式和视觉规范在 `references/`。Agent 配置示例放在 `agents/`。运行时产物生成到 `.localweb/`，不要提交。

## 构建、测试与开发命令

本仓库使用 `uv` 管理 Python 执行和依赖。

- `uv run scripts/localweb.py init`：初始化 `.localweb/` 运行时目录。
- `uv run scripts/localweb.py serve --port 8765`：在 `127.0.0.1` 启动本地 FastAPI/uvicorn 服务。
- `uv run scripts/localweb.py doctor`：检查 Python、依赖、shell 资源、写权限和初始化状态。
- `uv run python -m py_compile scripts/localweb.py`：执行快速语法检查。
- `uv run scripts/localweb.py clean`：清理已消费或已作废的 inbox 事件。

## 编码风格与命名约定

Python 使用 4 空格缩进。优先使用类型标注、`pathlib.Path` 和小型命令函数，命名形如 `cmd_<command>`。写 JSON 时复用现有的 `write_json()`、`append_jsonl()` 等帮助函数，保持原子写入。会进入文件名的 CLI ID 应先经过 `safe_id()`。前端 shell 资源应保持轻依赖、自包含，避免引入构建链。

## 测试指南

当前还没有正式测试套件。改动前后至少运行 `uv run python -m py_compile scripts/localweb.py` 和 `uv run scripts/localweb.py doctor`。涉及行为变化时，在临时项目中跑烟测，例如 `uv run scripts/localweb.py init --project /tmp/localweb-smoke`，再按影响范围执行 `status`、`choice`、`wait` 或 `clean`。不要把生成的运行时文件留在 `.localweb/` 或 `/tmp` 之外。

## 提交与 PR 指南

近期提交采用简短中文祈使句，例如 `修复 choice 重复使用和 inbox 膨胀问题`、`更新文档：添加 clean 命令和 choice ID 重用说明`。每个提交聚焦一个可理解的变化，并说明用户可见影响。PR 应包含动机、涉及的命令或协议文件、已运行的验证命令、相关 issue；如果修改浏览器 shell UI，请附截图。

## 安全与配置提示

除非明确需要，否则本地服务只绑定 `127.0.0.1`。不要用浏览器 choice 承载危险权限、命令执行、文件删除或网络授权。修改 `.localweb/` 文件形状前先读 `references/protocol.md`；修改默认 shell UI 前先读 `references/visual-style.md`。
