# 错题本与 AI Review · 2026-11-13

## 发现与修订

|优先级|问题|修订|
|---|---|---|
|P1|Caddy 只给点分域名添加 8090，连字符域名在该端口返回空 200|两个域名均显式绑定 HTTPS 8090，保留原 443 和博客/预览站点；已在线修复并核验三入口 JSON|
|P1|AI HTTP 调用占用 SQLite BEGIN IMMEDIATE 写事务，最长可阻塞全站写入|短事务原子预占配额，网络调用期间释放连接；完成后短事务写回|
|P1|配额检查与计量不原子，可并发超额，同题可重复付费请求|新增持久化 ai_requests 租约；按用户/任务原子计量，同题互斥，失败释放，过期可恢复|
|P1|解题/变式渲染函数在 renderWrongbook 内，逐题弹层调用时作用域不可见|提升为模块函数；浏览器实际点击及缓存展示通过|
|P1|漏答的 picked=NULL 触发数据库异常，并被判分接口静默吞掉，后续错题可能丢失|忽略无有效选择的题；取消静默吞错，判分与错题入库同事务|
|P2|达到日限无法查看缓存；不存在/跨用户 ID 参与限额检查|先验证归属和缓存；仅新生成占额，缓存在停用/达限时仍可读|
|P2|最近错误选项改变后继续显示旧错因；并发 AI 结果可能回写过期选项|错误选项改变时清分析缓存；写回前核对最新选项，拒绝过期分析|
|P2|局部保存管理员配置会清空其他路由/限额/禁用状态|合并 patch；严格检查布尔/整数字段；损坏配置安全回落|
|P2|超时、网络断连、非法响应造成 500 或把非法答案默认为 A|统一可恢复错误及通道回退；校验 JSON 对象、列表、答案范围、变式数量/重复选项；拒绝无效内容入缓存|
|P2|错题重做返回/完成只重设相同 hash，页面不刷新；可重复提交|显式重新渲染列表；提交期间禁用；结果弹层关闭前列表已刷新|
|P2|前端可用态忽略被禁用/无 Key 通道；计数不刷新|按实际候选通道返回任务可用态，并实时更新展示用量；生产忽略演示开关，演示缓存不会被当作真实结果|
|P2|预览部署脚本每次覆盖 ai.env；生产服务没有加载 AI 环境文件|预览只在文件缺失时创建模板；生产加载现有 ai.env；密钥不入库、不返回客户端|

保留上一轮907题、476道挑战题、题面版本快照、分步题完整情境。GLM 功能从共享目录的进行中代码独立集成，没有覆盖共享目录；检查时生产与预览均未挂载新的 admin 路由。

## 验证

- 最终本地全套 pytest：**186 passed，204 subtests passed**；仅测试客户端弃用警告。
- 新增/修订回归覆盖：网络调用期间其他写入可立即取得 SQLite 锁；同题并发去重；不同题并发不能突破日限；失败释放；缓存达限可读；配置 patch；缓存失效；用户隔离；非法模型结构/答案；漏答后的错题入库。
- 15 个前端模块语法与相对导入检查通过；两个部署 shell 语法检查通过；Caddy 生成幂等性、博客与预览保留测试通过。
- 476 道挑战题独立数学复算通过；16主题907题内容自检通过。
- 本地隔离 API：907题、190作答单元全部100分通过，38阅读单元通过；错题收录→分析/解题缓存→2道演示变式→用户隔离→重做清零与奖励通过。
- 浏览器隔离账号：分析、解题、变式的生成及缓存展示，重做返回、答对清零+20分、完成后返回列表均通过；控制台无 error。
- 截图 `wrongbook-review-2026-11-13.jpg` 来自隔离数据库，**AI 为明确标注的 STUB 演示，并非真实模型质量验收**。

## 真实 AI 配置状态与限制

检查时生产进程没有 AI 环境变量；预览仅有 `LEARN_AI_STUB=1` 和旧模型配置；`/etc/learning-highschool/ai.env` 没有服务密钥。因此本轮无法验收真实模型解题/错因质量。修订版生产在无密钥时明确关闭 AI，错题收录、回看、重做正常。

管理员使用 `#/admin` 调整路由、模型、每任务限额及做连通性检查。密钥由服务器 `/etc/learning-highschool/ai.env` 提供，变量模板见 `deploy/ai.env.example`；修改环境文件后重启服务。原 `LEARN_AI_KEY/BASE_URL/MODEL` 继续作为 DeepSeek 兼容通道。拍照识别仅有客户端预留，尚未实现网站录入流程。

默认模型名依据实际获取的官方资料核对：

- [GLM-4.7-Flash](https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash)
- [DeepSeek 模型及价格](https://api-docs.deepseek.com/quick_start/pricing)（deepseek-v4-flash）
- [GPT-4o mini](https://developers.openai.com/api/docs/models/gpt-4o-mini)

## 发布记录

- 应用发布提交：`687b531d03adecf3657c3c5befd0ebc2e2889d1f`，已推送 Gitee master 并部署生产。
- Linux 云端独立测试服务（127.0.0.1:8002，独立目录 `/opt/learning_highschool_ai_review`、独立数据库 `/var/lib/learning-highschool-ai-review/app.db`）通过错题本整条流程及907题、190判分单元、38阅读单元；AI仅为STUB，原有预览8091未改动。验收后临时服务已停止。
- 生产迁移至 schema v8，服务、Caddy、原有预览服务均 active，无启动 error 日志。生产通过全部907题/190公开题面单元/38阅读单元核验（只读题目，不在生产作答发奖）。
- 公网连字符域名8090、点分域名8090、原443入口均返回健康JSON；生产HTML200；错题本和管理页面JS的SHA-256与Git发布对象一致，Cache-Control包含no-cache；匿名管理接口401，普通用户403。
- 迁移前后原有学习数据逐行比对均保留：progress 6，wrong_questions 0，events 9，achievements 4，checkins 7，card_owned 6，draws 11。迁移前17个用户保留，爸爸账号自动获得管理角色；验收只新建匿名读取会话。
- 代码备份：`/var/backups/learning-highschool/wrongbook-pre-687b531-20261113-093031.tar.gz`；数据库备份：同前缀 `.db`；服务及修复后的Caddy配置另有备份。
- Caddy入口修复前备份：`/var/backups/learning-highschool/caddy-8090-20261113-090522`。
- 生产AI环境加载通过独立systemd drop-in添加：`/etc/systemd/system/learning-highschool.service.d/50-ai-review.conf`；现有密钥文件未覆盖。验收时实际状态为 `ai.enabled=false, ai.stub=false`，等待服务密钥后才能进行真实模型质量验收。
- 正常访问：[8090站点](https://123-56-217-104.sslip.io:8090/)；备用[443站点](https://123-56-217-104.sslip.io/)。8090为HTTPS，请使用完整HTTPS地址。
