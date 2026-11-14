"""应用入口：路由注册、静态挂载、异常处理。"""
from __future__ import annotations

import mimetypes
import os
from contextlib import asynccontextmanager

# Windows 注册表有时把 .js/.css 登记成 text/plain，浏览器会按严格 MIME 规则
# 拒绝执行 <script type="module">，导致整站白屏。显式覆盖，跨平台无害。
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import content_loader, db
from app.routers import (achievements, admin, blindbox, bosses, cards, content,
                         progress, rewards, session, wishes, wrongbook)
BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
ASSETS_DIR = BASE_DIR / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    content_loader.clear_cache()
    yield


app = FastAPI(
    title="高中理科学习助手",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "invalid_request", "message": "参数不合法",
                           "detail": exc.errors()}},
    )


@app.exception_handler(content_loader.ContentError)
async def content_handler(request: Request, exc: content_loader.ContentError):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "content_error", "message": str(exc)}},
    )


@app.get("/api/v1/healthz")
async def healthz():
    return {"ok": True, "version": app.version}


@app.middleware("http")
async def no_cache_for_shell(request: Request, call_next):
    """HTML/CSS/JS 不做强缓存，API 响应一律不缓存。

    前端没有构建链、也没有文件名哈希，如果浏览器缓存了旧 CSS，
    会出现「改了不生效」的困惑（实测踩过）。静态卡片图的缓存交给 Caddy。

    API 必须 no-store：前端拿到的是「内容 + 资源路径」，一旦 JSON 被缓存，
    换图后仍会指向旧资源，表现为「服务器已更新但页面还是旧图」。
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    elif path.endswith((".html", ".css", ".js")) or path in ("/", ""):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


app.include_router(session.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(progress.router, prefix="/api/v1")
app.include_router(rewards.router, prefix="/api/v1")
app.include_router(cards.router, prefix="/api/v1")
app.include_router(bosses.router, prefix="/api/v1")
app.include_router(achievements.router, prefix="/api/v1")
app.include_router(wrongbook.router, prefix="/api/v1")
app.include_router(blindbox.router, prefix="/api/v1")
app.include_router(wishes.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

# 静态资源：卡片图、示意图
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# 前端 SPA：放在最后，兜底所有非 API 路径
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
