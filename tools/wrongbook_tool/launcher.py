"""错题本一键启动器。

双击「错题本一键启动.exe」即可：
  1. 启动学习网站     → http://127.0.0.1:8011（已在跑则跳过）
  2. 启动错题录入工具 → http://127.0.0.1:8021
  3. 自动打开浏览器进入录入工具

构建（改完 launcher.py 后重新打包）：
  .venv/Scripts/pyinstaller --onefile --distpath . --workpath build --specpath build tools/wrongbook_tool/launcher.py
  产物在仓库根目录。前提：仓库里已建好 .venv（README 第一节）。
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

SITE_PORT = 8011
TOOL_PORT = 8021
SITE_URL = f"http://127.0.0.1:{SITE_PORT}"
TOOL_URL = f"http://127.0.0.1:{TOOL_PORT}"
REVIEW_VERSION = "gpt-import-review-1"


def repo_root() -> Path:
    """pyinstaller onefile 下 __file__ 在临时目录，用 exe 所在目录定位仓库根。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:
        return False


def review_version_ok(url: str, key: str = "review_version") -> bool:
    try:
        import json
        import urllib.request
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.load(response).get(key) == REVIEW_VERSION
    except Exception:
        return False


def spawn(args: list[str], cwd: Path) -> subprocess.Popen:
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    return subprocess.Popen(args, cwd=str(cwd),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=flags)


def main() -> None:
    if "--version" in sys.argv:
        print(REVIEW_VERSION)
        return
    # Windows GBK 控制台：输出改 UTF-8 且不容错崩溃
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = repo_root()
    venv_py = root / ".venv" / "Scripts" / "python.exe"
    py = str(venv_py) if venv_py.exists() else sys.executable

    print("=" * 52)
    print(f"  错题本一键启动 · GPT强审核版 {REVIEW_VERSION}")
    print("=" * 52)

    if not (root / "app" / "main.py").exists():
        print("[X] 请把 exe 放在 learning_highschool 仓库根目录后再运行。")
        input("按回车关闭...")
        return

    if not venv_py.exists():
        print("[X] 缺少项目 .venv/Scripts/python.exe，不能以启动器自身代替Python执行服务。")
        input("按回车关闭...")
        return
    for port, url, key in ((TOOL_PORT, f"{TOOL_URL}/api/state", "review_version"),
                           (SITE_PORT, f"{SITE_URL}/api/v1/healthz", "wrongbook_review_version")):
        if port_in_use(port) and not review_version_ok(url, key):
            print(f"[X] 端口 {port} 仍在运行旧版或未知服务。请关闭原启动器后重新运行，禁止复用未审核旧链路。")
            input("按回车关闭...")
            return
    procs: list[subprocess.Popen] = []

    if port_in_use(SITE_PORT) and http_ok(f"{SITE_URL}/api/v1/healthz"):
        print(f"[OK] 网站已在运行：{SITE_URL}")
    else:
        procs.append(spawn([py, "-m", "uvicorn", "app.main:app",
                            "--port", str(SITE_PORT), "--log-level", "warning"], root))
        print(f"[..] 正在启动网站 :{SITE_PORT}")

    if port_in_use(TOOL_PORT) and http_ok(f"{TOOL_URL}/api/state"):
        print(f"[OK] 录入工具已在运行：{TOOL_URL}")
    else:
        procs.append(spawn([py, str(root / "tools" / "wrongbook_tool" / "server.py")], root))
        print(f"[..] 正在启动录入工具 :{TOOL_PORT}")

    for _ in range(60):
        if http_ok(f"{SITE_URL}/api/v1/healthz", 1.0) and http_ok(f"{TOOL_URL}/api/state", 1.0):
            break
        time.sleep(0.5)

    if not review_version_ok(f"{TOOL_URL}/api/state") or not review_version_ok(f"{SITE_URL}/api/v1/healthz", "wrongbook_review_version"):
        print("[X] 新版GPT强审核服务未成功启动，不打开旧工具。请检查端口和Python依赖。")
        input("按回车关闭...")
        return
    print(f"\n[OK] 学习网站   {SITE_URL}")
    print(f"[OK] 错题录入   {TOOL_URL}")
    print("  关闭本窗口即停止两个服务。")
    webbrowser.open(TOOL_URL)

    try:
        while True:
            for p in procs:
                if p.poll() is not None:
                    print("某个服务退出了，窗口即将关闭…")
                    for q in procs:
                        q.terminate()
                    return
            time.sleep(1)
    except KeyboardInterrupt:
        for q in procs:
            q.terminate()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # 双击场景：报错不能闪退
        print(f"启动失败：{exc}")
        input("按回车关闭...")
