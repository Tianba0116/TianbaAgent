"""Terminal Channel — Immersive Claude Code-style Agent CLI.

Streaming output  ·  Slash commands  ·  Tool confirmation  ·  Rich display
"""

import sys
import os
import logging
import threading

from bridge.context import *
from bridge.reply import Reply, ReplyType
from channel.chat_channel import ChatChannel, check_prefix
from channel.chat_message import ChatMessage
from common.log import logger
from config import conf

# ═══════════════════════════════════════════════════════════════════════════════
# ANSI helpers
# ═══════════════════════════════════════════════════════════════════════════════

BOLD = "\033[1m"; DIM = "\033[2m"; ITALIC = "\033[3m"; UNDER = "\033[4m"
CYAN = "\033[36m"; GREEN = "\033[32m"; YELLOW = "\033[33m"
BLUE = "\033[34m"; MAGENTA = "\033[35m"; RED = "\033[31m"
WHITE = "\033[37m"; RESET = "\033[0m"
BG_RED = "\033[41m"; BG_GREEN = "\033[42m"; BG_YELLOW = "\033[43m"

def _c(code, text): return f"{code}{text}{RESET}"
def _osc(url, text=None):
    if text is None: text = url
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"

# Box-drawing
BOX_H  = "─"; BOX_V  = "│"; BOX_TL = "┌"; BOX_TR = "┐"
BOX_BL = "└"; BOX_BR = "┘"; BOX_ML = "├"; BOX_MR = "┤"

# ═══════════════════════════════════════════════════════════════════════════════
# Welcome
# ═══════════════════════════════════════════════════════════════════════════════

WELCOME = f"""
{CYAN}   ████████╗ ██╗  █████╗  ███╗  ██╗ ██████╗   █████╗{RESET}
{CYAN}   ╚══██╔══╝ ██║ ██╔══██╗ ████╗ ██║ ██╔══██╗ ██╔══██╗{RESET}
{CYAN}      ██║    ██║ ███████║ ██╔██╗██║ ██████╔╝ ███████║{RESET}
{CYAN}      ██║    ██║ ██╔══██║ ██║╚████║ ██╔══██╗ ██╔══██║{RESET}
{CYAN}      ██║    ██║ ██║  ██║ ██║ ╚███║ ██████╔╝ ██║  ██║{RESET}
{CYAN}      ╚═╝    ╚═╝ ╚═╝  ╚═╝ ╚═╝  ╚══╝ ╚═════╝  ╚═╝  ╚═╝{RESET}
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Destructive command patterns (for confirmation)
# ═══════════════════════════════════════════════════════════════════════════════

_DESTRUCTIVE_PATTERNS = [
    "rm ", "rmdir ", "del ", "deltree ",
    "mv ", "move ", "ren ", "rename ",
    "rm -rf", "rm -r", "rm -f",
    "format ", "fdisk ", "mkfs.",
    ">", ">>",
    "chmod ", "chown ",
    "pip uninstall", "npm uninstall", "apt remove", "apt purge",
    "DROP ", "DELETE ", "TRUNCATE ", "ALTER ",
    "shutdown", "reboot", "init 0", "init 6",
    "scp ", "rsync ", "nc ",
    ":(){ :|:& };:",  # fork bomb
]


def _is_destructive(command: str) -> bool:
    """Check if a shell command may modify/destroy data."""
    cmd = command.strip()
    for pat in _DESTRUCTIVE_PATTERNS:
        if pat in cmd:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Terminal Message
# ═══════════════════════════════════════════════════════════════════════════════

class TerminalMessage(ChatMessage):
    def __init__(self, msg_id, content, ctype=ContextType.TEXT,
                 from_user_id="User", to_user_id="Chatgpt", other_user_id="Chatgpt"):
        self.msg_id = msg_id
        self.ctype = ctype
        self.content = content
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.other_user_id = other_user_id


# ═══════════════════════════════════════════════════════════════════════════════
# Terminal Channel
# ═══════════════════════════════════════════════════════════════════════════════

class TerminalChannel(ChatChannel):
    NOT_SUPPORT_REPLYTYPE = [ReplyType.VOICE]

    def __init__(self):
        super().__init__()
        self._dual_mode = False
        self._msg_id = 0
        self._lock = threading.Lock()
        self._first_token = False
        self._in_thinking = False

    # ── Confirmation handler (called synchronously by agent) ────────────

    def _make_confirmation_handler(self):
        """Build a handler that asks for user confirmation on destructive ops."""
        def confirm(tool_name: str, args: dict) -> bool:
            if tool_name == "bash":
                command = str(args.get("command", ""))
                if _is_destructive(command):
                    print()
                    print(f"  {_c(BG_YELLOW + BOLD, ' ⚠ DESTRUCTIVE COMMAND ')}")
                    print(f"  {BOX_TL}{BOX_H * 60}{BOX_TR}")
                    for line in command.strip().split("\n")[:10]:
                        print(f"  {BOX_V} {_c(RED, line[:58])}")
                    print(f"  {BOX_BL}{BOX_H * 60}{BOX_BR}")
                    print(f"  {_c(YELLOW, 'This command may modify or delete files.')}")
                    sys.stdout.write(f"  {_c(BOLD, 'Proceed? [y/N]:')} ")
                    sys.stdout.flush()
                    try:
                        answer = input().strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        print(_c(DIM, " Cancelled."))
                        return False
                    if answer != "y":
                        print(f"  {_c(DIM, 'Cancelled.')}")
                        return False
                    print(f"  {_c(GREEN, 'Proceeding...')}")
                    return True

            elif tool_name in ("write", "edit"):
                file_path = str(args.get("file_path", args.get("path", "")))
                print()
                print(f"  {_c(BG_YELLOW + BOLD, ' ⚠ FILE MODIFICATION ')}")
                print(f"  {_c(DIM, f'Agent will {tool_name}: {file_path}')}")
                sys.stdout.write(f"  {_c(BOLD, 'Proceed? [Y/n]:')} ")
                sys.stdout.flush()
                try:
                    answer = input().strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print(_c(DIM, " Cancelled."))
                    return False
                if answer and answer != "y":
                    print(f"  {_c(DIM, 'Cancelled.')}")
                    return False
                return True

            return True  # Allow all other tools
        return confirm

    # ── Event callback (SSE-style streaming to terminal) ─────────────────

    def _make_event_callback(self):
        """Stream agent events to terminal in real-time."""
        def on_event(event):
            etype = event.get("type", "")
            data = event.get("data", {})

            with self._lock:
                if etype == "agent_start":
                    self._first_token = True
                    self._in_thinking = False
                    print(f"  {_c(DIM, BOX_H * 50)}")

                elif etype == "reasoning_update":
                    delta = data.get("delta", "")
                    if delta:
                        if not self._in_thinking:
                            print(f"\n  {_c(MAGENTA + BOLD, '🧠 Thinking')}")
                            self._in_thinking = True
                        sys.stdout.write(_c(DIM, delta))
                        sys.stdout.flush()

                elif etype == "message_update":
                    delta = data.get("delta", "")
                    if delta:
                        if self._in_thinking:
                            sys.stdout.write("\n")
                            sys.stdout.flush()
                            self._in_thinking = False
                        if self._first_token:
                            print(f"\n  {_c(GREEN + BOLD, '⏺')} ", end="")
                            self._first_token = False
                        sys.stdout.write(delta)
                        sys.stdout.flush()

                elif etype == "message_end":
                    if not self._first_token:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                    self._first_token = True
                    self._in_thinking = False

                elif etype == "tool_execution_start":
                    if self._in_thinking:
                        sys.stdout.write("\n")
                        self._in_thinking = False
                    name = data.get("tool_name", "?")
                    args = data.get("arguments", {})
                    brief = self._fmt_tool_args(name, args)
                    print(f"  {_c(YELLOW, '⚙')} {_c(BOLD, name)} {brief}")
                    sys.stdout.flush()
                    self._first_token = True

                elif etype == "tool_execution_end":
                    result = data.get("result", "")
                    if result:
                        summary = self._fmt_tool_result(result)
                        if summary:
                            print(f"  {_c(DIM, '  ' + summary)}")
                            sys.stdout.flush()

                elif etype == "tool_execution_skipped":
                    print(f"  {_c(RED, '✖')} {_c(DIM, 'Tool execution cancelled by user.')}")
                    sys.stdout.flush()

                elif etype == "agent_end":
                    print(f"  {_c(DIM, BOX_H * 50)}")
                    self._first_token = True
                    self._in_thinking = False

                elif etype == "turn_end":
                    self._first_token = True

                elif etype == "error":
                    err = data.get("error", "")
                    print(f"\n  {_c(RED, '✖ Error:')} {_c(DIM, str(err)[:300])}")
                    sys.stdout.flush()

        return on_event

    @staticmethod
    def _fmt_tool_args(name: str, args: dict) -> str:
        if not args: return ""
        if name in ("read", "write", "edit"):
            return _c(DIM, str(args.get("file_path", args.get("path", ""))))
        if name == "bash":
            cmd = str(args.get("command", ""))
            return _c(DIM, cmd[:80] + ("..." if len(cmd) > 80 else ""))
        if name in ("web_search", "web_fetch"):
            return _c(DIM, str(args.get("query", args.get("url", ""))[:80]))
        if name == "browser":
            return _c(DIM, str(args.get("url", args.get("action", ""))[:80]))
        if name == "memory":
            return _c(DIM, str(args.get("query", ""))[:80])
        if name == "scheduler":
            return _c(DIM, str(args.get("cron", args.get("task", "")))[:80])
        if name == "send":
            return _c(DIM, str(args.get("message", ""))[:80])
        return ""

    @staticmethod
    def _fmt_tool_result(result) -> str:
        if not result: return ""
        text = str(result) if not isinstance(result, dict) else result.get("output", str(result))
        text = text.strip()
        first_line = text.split("\n")[0][:120]
        if len(text) > 120:
            first_line += "..."
        return first_line

    # ── send ─────────────────────────────────────────────────────────────

    def send(self, reply: Reply, context: Context):
        if reply.type == ReplyType.TEXT:
            pass  # Streaming already printed by on_event
        elif reply.type == ReplyType.IMAGE:
            from PIL import Image
            try:
                image_storage = reply.content
                image_storage.seek(0)
                img = Image.open(image_storage)
                print(f"\n  {_c(DIM, '[image displayed]')}")
                img.show()
            except Exception:
                print(f"\n  {_c(DIM, '[image]')}")
        elif reply.type == ReplyType.IMAGE_URL:
            print(f"\n  {_c(DIM, '[image]')} {reply.content}")
        elif reply.type == ReplyType.ERROR:
            print(f"\n  {_c(RED, '✖')} {reply.content}")
        elif reply.type == ReplyType.INFO:
            print(f"\n  {_c(DIM, reply.content)}")
        else:
            print(f"\n  {reply.content}")
        sys.stdout.flush()

    # ── startup ──────────────────────────────────────────────────────────

    def startup(self):
        import sys as _sys
        self._dual_mode = "--dual" in _sys.argv

        self._silence_console_logging()

        if not _sys.stdin.isatty():
            logger.warning("[TerminalChannel] stdin is not a TTY, disabled.")
            return

        self._print_welcome()
        self._msg_id = 0

        while True:
            try:
                prompt = self._read_input()
            except KeyboardInterrupt:
                print(f"\n\n  {_c(DIM, 'Goodbye.')}")
                sys.exit(0)
            except EOFError:
                return

            if prompt is None:
                continue

            # ── Slash commands ──────────────────────────────────────────
            if prompt.startswith("/"):
                self._dispatch_slash(prompt)
                continue

            # ── Local commands ──────────────────────────────────────────
            if prompt.lower() in ("help",):
                self._print_help()
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print(f"  {_c(DIM, 'Use /exit or Ctrl+C to quit.')}")
                continue

            # ── Send to agent ───────────────────────────────────────────
            self._msg_id += 1
            trigger_prefixs = conf().get("single_chat_prefix", [""])
            if check_prefix(prompt, trigger_prefixs) is None:
                prompt = trigger_prefixs[0] + prompt

            context = self._compose_context(
                ContextType.TEXT, prompt,
                msg=TerminalMessage(self._msg_id, prompt)
            )
            context["isgroup"] = False
            context["on_event"] = self._make_event_callback()
            context["confirmation_handler"] = self._make_confirmation_handler()

            if context:
                self.produce(context)
            else:
                raise Exception("context is None")

    # ══════════════════════════════════════════════════════════════════════
    # Slash command dispatcher
    # ══════════════════════════════════════════════════════════════════════

    def _dispatch_slash(self, text: str):
        cmd_line = text[1:].strip()
        if not cmd_line: return
        parts = cmd_line.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handlers = {
            "help":    lambda: self._print_help(),
            "status":  self._cmd_status,
            "model":   lambda: self._cmd_model(args),
            "tools":   lambda: self._cmd_tools(args),
            "memory":  lambda: self._cmd_memory(args),
            "skills":  lambda: self._cmd_skills(args),
            "context": lambda: self._cmd_context(args),
            "clear":   self._cmd_clear,
            "compact": self._cmd_compact,
            "exit":    lambda: self._do_exit(),
        }

        if cmd in handlers:
            handlers[cmd]()
        else:
            # Unknown slash command — pass to agent
            self._forward_to_agent(text)

    # ── /status ──────────────────────────────────────────────────────────

    def _cmd_status(self):
        from cli import __version__
        web_port = conf().get("web_port", 9899)
        model = conf().get("model", "?")
        bot = conf().get("bot_type", "auto")
        mode = "Agent" if conf().get("agent") else "Chat"
        ws = conf().get("agent_workspace", "~/tianba")
        thinking = "ON" if conf().get("enable_thinking") else "OFF"

        print(f"""
  {_c(BOLD, 'TianbaAgent Status')}
  {BOX_TL}{BOX_H * 40}{BOX_TR}
  {BOX_V}  Version:   {__version__:<30} {BOX_V}
  {BOX_V}  Model:     {model:<30} {BOX_V}
  {BOX_V}  Bot:       {bot:<30} {BOX_V}
  {BOX_V}  Mode:      {mode:<30} {BOX_V}
  {BOX_V}  Thinking:  {thinking:<30} {BOX_V}
  {BOX_V}  Workspace: {ws:<30} {BOX_V}
  {BOX_V}  Web:       {f'http://localhost:{web_port}':<30} {BOX_V}
  {BOX_BL}{BOX_H * 40}{BOX_BR}
""")

    # ── /model ───────────────────────────────────────────────────────────

    def _cmd_model(self, args: str):
        from common import const as c
        if not args or args == "list":
            print(f"\n  {_c(BOLD, 'Available Models')}")
            print(f"  {BOX_TL}{BOX_H * 40}{BOX_TR}")
            models = [
                ("deepseek-v4-pro", "DeepSeek V4 Pro"),
                ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
                ("claude-opus-4-7", "Claude Opus 4.7"),
                ("gpt-4o", "GPT-4o"),
                ("gpt-4.1-mini", "GPT-4.1 Mini"),
                ("gemini-3.1-pro", "Gemini 3.1 Pro"),
                ("qwen3.6-plus", "Qwen 3.6 Plus"),
                ("glm-5.1", "GLM 5.1"),
                ("kimi-k2.6", "Kimi K2.6"),
                ("MiniMax-M2.7", "MiniMax M2.7"),
            ]
            current = conf().get("model", "")
            for model_id, label in models:
                mark = " *" if model_id == current else "  "
                print(f"  {BOX_V} {_c(BOLD if model_id == current else '', label):<38} {BOX_V}")
            print(f"  {BOX_BL}{BOX_H * 40}{BOX_BR}")
            print(f"  Current: {_c(GREEN, current)}")
            print(f"  Switch via Web Console or edit config.json")
            print()
        elif args.startswith("switch "):
            new_model = args[7:].strip()
            print(f"  {_c(YELLOW, 'Model switching via CLI is not yet supported.')}")
            print(f"  {_c(DIM, 'Use the Web Console to switch models, or edit config.json.')}")
        else:
            print(f"  Model: {_c(GREEN, conf().get('model', '?'))}")
            print(f"  Bot:   {_c(DIM, conf().get('bot_type', 'auto'))}")

    # ── /tools ───────────────────────────────────────────────────────────

    def _cmd_tools(self, args: str):
        try:
            from agent.tools import ToolManager
            tm = ToolManager()
            tm.load_tools()
            if args:
                name = args.strip()
                cls = tm.tool_classes.get(name)
                if cls:
                    doc = (cls.__doc__ or "").strip().split("\n")[0]
                    print(f"\n  {_c(BOLD, name)}")
                    print(f"  {_c(DIM, doc)}")
                else:
                    print(f"  {_c(RED, f'Tool not found: {name}')}")
            else:
                print(f"\n  {_c(BOLD, 'Available Tools')}  ({len(tm.tool_classes)} total)")
                print(f"  {BOX_TL}{BOX_H * 50}{BOX_TR}")
                for name in sorted(tm.tool_classes.keys()):
                    cls = tm.tool_classes[name]
                    doc = (cls.__doc__ or "").strip().split("\n")[0][:45]
                    print(f"  {BOX_V} {_c(CYAN, name):<18} {_c(DIM, doc):<30} {BOX_V}")
                print(f"  {BOX_BL}{BOX_H * 50}{BOX_BR}")
                print()
        except Exception as e:
            print(f"  {_c(RED, f'Error: {e}')}")

    # ── /memory ──────────────────────────────────────────────────────────

    def _cmd_memory(self, args: str):
        try:
            from agent.memory import get_default_memory_config, MemoryConfig
            ws = get_default_memory_config().workspace_root
            mem_dir = os.path.join(ws, "memory")
            if os.path.isdir(mem_dir):
                files = sorted(
                    [f for f in os.listdir(mem_dir) if f.endswith(".md")],
                    reverse=True
                )
                print(f"\n  {_c(BOLD, 'Memory Files')}  ({len(files)} entries)")
                for f in files[:10]:
                    print(f"  {_c(DIM, '  ' + f)}")
                if len(files) > 10:
                    print(f"  {_c(DIM, f'  ... and {len(files) - 10} more')}")
                print()
            else:
                print(f"  {_c(DIM, 'No memory directory found.')}")
        except Exception as e:
            print(f"  {_c(RED, f'Error: {e}')}")

    # ── /skills ──────────────────────────────────────────────────────────

    def _cmd_skills(self, args: str):
        import os as _os
        from common.utils import expand_path
        ws = expand_path(conf().get("agent_workspace", "~/tianba"))
        sd = _os.path.join(ws, "skills")
        if _os.path.isdir(sd):
            names = [
                d for d in _os.listdir(sd)
                if _os.path.isdir(_os.path.join(sd, d))
                and _os.path.isfile(_os.path.join(sd, d, "SKILL.md"))
            ]
            cfg_file = _os.path.join(sd, "skills_config.json")
            disabled = set()
            if _os.path.isfile(cfg_file):
                import json
                try:
                    with open(cfg_file) as f:
                        sc = json.load(f)
                    disabled = {k for k, v in sc.items() if not v}
                except Exception:
                    pass

            print(f"\n  {_c(BOLD, 'Installed Skills')}  ({len(names)} total)")
            for n in sorted(names):
                status = _c(DIM, "OFF") if n in disabled else _c(GREEN, "ON")
                print(f"  {status}  {_c(CYAN, n)}")
            print()
        else:
            print(f"  {_c(DIM, 'No skills directory.')}")

    # ── /context ─────────────────────────────────────────────────────────

    def _cmd_context(self, args: str):
        try:
            from bridge.bridge import Bridge
            ab = Bridge().get_agent_bridge()
            agent = getattr(ab, 'default_agent', None)
            if agent:
                with agent.messages_lock:
                    msgs = list(agent.messages)
                user_msgs = [m for m in msgs if m.get("role") == "user"]
                tool_msgs = [m for m in msgs if m.get("role") == "tool"]
                assistant_msgs = [m for m in msgs if m.get("role") == "assistant"]

                total_tokens = sum(len(str(m.get("content", ""))) for m in msgs) // 4

                print(f"\n  {_c(BOLD, 'Context')}")
                print(f"  {BOX_TL}{BOX_H * 35}{BOX_TR}")
                print(f"  {BOX_V} Messages:  {len(msgs):<4} (user: {len(user_msgs)}, asst: {len(assistant_msgs)}, tool: {len(tool_msgs)}) {BOX_V}")
                print(f"  {BOX_V} Est.tokens: ~{total_tokens:<6}                              {BOX_V}")
                print(f"  {BOX_V} Max turns: {conf().get('agent_max_context_turns', 20):<4}                               {BOX_V}")
                print(f"  {BOX_BL}{BOX_H * 35}{BOX_BR}")
                if args == "view":
                    print(f"\n  {_c(DIM, 'Last 5 messages:')}")
                    for m in msgs[-5:]:
                        role = m.get("role", "?")[:8]
                        content = str(m.get("content", ""))[:100]
                        print(f"  {_c(BOLD, role):>8} {_c(DIM, content)}")
                print()
            else:
                print(f"  {_c(DIM, 'No active agent session. Start chatting first.')}")
        except Exception as e:
            print(f"  {_c(RED, f'Error: {e}')}")

    # ── /clear ───────────────────────────────────────────────────────────

    def _cmd_clear(self):
        try:
            from bridge.bridge import Bridge
            ab = Bridge().get_agent_bridge()
            agent = getattr(ab, 'default_agent', None)
            if agent:
                with agent.messages_lock:
                    agent.messages.clear()
                print(f"  {_c(GREEN, '✓')} Conversation context cleared.")
            else:
                print(f"  {_c(DIM, 'No active session to clear.')}")
        except Exception as e:
            print(f"  {_c(RED, f'Error: {e}')}")

    # ── /compact ─────────────────────────────────────────────────────────

    def _cmd_compact(self):
        try:
            from bridge.bridge import Bridge
            ab = Bridge().get_agent_bridge()
            agent = getattr(ab, 'default_agent', None)
            if not agent:
                print(f"  {_c(DIM, 'No active session.')}")
                return
            with agent.messages_lock:
                msgs = list(agent.messages)
            if len(msgs) < 6:
                print(f"  {_c(DIM, 'Context is already small.')}")
                return
            # Keep system + last 3 exchanges
            system_msgs = [m for m in msgs if m.get("role") == "system"]
            non_system = [m for m in msgs if m.get("role") != "system"]
            kept = system_msgs + non_system[-6:]
            with agent.messages_lock:
                agent.messages = kept
            print(f"  {_c(GREEN, '✓')} Context compacted: {len(msgs)} → {len(kept)} messages.")
        except Exception as e:
            print(f"  {_c(RED, f'Error: {e}')}")

    # ── /exit ────────────────────────────────────────────────────────────

    def _do_exit(self):
        print(f"\n  {_c(DIM, 'Goodbye.')}")
        sys.exit(0)

    # ── Forward to agent (unknown slash command) ─────────────────────────

    def _forward_to_agent(self, text: str):
        self._msg_id += 1
        context = self._compose_context(
            ContextType.TEXT, text,
            msg=TerminalMessage(self._msg_id, text)
        )
        context["isgroup"] = False
        context["on_event"] = self._make_event_callback()
        context["confirmation_handler"] = self._make_confirmation_handler()
        if context:
            self.produce(context)

    # ══════════════════════════════════════════════════════════════════════
    # UI helpers
    # ══════════════════════════════════════════════════════════════════════

    def _silence_console_logging(self):
        for h in list(logger.handlers):
            if isinstance(h, logging.StreamHandler):
                h.setLevel(logging.CRITICAL)
        for h in list(logging.getLogger().handlers):
            if isinstance(h, logging.StreamHandler):
                h.setLevel(logging.CRITICAL)

    def _print_welcome(self):
        print(WELCOME)
        print(f"  {_c(BOLD + CYAN, 'TianbaAgent')} {_c(DIM, 'v2.0.7')}  {_c(DIM, '— Super AI Agent')}")
        print()
        if self._dual_mode:
            web_port = conf().get("web_port", 9899)
            print(f"  {_c(DIM, 'Web Console:')}  {_osc(f'http://localhost:{web_port}')}")
        print(f"  {_c(DIM, '/help for commands  ·  Ctrl+C to exit  ·  just chat to begin')}")
        print()

    HELP = f"""
  {BOLD}Slash Commands{RESET}
  {BOX_TL}{BOX_H * 55}{BOX_TR}
  {BOX_V} {_c(CYAN, '/help')}      Show this help                {BOX_V}
  {BOX_V} {_c(CYAN, '/status')}    Agent status & config          {BOX_V}
  {BOX_V} {_c(CYAN, '/model')}     Show or list models            {BOX_V}
  {BOX_V} {_c(CYAN, '/tools')}     List available tools           {BOX_V}
  {BOX_V} {_c(CYAN, '/memory')}    Recent memory entries          {BOX_V}
  {BOX_V} {_c(CYAN, '/skills')}    Installed skills               {BOX_V}
  {BOX_V} {_c(CYAN, '/context')}   View context stats & history   {BOX_V}
  {BOX_V} {_c(CYAN, '/clear')}     Clear conversation context     {BOX_V}
  {BOX_V} {_c(CYAN, '/compact')}   Compress context (keep recent) {BOX_V}
  {BOX_V} {_c(CYAN, '/exit')}      Quit (or Ctrl+C)               {BOX_V}
  {BOX_BL}{BOX_H * 55}{BOX_BR}

  {BOLD}Display{RESET}
  {DIM}⏺{RESET} Agent response   {DIM}⚙{RESET} Tool call   {DIM}🧠{RESET} Thinking   {DIM}✖{RESET} Error

  {BOLD}Confirmation{RESET}
  Destructive commands ({DIM}rm, mv, del, pip uninstall, etc.{RESET}) and
  file writes require explicit {DIM}y{RESET}/N confirmation before execution.
"""

    def _print_help(self):
        print(self.HELP)

    def _paint_prompt(self):
        return f"\n{_c(GREEN + BOLD, '▸')} "

    def _read_input(self):
        sys.stdout.write(self._paint_prompt())
        sys.stdout.flush()
        try:
            return input()
        except KeyboardInterrupt:
            raise

    def get_input(self):
        sys.stdout.flush()
        return input()
