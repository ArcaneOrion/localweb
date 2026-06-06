# LocalWeb Skill

本地 HTML 伴生界面 skill，为 CLI agent 提供可视化投影层。

## 项目结构

```
html-companion/          # skill 本体
├── SKILL.md            # skill 主文档
├── scripts/
│   └── localweb.py     # CLI 工具
├── assets/
│   └── shell/          # Web UI 模板
│       ├── index.html
│       ├── app.js
│       └── theme.css
├── references/         # 协议和模式文档
│   ├── protocol.md
│   ├── html-patterns.md
│   └── visual-style.md
└── agents/             # agent 配置

html-companion-design.md # 设计文档
```

## 快速开始

```bash
# 初始化项目
uv run html-companion/scripts/localweb.py init

# 启动服务
uv run html-companion/scripts/localweb.py serve --port 8765

# 健康检查
uv run html-companion/scripts/localweb.py doctor

# 清理已消费事件（可选，定期执行）
uv run html-companion/scripts/localweb.py clean
```

## 核心命令

| 命令 | 用途 |
|------|------|
| `init` | 初始化 .localweb 目录结构 |
| `serve` | 启动 HTTP 服务器 |
| `panel` | 注册 HTML panel |
| `status` | 更新状态和上下文 |
| `choice` | 创建选择项 |
| `wait` | 阻塞等待用户点击 |
| `clean` | 清理已消费事件 |
| `doctor` | 环境检查 |
| `emit` | 追加自定义事件 |

## 核心理念

- CLI 为主上下文和控制面
- Web 为高带宽可视化投影
- 文件协议解耦实现
- 轻量选择返回 CLI

详见 `html-companion-design.md` 和 `html-companion/SKILL.md`。
