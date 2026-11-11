"""单进程内存滑动窗口限流（P0 单 uvicorn worker 足够）。

同步码等价于账号凭证，``/session/adopt`` 是接管入口，必须限速。
进程重启会清空计数；若后续改成多 worker，应换 Redis / SQLite 实现。
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_LOCK = threading.Lock()


def allow(key: str, limit: int, window_seconds: float) -> bool:
    """在 window_seconds 内最多放行 limit 次。"""
    now = time.monotonic()
    with _LOCK:
        hits = _WINDOWS[key]
        while hits and now - hits[0] >= window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


def client_ip(request) -> str:
    """Caddy 反代下优先取 X-Forwarded-For 的首段。"""
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else ""
    return ip or (request.client.host if request.client else "unknown")


def reset() -> None:
    """测试用：清空全部计数。"""
    with _LOCK:
        _WINDOWS.clear()
