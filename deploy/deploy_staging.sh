#!/usr/bin/env bash
# 预览环境部署（8091 端口，独立数据库，不影响生产 8090）
#
#   bash deploy/deploy_staging.sh [branch]
#
# 默认部署当前分支。AI 走 LEARN_AI_STUB=1 演示模式；
# review 后把 /etc/learning-highschool/ai.env 里的 LEARN_AI_STUB 改成 0
# 并填入 LEARN_AI_KEY，即可切真实 AI 服务。
set -euo pipefail

HOST="${HOST:-aliyun}"
BRANCH="${1:-$(git branch --show-current)}"
STAGE_DIR=/opt/learning_highschool_staging
STAGE_DATA=/var/lib/learning-highschool-staging
STAGE_SERVICE=learning-highschool-staging
STAGE_PORT=8091
STAGE_API_PORT=8001

say() { printf '\n== %s\n' "$*"; }

say "1/6 准备目录并同步代码"
# 生产目录不是 git 仓库（deploy.sh 用 tar 直传），staging 同样用 tar
ssh "$HOST" "mkdir -p $STAGE_DIR $STAGE_DATA"
tar -czf -   --exclude='./.git' --exclude='./.venv' --exclude='__pycache__'   --exclude='./data' --exclude='./.pytest_cache'   . | ssh "$HOST" "tar -xzf - -C $STAGE_DIR"
echo "  已同步当前工作区（分支：$BRANCH）"
ssh "$HOST" "chown -R learn:learn $STAGE_DIR $STAGE_DATA"

say "3/6 安装依赖"
ssh "$HOST" "cd $STAGE_DIR && { [ -d .venv ] || python3 -m venv .venv; } && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt"

say "4/6 systemd（独立 DB + AI 演示模式）"
ssh "$HOST" "cat > /etc/systemd/system/$STAGE_SERVICE.service" <<'UNIT'
[Unit]
Description=High School Learning Site (STAGING)
After=network.target

[Service]
User=learn
Group=learn
WorkingDirectory=/opt/learning_highschool_staging
Environment=LEARN_DB=/var/lib/learning-highschool-staging/staging.db
Environment=LEARN_AI_STUB=1
EnvironmentFile=-/etc/learning-highschool/ai.env
ExecStart=/opt/learning_highschool_staging/.venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port 8001 --workers 1 --proxy-headers
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/learning-highschool-staging

[Install]
WantedBy=multi-user.target
UNIT
ssh "$HOST" "mkdir -p /etc/learning-highschool && if [ ! -e /etc/learning-highschool/ai.env ]; then umask 077; cat > /etc/learning-highschool/ai.env; else cat > /dev/null; fi" <<'AIEOF'
# 预览环境 AI 配置。review 后切真实服务：
#   LEARN_AI_STUB=0
#   LEARN_AI_KEY=sk-你的key
#   LEARN_AI_BASE_URL=https://api.deepseek.com/v1   （或中转站地址）
#   LEARN_AI_MODEL=deepseek-chat
LEARN_AI_STUB=1
LEARN_AI_BASE_URL=https://api.deepseek.com/v1
LEARN_AI_MODEL=deepseek-chat
AIEOF
ssh "$HOST" "systemctl daemon-reload && systemctl enable $STAGE_SERVICE >/dev/null 2>&1 || true && systemctl restart $STAGE_SERVICE && sleep 2 && systemctl is-active $STAGE_SERVICE"

say "5/6 Caddy :$STAGE_PORT"
ssh "$HOST" "cat > /tmp/stage_caddy_block" <<'BLOCK'
# 预览环境（staging，独立数据库）
:8091 {
	encode zstd gzip
	reverse_proxy 127.0.0.1:8001
}
BLOCK
ssh "$HOST" bash -s <<'REMOTE'
python3 - <<'PY'
import pathlib
p = pathlib.Path("/etc/caddy/Caddyfile")
s = p.read_text()
block = pathlib.Path("/tmp/stage_caddy_block").read_text()
if ":8091 {" not in s:
    s = s.rstrip() + "\n\n" + block
    p.write_text(s)
    print("Caddyfile appended :8091")
else:
    print("already present")
PY
caddy validate --config /etc/caddy/Caddyfile 2>&1 | tail -1
systemctl reload caddy 2>/dev/null || systemctl restart caddy
sleep 2
systemctl is-active caddy
REMOTE

say "6/6 健康检查"
ssh "$HOST" "curl -fsS http://127.0.0.1:$STAGE_API_PORT/api/v1/healthz && echo"

printf '\n预览地址: http://123.56.217.104:%s/  （HTTP，独立 staging 数据库）\n' "$STAGE_PORT"
echo "AI 演示模式: 开（LEARN_AI_STUB=1）"
echo "切真实 AI:   改 /etc/learning-highschool/ai.env 后 systemctl restart $STAGE_SERVICE"
