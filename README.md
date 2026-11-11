# 高中理科学习助手

面向高中生的物理 / 化学 / 数学微学习网站。每天 20–30 分钟精炼一个小主题，六大版块闯关，积分签到 + 名人卡收集。

- 部署目标：阿里云轻量 `123.56.217.104`，独立端口 **8090**（与同机 Hugo 博客隔离）
- 技术栈：FastAPI + SQLite / 原生 ES Modules（无构建链）
- 完整设计见 [实施计划.md](实施计划.md)

## 当前状态

**已上线可用**：https://123-56-217-104.sslip.io:8090/

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 骨架上线（FastAPI + Caddy 8090 + systemd） | 完成 |
| P1 | 内容框架 + 三主题内容（3×6×27 = 81 题） | 完成 |
| P2 | 六版块学习流程 + 即时判分 + 薄弱点 | 完成 |
| P3 | 积分 · 签到 · 集卡（12 张卡 / 5 套装） | 完成 |
| P4 | 移动端打磨与验收 | 进行中 |

## 本地运行

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
.venv/bin/python -m uvicorn app.main:app --reload --port 8011
# 打开 http://127.0.0.1:8011
```

自检与测试：

```bash
python tools/check_content.py       # 内容完整性（选项重复/答案越界/解析为空）
python tools/balance_answers.py     # 正确答案位置均衡（默认写回，--dry-run 只统计）
node tools/check_frontend.mjs .     # 前端 import 路径（静态 + 动态）
python -m pytest tests -q           # 40 个后端用例
```

## 部署

```bash
bash deploy/deploy.sh
```

脚本会建用户、装 venv、写 systemd 与 Caddy `:8090` 配置、健康检查、装备份 cron。
不会改动同机 `:80` 的 Hugo 博客。

## 目录

```
.
├── 任务书.txt                  # 原始需求
├── 实施计划.md                 # 完整实施方案（架构/数据/API/部署/验收）
└── design/mockup/              # 视觉样稿
    ├── cards_v1.html           # 集卡册整页（浏览器直接打开）
    ├── card_detail.html        # 单卡 + 详情弹层
    ├── img/                    # 12 张公有领域肖像（已统一调色）
    └── shot_*.png              # 渲染截图
```

## 六大版块

快速测试 → 基础闯关 → 知识点总结 → 难点剖析 → 实战巩固 → Boss 彩蛋

## 集卡系统

12 张物理/数学名人卡（牛顿、伽利略、法拉第、麦克斯韦、居里夫人、爱因斯坦、欧几里得、阿基米德、笛卡尔、高斯、欧拉、拉马努金），稀有度 N/R/SR/SSR，双保底，重复转碎片，5 个套装。

卡面素材来自 Wikimedia Commons 公有领域肖像，统一双色调处理，单张 10–22KB。

## 部署

见 [实施计划.md](实施计划.md) 第 10 节。

## 许可

人物肖像素材均为 Public Domain，来源与授权记录见 `实施计划.md` 附录 15.1。
