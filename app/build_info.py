"""构建信息：让管理界面能回答「线上跑的是哪一版代码」。

优先级：
1. 部署时由 deploy/deploy.sh 写入的 BUILD_INFO.json（服务器上唯一可靠来源，
   因为部署包不含 .git）；
2. 本地 .git 的 HEAD（开发机直接跑 uvicorn 时）；
3. 都没有则 unknown，界面照常渲染，不报错。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BUILD_FILE = BASE_DIR / "BUILD_INFO.json"

APP_VERSION = "0.1.0"

_cache: dict | None = None


def _read_build_file() -> dict:
    try:
        data = json.loads(BUILD_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(BASE_DIR), *args],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def _compose() -> dict:
    data = _read_build_file()
    commit = (data.get("commit") or _git("rev-parse", "HEAD") or "")[:40]
    short = commit[:7] if commit else "unknown"
    branch = data.get("branch") or _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    commit_date = data.get("commit_date") or _git("log", "-1", "--format=%cI")
    built_at = data.get("built_at") or ""
    dirty = bool(data.get("dirty"))
    label = f"v{APP_VERSION}+{short}" + ("-dirty" if dirty else "")
    return {
        "version": APP_VERSION,
        "label": label,
        "commit": commit or "unknown",
        "short": short,
        "branch": branch,
        "commit_date": commit_date,
        "built_at": built_at,
        "dirty": dirty,
        "source": "deploy" if data else ("git" if commit else "unknown"),
    }


def snapshot() -> dict:
    """当前进程启动时所在代码的构建信息（进程内缓存，部署重启后自动刷新）。"""
    global _cache
    if _cache is None:
        _cache = _compose()
    return dict(_cache)
