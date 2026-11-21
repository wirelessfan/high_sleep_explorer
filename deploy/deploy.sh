#!/usr/bin/env bash
# 部署到 VPS（幂等，可重复执行）
#
#   bash deploy/deploy.sh
#
# 首次执行会自动建用户、装 venv、写 systemd 与 Caddy 配置。
set -euo pipefail

HOST="${HOST:-aliyun}"
APP_DIR=/opt/learning_highschool
DATA_DIR=/var/lib/learning-highschool
LOG_DIR=/var/log/learning-highschool
BACKUP_DIR=/var/backups/learning-highschool
SERVICE=learning-highschool
DOMAIN="${DOMAIN:-123-56-217-104.sslip.io, 123.56.217.104.sslip.io}"
PORT="${PORT:-8090}"

say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }

say "1/7 准备远端目录与用户"
ssh "$HOST" bash -s <<EOF
set -euo pipefail
id -u learn >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin learn
mkdir -p $APP_DIR $DATA_DIR $LOG_DIR $BACKUP_DIR $DATA_DIR/wrongbook-images
chown -R learn:learn $DATA_DIR $LOG_DIR
EOF

say "2/7 同步代码"
# 本机可能没有 rsync（Windows Git Bash），用 tar over ssh 更稳
tar -czf - -C "$(dirname "${BASH_SOURCE[0]}")/.." \
  --exclude='./.git' --exclude='./.venv' --exclude='__pycache__' \
  --exclude='./data' --exclude='./.pytest_cache' --exclude='./design' \
  --exclude='./build' --exclude='./dist' --exclude='*.spec' \
  --exclude='./错题本一键启动.exe' \
  --exclude='./tools/wrongbook_tool/config.json' \
  --exclude='./wrong_src' --exclude='./assets/wrongbook' \
  . | ssh "$HOST" "tar -xzf - -C $APP_DIR"
ssh "$HOST" "chown -R learn:learn $APP_DIR"
# tar 是覆盖而非镜像：删掉已废弃的盲盒旧素材（bubu-*.svg 已被 labubu-*.png 取代）
ssh "$HOST" "rm -f $APP_DIR/assets/blindbox/bubu-*.svg"

say "3/7 安装依赖"
ssh "$HOST" bash -s <<EOF
set -euo pipefail
cd $APP_DIR
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
EOF

say "4/7 写 systemd 服务"
ssh "$HOST" bash -s <<EOF
set -euo pipefail
cat > /etc/systemd/system/$SERVICE.service <<'UNIT'
[Unit]
Description=High School Learning Site
After=network.target

[Service]
User=learn
Group=learn
WorkingDirectory=/opt/learning_highschool
Environment=LEARN_DB=/var/lib/learning-highschool/app.db
Environment=LEARN_WB_IMAGES=/var/lib/learning-highschool/wrongbook-images
EnvironmentFile=-/etc/learning-highschool/ai.env
# Production must never publish placeholder AI as a real analysis.
UnsetEnvironment=LEARN_AI_STUB
ExecStart=/opt/learning_highschool/.venv/bin/uvicorn app.main:app \\
  --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/learning-highschool

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable $SERVICE >/dev/null 2>&1 || true
systemctl restart $SERVICE
sleep 2
systemctl is-active $SERVICE
EOF

say "5/7 配置 Caddy（不动 :80 博客）"
ssh "$HOST" bash -s <<EOF
set -euo pipefail
CF=/etc/caddy/Caddyfile
cp -n \$CF \$CF.bak.learning 2>/dev/null || true
cp \$CF \$CF.pre-learning
python3 $APP_DIR/deploy/configure_caddy.py \$CF --domains "$DOMAIN" --port "$PORT"
if ! caddy validate --config /etc/caddy/Caddyfile; then
    cp \$CF.pre-learning \$CF
    exit 1
fi
systemctl reload caddy
sleep 3
systemctl is-active caddy
EOF

say "6/7 健康检查"
ssh "$HOST" "curl -fsS http://127.0.0.1:8000/api/v1/healthz && echo"

say "7/7 备份 cron"
ssh "$HOST" bash -s <<EOF
set -euo pipefail
cat > /etc/cron.d/$SERVICE-backup <<'CRON'
15 4 * * * root sqlite3 /var/lib/learning-highschool/app.db ".backup '/var/backups/learning-highschool/app-\$(date +\\%F).db'" && find /var/backups/learning-highschool -name 'app-*.db' -mtime +14 -delete
CRON
chmod 0644 /etc/cron.d/$SERVICE-backup
EOF

say "完成"
echo "  站点:    https://${DOMAIN%%,*}:$PORT/"
echo "  健康:    https://${DOMAIN%%,*}:$PORT/api/v1/healthz"
echo "  API文档: https://${DOMAIN%%,*}:$PORT/api/docs"
echo "  日志:    ssh $HOST journalctl -u $SERVICE -f"
