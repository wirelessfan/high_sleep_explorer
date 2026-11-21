# Gemini 协作说明（learning_highschool）

> 给外部 AI（Gemini 网页版）的工作约定。你只负责「读代码 + 出 diff」，一切执行落地在本地完成。

## 1. 你的边界

| 能力 | 你（Gemini 网页版） | 本地（WorkBuddy / 用户） |
|---|---|---|
| 读取公开仓库文本文件 | ✅ 通过 raw URL | ✅ 直接读磁盘 |
| 浏览未提交的本地改动 | ❌ 看不到 | ✅ |
| 执行代码 / 跑 pytest / 构建 | ❌ | ✅ |
| 接收整包 ZIP 批量改 | ❌ 不建议（452 文件、13MB 装不进上下文） | ✅ |
| git commit / push / 部署 | ❌ 不要尝试，也不要给命令 | ✅ 统一由本地执行 |

结论：**你出补丁（unified diff），本地审阅后 `git apply`。**

## 2. 仓库与链接

- 仓库：<https://gitee.com/matrix_python/learning_highschool>（公开）
- 工作分支：`codex/discovery-understanding-review`
- 页面链接模板：
  `https://gitee.com/matrix_python/learning_highschool/blob/codex/discovery-understanding-review/<文件路径>`
- 纯文本（推荐你读这个）：
  `https://gitee.com/matrix_python/learning_highschool/raw/codex/discovery-understanding-review/<文件路径>`

示例：
<https://gitee.com/matrix_python/learning_highschool/raw/codex/discovery-understanding-review/app/routers/wrongbook.py>

## 3. 每次任务的标准流程

1. 用户给任务 + 明确的文件清单（不给清单就不要猜，先要求清单）。
2. 你逐个用 raw URL 读原文，**不要凭记忆或推断写代码**。
3. 输出格式：每个文件一个 diff 代码块，路径必须与仓库一致：

   ```diff
   --- a/app/services/wrongbook.py
   +++ b/app/services/wrongbook.py
   @@ -12,6 +12,9 @@
   ```
   - 每个 hunk 保留 3 行上下文，行号可以模糊，但代码必须能对上原文。
   - 不重写整个文件、不省略未改动行、不用 `...` 占位。
4. 一次只改 1–3 个文件；需要跨 3 个以上文件时先拆任务。
5. 收尾附 3 行以内的「风险与验证点」：改了什么、可能影响哪里、本地该跑哪条测试。

## 4. 项目约定（硬约束）

- 后端：FastAPI + SQLite。路由在 `app/routers/`，业务逻辑在 `app/services/`，表结构在 `app/db.py`。
- 前端：**原生 ES Modules，无构建链、无框架、无 npm**。视图在 `web/js/views/`，接口封装统一走 `web/js/api.js`，样式在 `web/styles/app.css`。
- 语言：注释、UI 文案一律中文；受众是高中生，措辞要直白。
- 依赖：`requirements.txt` 之外**不得引入新依赖**；确有必要先在正文里说明理由并等确认。
- 测试：`tests/test_*.py`（pytest）。任何后端行为改动必须同时给出对应测试的 diff。
- 提交信息：英文短句、祈使句（仓库惯例），由本地写，不用你产出。
- 不入库的目录（已 gitignore，**不要引用、不要建议新增文件**）：
  `data/`、`assets/wrongbook/`、`wrong_src/`、`.venv/`、`dist/`、`错题本一键启动.exe`
- 密钥：仓库里没有 `.env`，也不要索要或写出任何 API Key；相关配置只写占位符，如 `AI_API_KEY`

## 5. 安全红线

- 不输出 `git push --force`、`git reset --hard`、`rm -rf` 之类破坏性命令。
- 不建议改动 `deploy/deploy.sh` 中涉及服务器地址、密钥、证书的行。
- 不确定的地方直说「需要看 X 文件」，不要编造函数名、字段名、接口路径。

## 6. 关键文件直链（按需取用）

| 文件 | raw 链接 |
|---|---|
| `app/main.py` | `.../raw/codex/discovery-understanding-review/app/main.py` |
| `app/db.py` | `.../raw/codex/discovery-understanding-review/app/db.py` |
| `app/routers/wrongbook.py` | `.../raw/codex/discovery-understanding-review/app/routers/wrongbook.py` |
| `app/routers/relax.py` | `.../raw/codex/discovery-understanding-review/app/routers/relax.py` |
| `app/services/wrongbook.py` | `.../raw/codex/discovery-understanding-review/app/services/wrongbook.py` |
| `app/services/grading.py` | `.../raw/codex/discovery-understanding-review/app/services/grading.py` |
| `app/services/ai_client.py` | `.../raw/codex/discovery-understanding-review/app/services/ai_client.py` |
| `web/js/api.js` | `.../raw/codex/discovery-understanding-review/web/js/api.js` |
| `web/js/app.js` | `.../raw/codex/discovery-understanding-review/web/js/app.js` |
| `web/js/views/wrongbook.js` | `.../raw/codex/discovery-understanding-review/web/js/views/wrongbook.js` |
| `web/styles/app.css` | `.../raw/codex/discovery-understanding-review/web/styles/app.css` |
| `content/wrongbook_taxonomy.json` | `.../raw/codex/discovery-understanding-review/content/wrongbook_taxonomy.json` |

`...` 前缀 = `https://gitee.com/matrix_python/learning_highschool`

## 7. 一句话版本

读指定 raw 文件 → 按文件给 unified diff（含上下文）→ 附验证点；不 clone、不执行、不推送、不引入依赖。
