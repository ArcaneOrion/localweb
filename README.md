# LocalWeb

> CLI agent 的本地 Web 可视化与上下文交互层

本地 HTML 伴生界面，为 CLI agent 提供可视化投影层。CLI 保持主控制面、权限面和会话上下文，Web 提供高带宽可视化输出和可选的上下文交互。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 特性

- 🎨 **富文本 HTML 面板** - 代码解释、图表、学习材料
- 🔄 **上下文交互** - 可选方向建议、标注、筛选、排序或小表单返回 CLI
- 📁 **文件协议解耦** - 独立、可审计、项目级
- 🔒 **默认安全** - localhost 绑定、无自动执行
- 🧹 **自动维护** - choice ID 重用安全、inbox 可清理

## 🚀 快速开始

```bash
# 初始化项目
uv run scripts/localweb.py init

# 启动服务
uv run scripts/localweb.py serve --port 8765

# 在浏览器打开 http://127.0.0.1:8765
```

## 📖 使用场景

- **教学复杂概念** - 可视化图解 + 可选学习路径
- **代码审查** - 带注解的 diff + 点击关注风险点
- **交互式调试** - 可视化状态 + 标记卡住步骤
- **多步骤规划** - 可视化上下文 + 进度追踪
- **需求澄清** - 用卡片、滑块或表单收集难以在 CLI 中表达的约束

## 📋 核心命令

| 命令 | 用途 |
|------|------|
| `init` | 初始化 .localweb 目录结构；`--shell-only` 只刷新浏览器 shell |
| `serve` | 启动 HTTP 服务器 |
| `panel` | 注册 HTML panel |
| `learn` | 从结构化 lesson JSON 生成学习面板 |
| `status` | 更新状态和上下文 |
| `choice` | 发布可选的建议型选择或上下文输入 |
| `wait` | 显式等待 Web 输入返回 CLI，可启用 CLI 文字兜底 |
| `clean` | 清理已消费和已作废事件 |
| `doctor` | 环境检查 |
| `emit` | 追加自定义事件 |

## 📂 项目结构

```
localweb/
├── SKILL.md            # Skill 主文档
├── scripts/
│   └── localweb.py     # CLI 工具
├── assets/
│   └── shell/          # Web UI 模板
├── references/         # 协议和模式文档
├── agents/             # Agent 配置
├── design.md           # 设计文档
└── README.md
```

## 🔧 工作流程示例

```bash
# 1. 生成可视化 panel
uv run scripts/localweb.py panel --id main --file explanation.html

# 或生成学习模式 panel；有 questions 时默认等待浏览器回答
uv run scripts/localweb.py learn --file learn/examples/epsilon-delta.json --id epsilon-delta
uv run scripts/localweb.py wait --id learn-epsilon-delta --type panel

# 2. 更新状态和上下文
uv run scripts/localweb.py status \
  --state learning \
  --context "任务=理解 React Fiber" \
  --context "阶段=核心概念"

# 3. 需要用户方向时，提供可选上下文输入；纯展示时可省略
uv run scripts/localweb.py choice --id next \
  --option overview="看整体流程" \
  --option source_path="看源码路径" \
  --option exercise="做练习"

# 4. 发布可回传输入后必须立刻 wait，保持 CLI 回合打开
uv run scripts/localweb.py wait --id next
# 输出: source_path

# panel 内嵌交互显式发送 Markdown 时，发布 panel 时声明 wait id
uv run scripts/localweb.py panel --id review --file review.html --wait-id review-context --wait-type panel
uv run scripts/localweb.py wait --id review-context --type panel
# 输出: ## 用户补充 ...

# 如果用户不想点选，也允许在交互式 CLI 中直接输入文字
uv run scripts/localweb.py wait --id next --cli-fallback
```

## 💡 核心理念

- **CLI 为主上下文** - 终端是唯一的会话和权限控制面
- **Web 为投影层** - 浏览器做可视化和低风险上下文输入，不处理权限
- **文件协议解耦** - CLI/Server/Browser 通过文件通信
- **显式控制流** - 发布可回传 Web 输入后，命令输出 `next_command` 指向对应 `wait`

## 📚 文档

- **[SKILL.md](SKILL.md)** - 完整使用指南
- **[design.md](design.md)** - 设计文档和架构
- **[references/protocol.md](references/protocol.md)** - 文件协议规范
- **[references/html-patterns.md](references/html-patterns.md)** - Panel 模式
- **[references/visual-style.md](references/visual-style.md)** - 视觉风格指南

## 🛠️ 依赖

- Python 3.10+
- FastAPI
- uvicorn

```bash
# 使用 uv (推荐)
uv run scripts/localweb.py serve

# 或手动安装依赖
pip install fastapi uvicorn
python scripts/localweb.py serve
```

## 📝 License

MIT

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
