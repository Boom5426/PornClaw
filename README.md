<p align="center">
  <img src="assets/logo.svg" alt="PornClaw Logo" width="200" />
</p>

<h1 align="center">PornClaw</h1>

<p align="center">
  <b>Multi-Strategy Series Recommendation Engine for Adult Content Sources</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Playwright-enabled-2EAD33" />
  <img src="https://img.shields.io/badge/Telegram-Telethon-26A5E4" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
</p>

---

PornClaw 是一个面向成人内容站点和频道源的系列推荐引擎原型。

它的目标不是做“万能爬虫”，而是把不同类型的数据源统一接进同一条推荐闭环：

1. 输入数据源
2. 抓取最近内容
3. 归并为系列
4. 收集用户偏好与反馈
5. 输出可解释的 Top 5 推荐

如果你第一次打开这个仓库，先看这三件事：

1. 进入 `pornclaw/`
2. 用 `demo://seed` 跑通 2 分钟演示
3. 再决定要不要接真实源，例如通用 HTML 页面、Pornhub、Telegram 公开频道

## 当前支持哪些数据源

| Source Type | 输入示例 | 是否需要额外认证 | 适合场景 |
|---|---|---:|---|
| `demo` | `demo://seed` | 否 | 2 分钟演示、验证闭环 |
| `generic_template` | `https://example.com/feed` | 否 | 常见卡片流/列表流 HTML 站点 |
| `pornhub` | `https://www.pornhub.com/model/<name>/videos` | 否 | 公开可访问的 Pornhub 列表页 |
| `telegram` | `https://t.me/<channel_name>` | 是 | Telegram 公开频道抓取 |

这里的“template adapter”指的是**外部站点 HTML 提取模板**，不是 Jinja 页面模板。

## 最快跑起来

### 路线 A：2 分钟演示模式

```bash
cd pornclaw
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000`，保持默认数据源 `demo://seed`，直接点“抓取并开始推荐”。

### 路线 B：真实数据源模式

如果你要接真实站点：

```bash
cd pornclaw
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python scripts/init_db.py
uvicorn app.main:app --reload
```

然后：

- 通用模板站点示例：`https://example.com/feed`
- Pornhub 示例：`https://www.pornhub.com/model/<name>/videos`
- Telegram 示例：`https://t.me/<public_channel_name>`

Telegram 这条路径需要你先配置开发者凭证，见下文“配置 / 环境变量”。

## 第一次使用会发生什么

1. 首页输入 `source_url`
2. 按需选择 `source_type`
3. 在“高级数据源设置”里设置：
   - `credential_profile`
   - `max_items`
   - 是否抓详情页
4. 系统自动选择 adapter
5. 抓取结果先标准化，再聚合到系列层级
6. 你在候选页和推荐页继续反馈，下一轮排序会变

如果你只想验活：

- 保持 `source_url = demo://seed`
- `source_type = demo`
- 随便勾两个喜欢标签
- 点“抓取并开始推荐”

## 配置 / 环境变量

基础运行参数：

| Name | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLite 路径或其他数据库连接串 | `sqlite:///./pornclaw.db` |
| `SECRET_KEY` | 应用密钥 | `dev-secret` |
| `REQUEST_TIMEOUT_SECONDS` | HTTP 抓取超时 | `10` |
| `REQUEST_RETRIES` | 抓取重试次数 | `2` |
| `CANDIDATE_SAMPLE_SIZE` | 候选反馈页卡片数 | `8` |
| `RECOMMENDATION_LIMIT` | 推荐返回数量 | `5` |
| `ADAPTER_USER_AGENT` | 对外抓取时使用的 UA | `PornClaw/2.0 ...` |
| `PLAYWRIGHT_HEADLESS` | 是否启用无头浏览器 | `true` |

Telegram 官方 API 参数：

| Name | Purpose |
|---|---|
| `TELEGRAM_API_ID` | Telegram developer API ID |
| `TELEGRAM_API_HASH` | Telegram developer API hash |
| `TELEGRAM_SESSION_STRING` | Telethon StringSession，可选 |
| `TELEGRAM_SESSION_FILE` | Telethon session 文件路径，可选 |

说明：

- Telegram 二期使用的是 **Telethon + 官方客户端 API**，不是 Bot API。
- 你需要先登录 `https://my.telegram.org` 创建开发者应用，拿到 `api_id` / `api_hash`。
- 请求里只传 `credential_profile`，不会把明文凭证写进数据库。

## 支持矩阵背后的接入策略

PornClaw 二期不是“一个 adapter 通吃全部平台”，而是三层策略并存：

- `DemoSourceAdapter`
  - 保证零依赖演示可用
- `GenericTemplateAdapter`
  - 处理卡片流优先、列表流降级补全的站点
- `PornhubAdapter`
  - 专门处理 Pornhub 公开页面，优先走站点专用解析和浏览器抓取
- `TelegramChannelAdapter`
  - 通过 Telethon 读取公开频道消息流

统一流程仍然相同：

```text
source_url/source_type/context
  -> adapter registry 选择实际 adapter
  -> fetch recent items
  -> normalize
  -> aggregate by series
  -> recommend + explain
```

## 常用命令

### 初始化数据库

```bash
cd pornclaw
python scripts/init_db.py
```

### 启动开发服务器

```bash
cd pornclaw
uvicorn app.main:app --reload
```

### 运行测试

```bash
cd pornclaw
pytest
```

### 安装 Playwright 浏览器

```bash
cd pornclaw
python -m playwright install chromium
```

### Docker 启动

```bash
cd pornclaw
docker compose up --build
```

## API 概览

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | 首页表单 |
| `POST` | `/start` | 从网页启动完整流程 |
| `POST` | `/source/ingest` | 抓取并创建 session |
| `POST` | `/profile/create` | 创建/更新画像 |
| `POST` | `/recommend` | 生成推荐 |
| `POST` | `/feedback` | 提交反馈 |
| `GET` | `/candidate-feedback/{id}` | 候选反馈页 |
| `GET` | `/recommendations/{id}` | 推荐结果页 |

二期 ingest 输入现在至少支持：

- `source_url`
- `source_type`
- `context`

## 推荐打分仍然保持可解释

PornClaw 现在仍然是规则推荐，不是黑盒模型。

| 维度 | 计算方式 | 权重 |
|---|---|---|
| 新鲜度 | `5.0 - 0.5 × min(days_old, 10)` | 基础分 |
| 标签匹配 | 命中喜欢标签 / 不喜欢标签 | `+2.5 / -4.0` |
| 反馈相似度 | 与已反馈系列标签重合 | `+1.5 / -2.0` |
| 活跃度 | `min(7d_updates, 5) × 0.8` | 加分 |
| 多样性控制 | 与已喜欢系列标签过度重叠时轻惩罚 | `-0.3` |

## 当前状态

当前仓库已经进入第二阶段：

- 一期 demo 闭环保留
- 已支持多策略 adapter 框架
- 已支持：
  - demo
  - generic HTML template
  - Pornhub
  - Telegram public channel

仍然属于原型阶段，不包含：

- 多用户系统
- 云部署
- 私有 Telegram 群/邀请链接
- Pornhub 登录态和私有内容
- 复杂 ML 模型

## Project Structure

准备读代码时再看这一节。

```text
pornclaw/
├── app/
│   ├── adapters/      # 多策略 source adapters
│   ├── routes/        # 页面和 API 入口
│   ├── services/      # ingest/normalize/recommend 主逻辑
│   ├── models/        # SQLAlchemy 模型
│   ├── templates/     # 页面模板
│   └── static/        # 样式
├── tests/
├── scripts/
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Roadmap

- [ ] 把 generic template adapter 做成可配置模板库
- [ ] 给 Pornhub adapter 增加更稳的页面快照/录制测试
- [ ] 给 Telegram adapter 增加真实凭证集成测试
- [ ] 增加 cookies / proxy / header profile 支持
- [ ] 优化系列归并规则
- [ ] 继续打磨 README 和首次接入体验

## License

MIT
