
<p align="center">
  <img src="channel/web/static/logo.jpg" alt="TianbaAgent" width="120" />
  <h1 align="center">TianbaAgent</h1>
  <p align="center">面向科研场景的 LLM 智能助手 — 自主任务规划 · 多模型调度 · 长期记忆 · 知识沉淀</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.7--3.12-blue" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Models-13+-orange" alt="Models">
  <img src="https://img.shields.io/badge/Channels-9+-purple" alt="Channels">
</p>

---

## 快速开始

一行命令完成安装和配置，之后输入 `tianba` 即可使用：

**Linux / macOS：**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Tianba0116/TianbaAgent/main/run.sh)
```

**Windows（PowerShell）：**

```powershell
git clone https://github.com/Tianba0116/TianbaAgent.git
cd TianbaAgent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
tianba
```

**Docker：**

```bash
docker compose -f docker/docker-compose.yml up -d
```

安装脚本会自动完成 Python 环境检测、依赖安装、模型选择和配置生成。启动后在浏览器访问 `http://localhost:9899/chat` 或直接在终端对话。

---

## 项目流程

```
用户输入 "帮我调研多模态学习近三年进展并整理综述"
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  Channel 层 — 消息接入                                    │
│                                                           │
│  Web / 微信 / 飞书 / 钉钉 / QQ / 终端 — 统一 → Context    │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Bridge 层 — 中央路由                                     │
│                                                           │
│  消息总线单例，鉴权 → 路由 → 分发至 Agent                   │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Agent 层 — 推理决策                                      │
│                                                           │
│  ReAct 循环：                                             │
│  规划子任务 → 选择工具 → 执行 → 观察结果 → 修正 → 汇总     │
│                                                           │
│  多级上下文管理：溢出自动压缩 / 工具死循环检测 / 空响应兜底  │
└──────────────────────────┬───────────────────────────────┘
                           │
                ┌──────────┼──────────┐
                ▼          ▼          ▼
        ┌──────────┐ ┌────────┐ ┌──────────┐
        │  工具执行  │ │ LLM 调用│ │  技能系统 │
        │           │ │        │ │           │
        │ bash      │ │ Claude │ │ SKILL.md  │
        │ 文件读写   │ │ GPT    │ │ 热加载    │
        │ 网页搜索   │ │ Gemini │ │ 即插即用  │
        │ 浏览器    │ │ DeepSeek│ │           │
        │ 定时任务   │ │ ...    │ │           │
        └──────────┘ └────────┘ └──────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Extension 层 — 知识沉淀                                  │
│                                                           │
│  对话归档(Markdown) → SQLite 索引 → 向量语义检索            │
│  梦境蒸馏：定时从碎片对话提炼长期知识 → 知识图谱             │
└──────────────────────────────────────────────────────────┘
```

---

## 架构

```
Channel ──→ Bridge ──→ Agent ──→ Extension
  ↑            ↑          ↑           ↑
消息接入     消息路由    LLM 推理   能力扩展
```

| 层 | 目录 | 职责 | 扩展方式 |
|---|---|---|---|
| Channel | `channel/` | 对接 9+ IM 平台协议差异 | 继承 `ChatChannel` 基类 |
| Bridge | `bridge/` | 单例消息总线，统一路由分发 | 注册新 bot_type |
| Agent | `agent/protocol/` | ReAct 循环，上下文管理，流式输出 | LLMModel 适配器 |
| Extension | `agent/tools/` `agent/skills/` `agent/memory/` `agent/knowledge/` | 工具/技能/记忆/知识库 | 类注册 / SKILL.md / 插件系统 |

**设计原则：每一层只通过稳定接口与相邻层通信，新增平台或模型仅需扩展对应层，核心链路零改动。**

---

## 核心特性

- **ReAct 自主决策** — Agent 接收任务后拆解子目标，自主选择和调用工具，观察结果修正方向。单次请求支持 20+ 步连续操作
- **多模型协同调度** — 工厂+适配器模式统一封装 13+ 种 LLM（Claude / GPT / Gemini / DeepSeek / 通义千问 / 智谱 / 豆包 / Kimi 等），按任务复杂度自动匹配模型
- **三层递进记忆** — 对话按日归档（Markdown）→ SQLite + FTS5 全文索引 → 向量嵌入语义检索。配合梦境蒸馏自动从碎片对话提取长期知识
- **工具与技能热插拔** — 工具层类注册机制运行时动态加载，技能层基于 SKILL.md 规范声明式安装。新增能力无需重启服务，失败模块自动降级隔离
- **流式实时反馈** — SSE 推送 Agent 思考过程、工具调用状态、最终回复，支持断线重连和无缝降级轮询
- **知识图谱** — 自动解析文档间 Markdown 链接关系，构建可视化知识网络

---

## 日常使用

```bash
# 双端模式（Web + CLI，前台运行）
tianba

# 后台服务管理
tianba start          # 后台启动
tianba stop           # 停止
tianba restart        # 重启
tianba status         # 查看状态
tianba logs           # 查看日志

# 技能管理
tianba skill list              # 列出已安装技能
tianba skill install <name>    # 安装新技能

# 知识库管理
tianba knowledge list          # 浏览知识库
tianba knowledge <action>      # 管理知识库

# 安装浏览器工具（支持网页截图/自动化）
tianba install-browser
```

---

## 配置

首次运行安装脚本时会交互式完成配置，生成 `config.json`。也可以手动编辑：

```json
{
  "model": "deepseek-v4-pro",
  "deepseek_api_key": "sk-xxx",
  "deepseek_api_base": "https://api.deepseek.com/v1",
  "agent": true,
  "agent_workspace": "./.tianba",
  "channel_type": "web",
  "web_port": 9899
}
```

支持的模型配置字段：`open_ai_api_key` / `claude_api_key` / `gemini_api_key` / `deepseek_api_key` / `zhipu_ai_api_key` / `dashscope_api_key` / `moonshot_api_key` / `ark_api_key` / `minimax_api_key` / `linkai_api_key`

也可以在 Web 控制台 `http://localhost:9899/chat` → 配置页面在线修改，无需重启。

---

## 项目结构

```
TianbaAgent/
├── agent/                   # Agent 核心引擎
│   ├── protocol/            # ReAct 循环、流式执行、消息管理
│   ├── tools/               # 工具系统（bash/读写/搜索/浏览器/定时）
│   ├── skills/              # 技能系统（SKILL.md 加载/格式化）
│   ├── memory/              # 三层记忆管理
│   ├── knowledge/           # 知识库与图谱
│   └── prompt/              # System prompt 构建
├── models/                  # 13+ LLM 适配器（工厂模式）
├── channel/                 # 9+ IM 平台接入
│   ├── web/                 # Web 控制台
│   └── terminal/            # CLI 终端
├── bridge/                  # 消息总线与 Agent 桥接
├── plugins/                 # 插件系统（生命周期管理）
├── cli/                     # tianba CLI 命令
├── common/                  # 公共工具（单例/Token桶/日志）
├── skills/                  # 内置技能定义
├── docker/                  # Docker 部署
├── run.sh                   # 一键安装与管理脚本
├── requirements.txt         # Python 依赖
└── pyproject.toml           # 项目元数据与 CLI 入口
```

---

## License

MIT
