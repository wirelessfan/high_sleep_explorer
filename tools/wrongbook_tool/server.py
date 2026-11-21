"""错题录入工具 · 本地服务。

启动（用网站的虚拟环境即可）：
    .venv/Scripts/python.exe tools/wrongbook_tool/server.py
    # 浏览器打开 http://127.0.0.1:8021

职责（全部本地运行，不经过任何第三方中转）：
- 递归扫描文件夹里的截图/照片（jpg/png/webp/bmp/gif，按内容 md5 去重）
- 提供本地图片预览（只允许访问已扫描根目录下的文件）
- AI 识别代理：优先走网站站内通道（/api/v1/wrongbook/photo/recognize），
  也可配置自定义 OpenAI 兼容视觉端点（如 DeepSeek/GLM/Qwen-VL）
- 批量导入代理：把整理好的错题 POST 到网站 /api/v1/wrongbook/import

鉴权说明：网站账号密码登录后 token 只保存在本机 config.json，不上传别处。
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import os
import re
import socket
import time
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

TOOL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = TOOL_DIR / "config.json"
MOBILE_DIR = TOOL_DIR / "mobile_uploads"   # 手机拍照上传暂存
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
_IMPORT_MAGIC = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",
    b"GIF8": "gif",
}

# 已扫描的根目录：图片预览只允许这些目录下的文件（防路径穿越）。
ALLOWED_ROOTS: set[str] = set()
try:
    MOBILE_DIR.mkdir(exist_ok=True)
    ALLOWED_ROOTS.add(str(MOBILE_DIR.resolve()))
except OSError:
    pass

RECOGNIZE_PROMPT = (
    "你是题目录入助手。用户会给你一张高中理科题目截图，"
    "请把截图里的题目完整转录成结构化文本。要求：\n"
    "1. 数学公式用纯文本表述（如 x^2、√3、分数写成 a/b），不要用 LaTeX。\n"
    "2. 只转录题目本身，不要作答、不要添加截图里没有的内容。\n"
    "3. 截图里有多道题时，只转录最完整的一道；文字看不清用〔?〕标注。\n"
    "4. 只输出 JSON，格式："
    '{"stem": "题干", "options": ["A内容", "B内容", "C内容", "D内容"], '
    '"subject": "physics|chemistry|math|biology|geography"}'
    "；不是选择题时 options 给空数组，subject 按学科判断。"
)


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


app = FastAPI(title="错题录入工具", docs_url=None, redoc_url=None)
PORT = 8021
# 默认同步目标：线上网站（家人任何设备打开都能看到）；本机调试可改成 http://127.0.0.1:8011
DEFAULT_SITE = os.environ.get("WB_SITE", "https://123-56-217-104.sslip.io:8090")


class LoginIn(BaseModel):
    site_url: str = Field(min_length=8, max_length=200)
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class CustomIn(BaseModel):
    base_url: str = Field(min_length=8, max_length=200)   # 如 https://api.deepseek.com/v1
    api_key: str = Field(min_length=8, max_length=200)
    model: str = Field(min_length=1, max_length=100)


class ScanIn(BaseModel):
    folder: str = Field(min_length=1, max_length=300)


class ImageIn(BaseModel):
    image: str = Field(min_length=32, max_length=6 * 1024 * 1024)


class ImportIn(BaseModel):
    items: list[dict] = Field(min_length=1, max_length=100)


def _site(cfg: dict) -> str:
    return (cfg.get("site_url") or DEFAULT_SITE).rstrip("/")


def _guest_token(site: str) -> str:
    """用访客身份拿一个会话 token（错题本本身是家庭共享的，游客也能写入）。"""
    try:
        r = httpx.post(f"{site}/api/v1/session", timeout=20)
        r.raise_for_status()
        tok = r.json().get("token", "")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"连不上网站：{exc}")
    if not tok:
        raise HTTPException(status_code=502, detail="网站没有返回会话 token")
    return tok


def _site_headers(cfg: dict) -> dict:
    """网站鉴权头：优先用登录账号；没登录就自动用访客会话，保证「录了就能同步」。"""
    site = _site(cfg)
    if not cfg.get("token"):
        cfg["token"] = _guest_token(site)
        cfg["guest"] = True
        save_config(cfg)
    return {"Authorization": f"Bearer {cfg['token']}"}


def _site_post(cfg: dict, path: str, payload: dict, timeout: int = 60) -> httpx.Response:
    """带 token 失效自愈的 POST：401 时丢掉旧 token 换成访客会话再试一次。"""
    r = httpx.post(f"{_site(cfg)}{path}", headers=_site_headers(cfg), json=payload, timeout=timeout)
    if r.status_code == 401:
        cfg.pop("token", None)
        cfg.pop("guest", None)
        r = httpx.post(f"{_site(cfg)}{path}", headers=_site_headers(cfg), json=payload, timeout=timeout)
    return r


def _site_get(cfg: dict, path: str, timeout: int = 20) -> httpx.Response:
    r = httpx.get(f"{_site(cfg)}{path}", headers=_site_headers(cfg), timeout=timeout)
    if r.status_code == 401:
        cfg.pop("token", None)
        cfg.pop("guest", None)
        r = httpx.get(f"{_site(cfg)}{path}", headers=_site_headers(cfg), timeout=timeout)
    return r


def _proxy_resp(resp: httpx.Response) -> JSONResponse:
    """把网站的响应（含错误 detail）原样转给工具前端。"""
    try:
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    except ValueError:
        raise HTTPException(status_code=502, detail=f"网站返回异常：HTTP {resp.status_code}")


def _parse_json_text(text: str) -> dict:
    """从模型输出里抠出 JSON（容忍 ```json 包裹与前后杂文）。"""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise RuntimeError("模型没有返回 JSON，请重试或换模型")
    return json.loads(m.group(0))


def _chat_custom(messages: list, cfg: dict, max_tokens: int = 1500) -> str:
    """本地自定义端点的 OpenAI 兼容 chat 调用，返回文本。"""
    c = cfg["custom"]
    r = httpx.post(
        c["base_url"].rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {c['api_key']}"},
        json={"model": c["model"], "messages": messages,
              "max_tokens": max_tokens, "temperature": 0.1},
        timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"自定义端点错误：HTTP {r.status_code} {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]


def _vision_user_content(image_b64: str, text: str) -> list:
    return [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
        {"type": "text", "text": text},
    ]


def _recognize_custom(image_b64: str, cfg: dict) -> dict:
    c = cfg["custom"]
    messages = [
        {"role": "system", "content": RECOGNIZE_PROMPT},
        {"role": "user", "content": _vision_user_content(image_b64, "请转录截图里的题目。")},
    ]
    text = _chat_custom(messages, cfg, max_tokens=1200)
    parsed = _parse_json_text(text)
    return {
        "stem": str(parsed.get("stem", "")).strip()[:2000],
        "options": [str(o).strip()[:200] for o in (parsed.get("options") or [])
                    if str(o).strip()][:6],
        "subject": str(parsed.get("subject", "")).strip(),
        "channel": "custom",
        "model": c["model"],
    }


# ---------------------------------------------------------------- 连接设置

@app.get("/api/state")
def state():
    cfg = load_config()
    return {
        "site_url": cfg.get("site_url", ""),
        "effective_site": _site(cfg),
        "default_site": DEFAULT_SITE,
        "username": cfg.get("username", ""),
        "logged_in": bool(cfg.get("token")) and not cfg.get("guest"),
        "guest_sync": bool(cfg.get("guest")),
        "custom_ready": bool(cfg.get("custom")),
        "custom_base_url": cfg.get("custom", {}).get("base_url", ""),
        "custom_model": cfg.get("custom", {}).get("model", ""),
    }


@app.post("/api/login")
def login(body: LoginIn):
    cfg = load_config()
    cfg["site_url"] = body.site_url.rstrip("/")
    try:
        r = httpx.post(f"{cfg['site_url']}/api/v1/session/login",
                       json={"username": body.username, "password": body.password},
                       timeout=15)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"连不上网站：{exc}")
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code,
                            detail=r.json().get("detail", "登录失败"))
    cfg["token"] = r.json().get("token", "")
    cfg["username"] = body.username
    cfg.pop("guest", None)
    save_config(cfg)
    return {"ok": True, "site_url": cfg["site_url"], "username": body.username}


@app.post("/api/logout")
def logout():
    cfg = load_config()
    cfg.pop("token", None)
    cfg.pop("guest", None)
    save_config(cfg)
    return {"ok": True}


@app.post("/api/custom")
def set_custom(body: CustomIn):
    cfg = load_config()
    cfg["custom"] = {"base_url": body.base_url.rstrip("/"),
                     "api_key": body.api_key, "model": body.model}
    save_config(cfg)
    return {"ok": True}


@app.post("/api/custom/clear")
def clear_custom():
    cfg = load_config()
    cfg.pop("custom", None)
    save_config(cfg)
    return {"ok": True}


# ---------------------------------------------------------------- 文件扫描

@app.post("/api/scan")
def scan(body: ScanIn):
    folder = Path(body.folder)
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"目录不存在：{folder}")
    files: dict[str, dict] = {}
    for root, _dirs, names in os.walk(folder):
        for name in names:
            p = Path(root) / name
            if p.suffix.lower() not in IMG_EXTS:
                continue
            try:
                data = p.read_bytes()
            except OSError:
                continue
            digest = hashlib.md5(data).hexdigest()  # 内容去重：同一截图复制多份只留一份
            if digest in files:
                continue
            files[digest] = {
                "path": str(p),
                "size": p.stat().st_size,
                "mtime": int(p.stat().st_mtime),
            }
    ALLOWED_ROOTS.add(str(folder.resolve()))
    out = sorted(files.values(), key=lambda x: -x["mtime"])
    return {"root": str(folder), "count": len(out), "files": out}


_IMG_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
              ".webp": "image/webp", ".bmp": "image/bmp", ".gif": "image/gif"}


@app.get("/api/image")
def image(path: str):
    p = Path(path).resolve()
    if not any(str(p).startswith(r + os.sep) or str(p) == r for r in ALLOWED_ROOTS):
        raise HTTPException(status_code=403, detail="只允许访问已扫描目录下的图片")
    if p.suffix.lower() not in IMG_EXTS or not p.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(p, media_type=_IMG_TYPES.get(p.suffix.lower(), "application/octet-stream"))


# ---------------------------------------------------------------- AI 识别

SOLVE_PROMPT = (
    "你是高中理科解题老师。用户给你一道题目（截图或文字），请独立解题并给出教学向解析。要求：\n"
    "1. 数学公式用纯文本（如 x^2、√3、a/b），不要用 LaTeX；推导分步骤写，每步一行。\n"
    "2. 只输出 JSON，格式："
    '{"answer_index": 0, "explain": "一句话关键点", "derivation": "逐步推导过程", '
    '"mistake_hint": "学生在这道题最常见的错因（一句话）"}'
    "；answer_index 是正确选项序号（A=0、B=1…），非选择题给 0 并在 derivation 里写解。"
)


class CompleteIn(BaseModel):
    image: str = Field(default="", max_length=6 * 1024 * 1024)
    stem: str = Field(min_length=1, max_length=20000)
    options: list[str] = Field(default_factory=list, max_length=8)
    qtype: str = Field(default="choice", max_length=16)


FILL_SOLVE_PROMPT = (
    "你是高中理科解题老师。用户给你一道填空题或解答题（没有选项），请独立解题。要求：\n"
    "1. 数学式用纯文本（x^2、√3、a/b、|x|），不要 LaTeX；推导分步骤，每步一行。\n"
    "2. 只输出 JSON："
    '{"answer_text":"最终答案（多解用「或」连接，区间用 [a,b] 写法，带单位）",'
    '"explain":"一句话关键思路","derivation":"逐步推导","mistake_hint":"学生最常见的错因（一句话）"}'
)


def _chat_any(messages: list, max_tokens: int = 2000) -> tuple[str, str]:
    """先用「连接设置」里的自定义端点，失败再走 WorkBuddy 本地网关，返回 (文本, 模型名)。"""
    cfg = load_config()
    errors = []
    if cfg.get("custom"):
        try:
            return _chat_custom(messages, cfg, max_tokens=max_tokens), cfg["custom"]["model"]
        except Exception as exc:
            errors.append(f"自定义端点：{exc}")
    gw = _local_gateway()
    if gw:
        url, key, model = gw
        try:
            return _post_chat(url, key, model, messages, max_tokens=max_tokens), model
        except Exception as exc:
            errors.append(f"本地网关 {model}：{exc}")
    raise HTTPException(status_code=503,
                        detail="本地 AI 都不可用：" + ("；".join(errors) or "未配置端点"))


@app.post("/api/ai/complete")
def ai_complete(body: CompleteIn):
    """本地 AI 解题补全：选择题给正确选项，填空/解答题给答案文本；都附推导与错因。"""
    fill = str(body.qtype or "choice").lower() != "choice"
    opts = [f"{chr(65 + i)}. {o}" for i, o in enumerate(body.options) if str(o).strip()]
    text = "题目：" + body.stem
    if opts and not fill:
        text += "\n选项：\n" + "\n".join(opts)
    system = FILL_SOLVE_PROMPT if fill else SOLVE_PROMPT
    if body.image.strip():
        s = body.image.strip()
        if s.startswith("data:"):
            _, _, s = s.partition(",")
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": _vision_user_content(s, text + "\n（以截图为准，文字仅作参考）")},
        ]
    else:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ]
    raw, model = _chat_any(messages, max_tokens=2000)
    try:
        parsed = _parse_json_text(raw)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"模型输出不是 JSON：{exc}")
    if fill:
        return {
            "answer_index": -1,
            "answer_text": str(parsed.get("answer_text", ""))[:500],
            "explain": str(parsed.get("explain", ""))[:1000],
            "derivation": str(parsed.get("derivation", "") or "\n".join(parsed.get("steps") or []))[:8000],
            "mistake_hint": str(parsed.get("mistake_hint", ""))[:1000],
            "model": model,
        }
    return {
        "answer_index": int(parsed.get("answer_index", -1)),
        "answer_text": "",
        "explain": str(parsed.get("explain", ""))[:1000],
        "derivation": str(parsed.get("derivation", ""))[:8000],
        "mistake_hint": str(parsed.get("mistake_hint", ""))[:1000],
        "model": model,
    }


@app.post("/api/recognize")
def recognize(body: ImageIn):
    s = body.image.strip()
    if s.startswith("data:"):
        _, _, s = s.partition(",")
    cfg = load_config()
    try:
        if cfg.get("custom"):
            result = _recognize_custom(s, cfg)
        else:
            r = httpx.post(f"{_site(cfg)}/api/v1/wrongbook/photo/recognize",
                           headers=_site_headers(cfg), json={"image": s}, timeout=120)
            if r.status_code >= 400:
                raise HTTPException(status_code=r.status_code,
                                    detail=r.json().get("detail", "识别失败"))
            result = r.json().get("result", {})
        if not result.get("stem"):
            raise RuntimeError("AI 没识别出题干，请裁剪得再完整些")
        return {"result": result}
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/m", include_in_schema=False)
def mobile_page():
    """手机拍照上传页（局域网内手机浏览器直接访问 /m）。"""
    return FileResponse(TOOL_DIR / "static" / "m.html")


# ---------------------------------------------------------------- 手机上传

def _lan_ip() -> str:
    """局域网 IP（不真正发包，只借 UDP 路由表探测）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _qr_svg(url: str) -> str | None:
    """URL → 二维码 SVG（base64 data URI）；未装 qrcode 库时返回 None。"""
    try:
        import qrcode
        import qrcode.image.svg
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=14)
        buf = io.BytesIO()
        img.save(buf)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


@app.get("/api/lan-info")
def lan_info():
    url = f"http://{_lan_ip()}:{PORT}"
    return {"url": url, "qr": _qr_svg(url),
            "mobile_page": f"{url}/m"}


class MobileImageIn(BaseModel):
    image: str = Field(min_length=32, max_length=6 * 1024 * 1024)


@app.post("/api/mobile/upload")
def mobile_upload(body: MobileImageIn):
    """手机拍照/相册图片上传暂存（存 tools/wrongbook_tool/mobile_uploads/）。"""
    s = body.image.strip()
    if s.startswith("data:"):
        _, _, s = s.partition(",")
    try:
        data = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="图片 base64 解码失败")
    ext = None
    for magic, e in _IMPORT_MAGIC.items():
        if data[:len(magic)] == magic:
            ext = e
            break
    if not ext:
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/webp/gif 图片")
    name = f"{int(time.time() * 1000)}.{ext}"
    (MOBILE_DIR / name).write_bytes(data)
    return {"ok": True, "path": str(MOBILE_DIR / name), "count": len(list(MOBILE_DIR.glob("*")))}


@app.get("/api/mobile/list")
def mobile_list():
    files = sorted(MOBILE_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"files": [{"path": str(p), "size": p.stat().st_size,
                       "mtime": int(p.stat().st_mtime)} for p in files
                      if p.suffix.lower() in IMG_EXTS]}


class MobileDeleteIn(BaseModel):
    path: str = Field(min_length=1, max_length=400)


@app.post("/api/mobile/delete")
def mobile_delete(body: MobileDeleteIn):
    p = Path(body.path).resolve()
    if p.parent != MOBILE_DIR.resolve() or not p.is_file():
        raise HTTPException(status_code=403, detail="只能删除手机上传目录里的文件")
    p.unlink()
    return {"ok": True}


# ---------------------------------------------------------------- 一键全自动

REPO_ROOT = TOOL_DIR.parent.parent

AUTO_PROMPT = """你是高中错题整理助手。用户给你一张试卷/作业/截图页面，
请把这一页拆成一道道独立题目（按题号），逐题完成：转录 → 判题型 → 独立解答 → 错因分析。

【拆分规则】
1. 一个题号算一道题；第 13 题与第 14 题绝不能合并，也绝不能把整页当成一道题。
2. 同题号下的小问（1）（2）属于同一道题；共享材料复制到每题 stem。
3. 页面上有几道就返回几道（最多 12 道），只返回一道会被判为失败。

【题型 qtype】
- choice：原文确实印着 A/B/C/D 单选选项；
- multi_choice：原题明确标注“多选”，答案必须给 answer_indices 选项序号数组；
- fill：横线、括号、空格填答案的题（“则 a = ____”），**options 必须给 []，绝对不要编造 ABCD**；
- solution：需要写过程/证明的题，options 也给 []。

【字段】
- stem：题干（纯文本数学式：x^2、√(x+1)、a/b、|x|，不要 LaTeX）
- options：仅 choice 给选项内容（不含 “A.” 前缀）
- picked：仅 choice 给学生实际选的错误选项序号；非选择题给 -1
- answer：仅 choice 给正确选项序号（A=0,B=1…）；非选择题给 -1；multi_choice 用 answer_indices / picked_indices 数组
- answer_text：fill/solution 的正确答案（多解用「或」连接，区间写 [a,b]）；choice 给 ""
- subject / chapter：只能从下面给定 id 里选（选不到给空字符串）
- skill：考点；explain：一句话关键思路；wrong_reason：学生最可能的错因
- derivation：分步推导，每步一行
- bbox：这道题在整张图中的位置 [x,y,w,h]，归一化 0~1，只框住这一题（从题号到答案横线/选项结束的完整一块，高度通常 ≥ 0.04，不要把题干挤成一条细线）

【输出】只输出 JSON，不要解释：
{"items":[{"no":"1","qtype":"fill","stem":"...","options":[],"picked":-1,"answer":-1,
"answer_text":"2","subject":"math","chapter":"functions","skill":"值域",
"explain":"...","wrong_reason":"...","derivation":"步骤1\n步骤2","bbox":[0.05,0.1,0.9,0.2]}]}
页面上没有题目就返回 {"items":[]}。

学科与章节 id 清单：
{taxonomy}"""


def _taxonomy_ids() -> dict:
    """本地 taxonomy：{subject: [chapter_id,...]}，用于校验 AI 返回的分类。"""
    try:
        raw = json.loads((REPO_ROOT / "content" / "wrongbook_taxonomy.json")
                         .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {s["id"]: [c["id"] for c in s.get("chapters", [])] for s in raw.get("subjects", [])}


def _taxonomy_prompt(tax: dict) -> str:
    lines = []
    for s, chapters in tax.items():
        lines.append(f"- {s}: " + ", ".join(chapters))
    return "\n".join(lines) if lines else "（无，subject 与 chapter 都返回空字符串）"


def _local_gateway() -> tuple[str, str, str] | None:
    """WorkBuddy 本地模型网关（~/.workbuddy/models.json）。

    优先用环境变量指定的模型；否则取第一个带视觉能力的模型。
    返回 (chat_url, api_key, model) 或 None。
    """
    try:
        models = json.loads((Path.home() / ".workbuddy" / "models.json")
                            .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(models, list) or not models:
        return None
    want = os.environ.get("WB_LOCAL_AI_MODEL") or os.environ.get("WORKBUDDY_VLM_MODEL")
    pick = None
    if want:
        pick = next((m for m in models if m.get("id") == want), None)
    if not pick:
        pick = next((m for m in models if m.get("supportsImages")), None)
    if not pick or not pick.get("url") or not pick.get("apiKey"):
        return None
    return pick["url"], pick["apiKey"], pick["id"]


def _post_chat(url: str, key: str, model: str, messages: list,
               max_tokens: int = 3000, timeout: float = 180) -> str:
    r = httpx.post(url, headers={"Authorization": f"Bearer {key}"},
                   json={"model": model, "messages": messages,
                         "max_tokens": max_tokens, "temperature": 0.1},
                   timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code} {r.text[:200]}")
    data = r.json()
    if "error" in data:
        raise RuntimeError(str(data["error"])[:200])
    return data["choices"][0]["message"]["content"]


def _normalize_auto_items(parsed: dict, tax: dict) -> list[dict]:
    """校验/规范 AI 返回的题目条目：题型、选项、答案、坐标全部收敛。"""
    items = []
    for raw in (parsed.get("items") or [])[:12]:
        stem = str(raw.get("stem", "")).strip()
        if not stem:
            continue
        options = [str(o).strip() for o in (raw.get("options") or []) if str(o).strip()][:6]
        qtype = str(raw.get("qtype", "")).strip().lower()
        if qtype not in ("choice", "multi_choice", "fill", "solution"):
            qtype = "choice" if len(options) >= 2 else "fill"
        if qtype in ("choice", "multi_choice") and len(options) < 2:
            qtype = "fill"
        answer_indices = []
        picked_indices = []
        if qtype not in ("choice", "multi_choice"):
            options = []
            picked = answer = -1
        elif qtype == "multi_choice":
            answer = -1
            picked = -1
            answer_indices = raw.get("answer_indices")
            picked_indices = raw.get("picked_indices")
            valid = lambda values: isinstance(values, list) and len(values) == len(set(values)) and all(type(v) is int and 0 <= v < len(options) for v in values)
            if not valid(answer_indices): answer_indices = []
            if not valid(picked_indices): picked_indices = []
        else:
            def idx(v, default):
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    return default
                return v if 0 <= v < len(options) else default
            answer = idx(raw.get("answer"), 0)
            picked = idx(raw.get("picked"), (answer + 1) % len(options))
            if picked == answer:
                picked = (answer + 1) % len(options)
        answer_text = str(raw.get("answer_text", "")).strip()[:500] if qtype != "choice" else ""
        subject = str(raw.get("subject", "")).strip()
        if subject not in tax:
            subject = ""
        chapter = str(raw.get("chapter", "")).strip()
        if chapter not in tax.get(subject, []):
            chapter = ""
        bbox = raw.get("bbox")
        if not (isinstance(bbox, list) and len(bbox) == 4
                and all(isinstance(n, (int, float)) for n in bbox)):
            bbox = None
        else:
            bbox = [max(0.0, min(1.0, float(n))) for n in bbox]
        items.append({
            "no": str(raw.get("no", "")).strip()[:16],
            "stem": stem[:5000],
            "qtype": qtype,
            "answer_text": answer_text,
            "options": options,
            "picked": picked,
            "answer": answer,
            "answer_indices": answer_indices,
            "picked_indices": picked_indices,
            "review_status": "ready" if qtype == "choice" and answer >= 0 or qtype == "multi_choice" and answer_indices or qtype not in ("choice", "multi_choice") and answer_text else "needs_transcription",
            "review_reason": "原图或标准答案缺失，待补录" if qtype in ("choice", "multi_choice") and not (answer_indices if qtype == "multi_choice" else answer >= 0) else "",
            "subject": subject,
            "chapter": chapter,
            "skill": str(raw.get("skill", ""))[:64],
            "explain": str(raw.get("explain", ""))[:2000],
            "wrong_reason": str(raw.get("wrong_reason", ""))[:2000],
            "derivation": str(raw.get("derivation", ""))[:8000],
            "bbox": bbox,
        })
    return items


class AutoIn(BaseModel):
    image: str = Field(min_length=32, max_length=8 * 1024 * 1024)


@app.post("/api/ai/auto")
def ai_auto(body: AutoIn):
    """一键全自动：一张页面截图 → 所有题目（转录+答案+推导+错因+框选坐标）。

    通道优先级：
      1) 「连接设置」里配置的本地 AI 端点
      2) WorkBuddy 本地模型网关（~/.workbuddy/models.json，自动挑可用视觉模型）
      3) 网站站内 AI（识别 + 解题/分析，兜底，占网站限额）
    """
    s = body.image.strip()
    if s.startswith("data:"):
        _, _, s = s.partition(",")
    tax = _taxonomy_ids()
    messages = [
        {"role": "system", "content": AUTO_PROMPT.replace("{taxonomy}", _taxonomy_prompt(tax))},
        {"role": "user", "content": _vision_user_content(s, "请整理这张页面上的所有题目。")},
    ]
    errors = []

    cfg = load_config()
    # 1) 自定义端点
    if cfg.get("custom"):
        try:
            text = _chat_custom(messages, cfg, max_tokens=4000)
            items = _normalize_auto_items(_parse_json_text(text), tax)
            return {"items": items, "channel": "local-custom",
                    "model": cfg["custom"]["model"], "errors": errors}
        except Exception as exc:
            errors.append(f"自定义端点：{exc}")

    # 2) WorkBuddy 本地网关
    gw = _local_gateway()
    if gw:
        url, key, model = gw
        try:
            text = _post_chat(url, key, model, messages, max_tokens=4000)
            items = _normalize_auto_items(_parse_json_text(text), tax)
            return {"items": items, "channel": "workbuddy-local",
                    "model": model, "errors": errors}
        except Exception as exc:
            errors.append(f"本地网关 {model}：{exc}")

    # 3) 网站 AI 兜底（单题：识别 → 解题/分析）
    try:
        r = httpx.post(f"{_site(cfg)}/api/v1/wrongbook/photo/recognize",
                       headers=_site_headers(cfg), json={"image": s}, timeout=120)
        if r.status_code >= 400:
            raise RuntimeError(r.json().get("detail", f"HTTP {r.status_code}"))
        recog = r.json().get("result", {})
        stem = recog.get("stem", "")
        if not stem:
            raise RuntimeError("网站 AI 没识别出题干")
        options = recog.get("options") or ["（非选择题）", "（非选择题）"]
        item = {"stem": stem, "options": options, "picked": 0, "answer": 0,
                "subject": recog.get("subject", ""), "chapter": "", "skill": "",
                "explain": "", "wrong_reason": "", "derivation": "", "bbox": None}
        try:
            a = httpx.post(f"{_site(cfg)}/api/v1/wrongbook/photo/analyze",
                           headers=_site_headers(cfg),
                           json={"stem": stem, "options": options, "picked": 0},
                           timeout=180)
            if a.status_code < 400:
                res = a.json()
                solve = res.get("solve") or {}
                ana = res.get("analyze") or {}
                if isinstance(solve.get("answer"), int) and 0 <= solve["answer"] < len(options):
                    item["answer"] = solve["answer"]
                    item["picked"] = (solve["answer"] + 1) % len(options)
                item["explain"] = solve.get("key_point", "") or ""
                item["derivation"] = "\n".join(solve.get("steps") or [])
                item["wrong_reason"] = (ana.get("misconception", "") or "") + \
                    ((" " + ana.get("analysis", "")) if ana.get("analysis") else "")
        except Exception as exc:
            errors.append(f"网站分析：{exc}")
        return {"items": [item], "channel": "site", "model": "site-ai", "errors": errors}
    except Exception as exc:
        errors.append(f"网站兜底：{exc}")

    raise HTTPException(status_code=503,
                        detail="本地 AI 与网站 AI 都不可用：" + "；".join(errors))


@app.post("/api/import-image")
def import_image(body: ImageIn):
    """把（裁剪后的）题目图片上传到网站，返回可访问路径。"""
    cfg = load_config()
    r = _site_post(cfg, "/api/v1/wrongbook/import/image", {"image": body.image}, timeout=60)
    return _proxy_resp(r)


# ---------------------------------------------------------------- 分类与导入

@app.get("/api/taxonomy")
def taxonomy():
    cfg = load_config()
    return _proxy_resp(_site_get(cfg, "/api/v1/wrongbook/taxonomy", timeout=20))


@app.post("/api/import")
def import_batch(body: ImportIn):
    cfg = load_config()
    # overwrite=False：同一题重复录入时网站按题干去重跳过，不会重复累加「又错一次」
    r = _site_post(cfg, "/api/v1/wrongbook/import",
                   {"items": body.items, "overwrite": False}, timeout=60)
    if r.status_code >= 400:
        return _proxy_resp(r)
    data = r.json()
    data["site_url"] = _site(cfg)
    return data


app.mount("/", StaticFiles(directory=TOOL_DIR / "static", html=True), name="static")


if __name__ == "__main__":
    print(f"错题录入工具已启动")
    print(f"  本机访问   http://127.0.0.1:{PORT}")
    print(f"  手机访问   http://{_lan_ip()}:{PORT}/m （同一 WiFi 下扫码/输入即可拍照上传）")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
