# Sunny 的高中探索旅程

面向高中生的物理 / 化学 / 数学微学习网站。每天 20–30 分钟，一个大主题按「基础 → 进阶 → 高级」学上一两周；六大版块 × 三档难度 = 最多 18 个学习单元，积分签到 + 名人卡收集 + 每日随机卡 + 每日主题 + 历史上的今天。

- 线上地址：<https://123-56-217-104.sslip.io:8090/>
- 部署目标：阿里云轻量 `123.56.217.104`，独立端口 **8090**（与同机 Hugo 博客的 `:80` 隔离）
- 技术栈：FastAPI + SQLite / 原生 ES Modules（**无构建链**，改完刷新即生效）
- 设计文档：[实施计划.md](实施计划.md)

---

## 一、换一台电脑继续开发（从这里开始）

### 1. 装基础环境

| 需要 | 说明 |
|---|---|
| Python 3.11+ | <https://www.python.org/downloads/>，安装时勾选 **Add Python to PATH** |
| Git | <https://git-scm.com/downloads> |
| Node.js（可选） | 只有跑 `check_frontend.mjs` 才需要，<https://nodejs.org/> |

> 不需要 Docker、不需要 npm install、不需要任何前端构建工具。

### 2. 克隆仓库

```bash
git clone https://gitee.com/matrix_python/learning_highschool.git
cd learning_highschool
```

首次会要求输入 Gitee 账号密码（或已在系统里保存的凭据）。

### 3. 建虚拟环境并装依赖

**Windows（Git Bash / PowerShell 均可）：**

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

**macOS / Linux：**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

以后所有命令都用 `.venv/Scripts/python.exe`（Win）或 `.venv/bin/python`（Mac/Linux），不要用系统 Python。

### 4. 本地跑起来

```bash
# Windows
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8011
# macOS / Linux
.venv/bin/python -m uvicorn app.main:app --reload --port 8011
```

打开 <http://127.0.0.1:8011>。

**本地没有账号**，需要先建测试账号：

```bash
python tools/seed_users.py --password 123456
```

会创建 `sunny` / `dad` / `mom` 三个账号，密码 `123456`。

> 本地数据库在 `data/app.db`，已加入 `.gitignore`，不会污染仓库。想重置就删掉 `data/` 目录。

### 5. 改完代码后的自检

```bash
python tools/check_content.py     # 内容完整性：选项重复、答案越界、解析为空、卡片缺图
python tools/check_frontend.mjs . # 前端 import 路径 + 语法（需要 Node）
python -m pytest tests -q         # 后端用例
```

**改内容必跑 `check_content.py`**，它能抓出缺图、答案越界这类问题。

### 6. 提交并推回 Gitee

```bash
git add -A
git commit -m "feat(content): 新增 XXX 主题"
git push origin master
```

### 7. 部署到线上（可选，需要 VPS 权限）

```bash
bash deploy/deploy.sh
```

脚本会同步代码、装依赖、重启服务、健康检查，**不会碰同机 `:80` 的博客**。
需要本机能 `ssh aliyun` 直连（详见 [SSH 配置](#ssh-配置)）。

---

## 二、内容怎么加

### 目录结构

```
content/
├── catalog.json           # 科目、主题索引、版块元数据
├── topics/*.json          # 每个主题一个文件（六大版块 + 三档难度）
├── cards/cards.json       # 卡片定义（图片、稀有度、套装、关联知识点）
├── rewards.json           # 积分、抽卡概率、兑换比例、核销白名单
├── bosses.json            # 守关怪图鉴（由 tools/generate_bosses.py 生成）
├── daily.json             # 每日主题（节日特辑等）
├── history.json           # 历史故事
└── media/media.json       # B 站视频素材与入选理由

web/js/views/              # 页面：home / subjects / topic / section / album / me / achievements / login
app/routers/               # API：session / content / progress / rewards / cards / achievements / bosses
app/services/              # 业务：grading / scoring / gacha / achievements / events / ratelimit
```

### 新增一个主题

1. 在 `content/topics/` 下新建 `<科目>-<主题>.json`（照抄现成文件改）
2. 在 `content/catalog.json` 的 `topics` 数组里登记，并挂到对应科目的 `topics` 列表
3. 补齐可视化：`assets/notes/intro-<主题id>.svg` 引导动画 + 主题 JSON 的 `diagrams`（≥2 页）
4. 跑 `python tools/check_diagrams.py --strict` 与 `python tools/check_content.py`
5. 需要 Boss 立绘就改 `tools/generate_bosses.py` 的配置后重新生成

### 题目档位

每个版块支持 `basic` / `advanced` / `expert` 三档，内容放在 `sections[].tiers` 里。
全通判定按「版块 × 已开放档位」的单元计。

### 主题页图集

主题 JSON 顶层的 `diagrams` 会在主题页渲染成「图解补充」面板，支持按钮、
← → 键与触屏滑动翻页：

```json
"diagrams": [
  { "src": "/assets/notes/xxx.svg", "title": "一句话标题", "caption": "这张图想讲的结论" }
]
```

插图请扩展生成器 `tools/generate_physics_svgs.py` / `tools/generate_science_diagrams.py`，
不要手写坐标——曲线、切点、受力、能量必须由同一组数学状态推导。

### 题目档位

每个版块支持 `basic` / `advanced` / `expert` 三档，内容放在 `sections[].tiers` 里。
全通判定按「版块 × 已开放档位」的单元计。

### 答案位置

`python tools/balance_answers.py` 会把正确答案轮换到 A/B/C/D，避免全选 A 就能得分。
默认直接写回文件，加 `--dry-run` 只统计。

---

## 三、当前内容量

| 项 | 数量 |
|---|---|
| 主题 | 11 个（物理 5 / 化学 5 / 数学 1） |
| 题目 | 556 题（基础 / 进阶 / 高级三档） |
| 教学插图 | 43 张 SVG + 11 张主题引导动画 |
| 卡片 | 17 张，5 个套装 |
| Boss 立绘 | 60 张 SVG |
| 后端测试 | 126 个用例 |

> 内容仍在持续扩充。准确数字以 `python tools/check_content.py` 与
> `python tools/check_diagrams.py` 的输出为准。

## 三之二、可视化方针（新增内容必须遵守）

图解与动画是本站的基本教学形态，不是装饰。三条硬要求：

1. 每个主题必须有引导动画 `assets/notes/intro-<topic-id>.svg`；
2. 每个主题必须有 **≥2 页**图解补充（主题 JSON 的 `diagrams` 字段，页面自动渲染成可翻页图集）；
3. 「难点剖析」「实战巩固」里的高频易错点必须能指向一张图。

插图一律由 `tools/generate_physics_svgs.py` / `tools/generate_science_diagrams.py`
按数学模型生成，禁止手写坐标；动画统一用 SMIL，并提供 `prefers-reduced-motion` 静态回退。

完整规范与覆盖现状见 [可视化方针.md](可视化方针.md)，
覆盖率用 `python tools/check_diagrams.py` 查看（`--strict` 可作为新主题验收门禁）。

## 四、功能概览

**六大版块**：快速测试 → 基础闯关 → 知识点总结 → 难点剖析 → 实战巩固 → Boss 彩蛋

**三档难度**：基础（70–80 分）/ 进阶（80–90）/ 高级（90–95），积分系数 1.0 / 1.3 / 1.6。进度按 `(用户, 主题, 版块, 档位)` 四元组记录，「全通」按已开放单元判定。主题时长由 `content_loader.topic_minutes()` 逐单元实时汇总，无需手工维护。

**每日主题**：`content/daily.json` 按日期轮转主题，节日特辑（双十一、圆周率日、高考、教师节等）优先接管并附学科 digest。`GET /api/v1/daily?date=YYYY-MM-DD` 可指定日期调试。

**历史上的今天**：`content/history.json` 的科学史事件，按 (月, 日) 精确命中；当日无条目则回退到年内最近一条并返回 `fallback` + 带符号 `offset_days`，前端如实标注「X 天前」。`GET /api/v1/history?date=...`。

**账号**：`sunny` / `dad` / `mom`，密码登录，可自助修改密码。首次登录后可在「我的」页改。

**积分**：签到（连签加成）、版块首通、Boss、主题全通、复习（日上限）

**成就卡**（真金白银，注意预算）：
- `100 积分 = 1 张 50 元卡`，每天最多兑 2 张（50–100 元/天）
- 每日随机卡：每人每天 1 次，¥5(50%) / ¥10(30%) / ¥20(15%) / ¥50(5%)，期望 ¥11/天
- 抽到的卡可赠送给 `sunny`
- **核销只能由 `dad` / `mom` 操作**，白名单在 `rewards.json` 的 `achievement.redeem_by`

**数值都在 `content/rewards.json` 里**，改配置不用改代码。

## 五、部署与运维

| 项 | 位置 |
|---|---|
| 代码 | `/opt/learning_highschool` |
| 数据库 | `/var/lib/learning-highschool/app.db` |
| 备份 | `/var/backups/learning-highschool/`（每日 4:15，保留 14 天） |
| 服务 | `systemctl status learning-highschool` |
| 日志 | `journalctl -u learning-highschool -f` |
| 反向代理 | Caddy `/etc/caddy/Caddyfile` 的 `:8090` 块 |

### SSH 配置

本机 `~/.ssh/config` 加：

```
Host aliyun
    HostName 123.56.217.104
    User root
    IdentityFile ~/.ssh/aliyun_matrix2004.pem
    IdentitiesOnly yes
```

密钥文件**不入库**（`.gitignore` 已排除 `*.pem`）。

## 六、常见问题

**Q：页面改了但浏览器没变**
代码无构建链，浏览器可能缓存了旧 JS/CSS。服务端已对 `.html/.css/.js` 设置 `no-cache`，若仍不生效就硬刷新（Ctrl+Shift+R）。

**Q：本地起不来，报 `ModuleNotFoundError`**
用了系统 Python。改用 `.venv/Scripts/python.exe -m uvicorn ...`。

**Q：`seed_users.py` 建完账号登录不了**
确认用的是同一个数据库。默认读 `data/app.db`，可用 `LEARN_DB` 环境变量指定：

```bash
LEARN_DB=/path/to/app.db python tools/seed_users.py
```

**Q：改了 `db.py` 加字段，老数据怎么办**
在 `init_db()` 里加迁移函数，按「列是否存在」判断并执行（幂等），不要只依赖版本号比较——历史上出现过两个迁移撞同一个版本号被跳过的问题。

## 七、许可

人物肖像来自 Wikimedia Commons，均为 Public Domain，来源记录见 [实施计划.md](实施计划.md) 附录 15.1。
卡通插画（`assets/art/`）与 Boss 立绘（`assets/bosses/`）为原创 SVG。
