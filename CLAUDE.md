# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TianbaAgent is a super AI assistant powered by LLMs. It supports autonomous task planning, long-term memory, a knowledge base, a Skills system, tool use, and multi-platform messaging (WeChat, Feishu, DingTalk, QQ, Web Console, Terminal, etc.).

## Architecture (4-Layer Separation)

```
Channel Layer → Bridge Layer → Bot/Agent Layer → Extension Layer
```

| Layer | Directory | Responsibility |
|---|---|---|
| Channel | `channel/` | 9+ IM platform integrations, each extends `ChatChannel` |
| Bridge | `bridge/` | Central dispatch singleton (`Bridge`), agent bridge (`AgentBridge`) |
| Bot/Agent | `models/` + `agent/` | LLM provider adapters + core agent engine |
| Extension | `agent/tools/`, `agent/skills/`, `agent/memory/`, `agent/knowledge/` | Tools, skills, memory, knowledge |

### Key Directories

- **`agent/protocol/`** — Core agent logic: `Agent` class, `AgentStreamExecutor` (streaming), task management, message utils, result types
- **`agent/tools/`** — Tool system: `ToolManager`, `BaseTool`, and tool implementations (bash, read, write, edit, web_search, web_fetch, browser, scheduler, memory, vision, env_config, send)
- **`agent/memory/`** — Memory system: daily files (`memory/YYYY-MM-DD.md`), SQLite + vector embedding storage, dream distillation, context trimming, conversation store
- **`agent/skills/`** — Skill system: manager, loader (SKILL.md parsing), formatter, service
- **`agent/knowledge/`** — Structured knowledge base with graph capabilities
- **`agent/prompt/`** — System prompt builder, workspace initialization
- **`agent/chat/`** — Chat session services
- **`models/`** — LLM provider integrations (openai, claudeapi, gemini, deepseek, dashscope/qwen, minimax, zhipu/glm, baidu, xunfei, moonshot, doubao, modelscope, linkai)
- **`channel/`** — Platform channels (weixin, feishu, dingtalk, qq, web, terminal, wechatmp, wechatcom, wecom_bot)
- **`plugins/`** — Plugin system extending channel behavior (godcmd, role, banwords, dungeon, keyword, agent, tool, finish)
- **`bridge/`** — `Bridge` (central dispatch), `AgentBridge` (agent integration), `AgentInitializer` (agent setup), `AgentEventHandler` (streaming events)
- **`common/`** — Shared: constants (`const.py`), logging, utilities, singleton, token bucket, cloud client
- **`cli/`** — CLI commands using Click (`tianba start|stop|restart|skill|knowledge|...`)
- **`voice/`** — TTS/STT providers (openai, edge, baidu, azure, google, minimax, etc.)
- **`translate/`** — Translation providers (baidu)
- **`skills/`** — Built-in skill definitions (SKILL.md format)
- **`.tianba/`** — Agent identity (`AGENT.md`, `USER.md`, `RULE.md`), memory files, knowledge, skills cache

## Key Commands

### Startup & Management

```bash
bash run.sh              # Interactive management script (install, start, stop, restart, logs)
python app.py            # Start directly (requires config.json)
tianba                   # Start in dual mode (Web + CLI)
tianba start             # Start as background service
tianba stop              # Stop via CLI
tianba restart           # Restart via CLI
tianba status            # Check status
tianba logs              # View logs
```

### CLI (`tianba` command, installed via pip)

```bash
tianba                   # Dual mode: Web + CLI (default)
tianba start             # Start TianbaAgent
tianba stop              # Stop TianbaAgent
tianba restart           # Restart and update
tianba status            # Show running status
tianba logs              # View logs
tianba skill list        # List installed skills
tianba skill install <name> # Install a skill
tianba knowledge <action>   # Manage knowledge base
tianba install-browser   # Install Playwright + Chromium for browser tool
```

### Configuration

- Copy `config-template.json` to `config.json` and edit
- Key settings: `model`, `bot_type`, `open_ai_api_key`, `channel_type`, `agent_workspace`

### Development Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-optional.txt  # Optional deps for specific channels/models
pip install -e .            # Install `tianba` CLI command
```

## Key Design Patterns

- **Singleton**: `Bridge`, `ToolManager` — central dispatch and tool management
- **Factory pattern**: `channel_factory`, `bot_factory`, `voice/factory.py`, `translate/factory.py`
- **Plugin system**: `PluginManager` loads plugins from `plugins/plugins.json`, hooks into message lifecycle events
- **Agent memory**: File-based (Markdown) + SQLite + vector embeddings for retrieval
- **Skills**: SKILL.md files with YAML frontmatter, loaded from `skills/` (builtin) and `~/tianba/skills/` (custom)
- **Channel concurrency**: Each channel runs in a daemon thread; web console auto-starts as default UI
