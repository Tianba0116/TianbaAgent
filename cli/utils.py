"""Shared utilities for tianba CLI."""

import os
import sys
import json


def get_project_root() -> str:
    """Get the TianbaAgent project root directory."""
    # cli/ is directly under the project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_dual_foreground():
    """Launch TianbaAgent in dual mode (Web + CLI) directly in this process.

    This is the default when running ``tianba`` without arguments.
    The app runs as a foreground process — closing the terminal (Ctrl+C)
    stops everything cleanly.

    No subprocess. No daemon. One process, one lifecycle.
    """
    root = get_project_root()
    if root not in sys.path:
        sys.path.insert(0, root)

    # Signal app.py to start both Web and Terminal channels
    sys.argv.append("--dual")

    from app import run
    run()


def get_workspace_dir() -> str:
    """Get the agent workspace directory from config, defaulting to ~/tianba."""
    config = load_config_json()
    workspace = config.get("agent_workspace", "~/tianba")
    return os.path.expanduser(workspace)


def get_skills_dir() -> str:
    """Get the custom skills directory."""
    return os.path.join(get_workspace_dir(), "skills")


def get_builtin_skills_dir() -> str:
    """Get the builtin skills directory."""
    return os.path.join(get_project_root(), "skills")


def load_config_json() -> dict:
    """Load config.json from project root."""
    config_path = os.path.join(get_project_root(), "config.json")
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_skills_config() -> dict:
    """Load skills_config.json from the custom skills directory."""
    path = os.path.join(get_skills_dir(), "skills_config.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def ensure_sys_path():
    """Add project root to sys.path so we can import agent modules."""
    root = get_project_root()
    if root not in sys.path:
        sys.path.insert(0, root)


SKILL_HUB_API = "https://skills.tianbaagent.ai/api"
