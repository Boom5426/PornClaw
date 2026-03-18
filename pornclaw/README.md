# PornClaw App

`pornclaw/` 是这个仓库里真正的 Python Web 应用目录。

如果你是第一次跑项目，建议先用 `demo://seed` 走通闭环；如果你要接真实平台，再看下面的 adapter 分类和环境变量说明。

## 第二阶段能力

第二阶段不再把“数据源接入”理解成一个单一 HTML parser，而是分成多种 adapter：

- `demo`
  - 内置假数据，保证零依赖演示
- `generic_template`
  - 处理普通 HTML 内容站点
  - 支持卡片流优先、列表流降级补字段
- `pornhub`
  - 专门适配 Pornhub 公开页面
  - 优先走站点专用解析，必要时浏览器抓取
- `telegram`
  - 通过 Telethon 读取 Telegram 公开频道

## 支持的输入格式

| Adapter | 输入示例 |
|---|---|
| `demo` | `demo://seed` |
| `generic_template` | `https://example.com/feed` |
| `pornhub` | `https://www.pornhub.com/model/<name>/videos` |
| `telegram` | `https://t.me/<public_channel_name>` |

Telegram 当前只支持公开频道根地址，不支持：

- `t.me/+...`
- `joinchat`
- `t.me/c/...`
- 私有群
- Bot API 模式

## 运行时约束

- `demo` 只接受 `demo://...`，不会再把任意 `http/https` 页面按 demo source 抓取。
- `generic_template` 只处理普通 `http/https` 页面；显式指定 adapter 时，URL 也必须满足该 adapter 自己的校验。
- `pornhub` 只接受真实 `pornhub.com` 或其子域名，不接受仅仅“字符串后缀像 pornhub”的域名。
- `telegram` 只接受 `https://t.me/<username>` / `https://telegram.me/<username>` 这类公开频道地址。
- 反馈要求 `series_id` 必须属于当前 `session_id`，跨 session 的反馈会被拒绝。
- 所有发布时间在进入聚合和推荐前都会先归一化，避免时区时间和无时区时间混用导致排序或打分异常。

## Adapter 是怎么被选中的

流程如下：

```text
source_url + source_type + context
  -> adapter registry
  -> 选择 Demo / GenericTemplate / Pornhub / Telegram
  -> 抓取 recent items
  -> normalize
  -> aggregate
  -> recommend
```

其中：

- `source_type=auto` 会根据 URL 域名自动猜
- `source_type` 显式指定时，会优先走对应 adapter
- `context` 用来传非敏感配置，例如：
  - `credential_profile`
  - `max_items`
  - `fetch_detail_pages`

## 本地运行

### Demo 模式

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload
```

浏览器打开 `http://127.0.0.1:8000`，保持默认 `demo://seed` 即可。

### 真实平台模式

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python scripts/init_db.py
uvicorn app.main:app --reload
```

## 环境变量

基础运行参数：

- `DATABASE_URL`
- `SECRET_KEY`
- `REQUEST_TIMEOUT_SECONDS`
- `REQUEST_RETRIES`
- `CANDIDATE_SAMPLE_SIZE`
- `RECOMMENDATION_LIMIT`
- `ADAPTER_USER_AGENT`
- `PLAYWRIGHT_HEADLESS`

Telegram 官方 API：

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION_STRING`
- `TELEGRAM_SESSION_FILE`

说明：

- Telegram 二期用的是 **官方客户端 API + Telethon**
- 不会把明文凭证直接从前端提交到数据库
- 前端/接口只提交 `credential_profile`

## Supported Adapters

### DemoSourceAdapter

- 读取内置 HTML
- 永远可用
- 用于开发和演示基线

### GenericTemplateAdapter

- 处理常见外部 HTML 列表页
- 如果列表页字段不够，可以回详情页补全
- 适合“结构相对常规”的内容站点

### PornhubAdapter

- 处理公开 Pornhub 页面
- 支持基于列表页提取最近内容
- 优先使用专用 parser，而不是依赖 generic template 猜结构

### TelegramChannelAdapter

- 处理公开 Telegram 频道
- 将消息流映射成内部 raw items
- 默认按频道名聚合为系列

## 如何新增一个模板 adapter

如果你要接一个新的 HTML 站点，建议先走 generic template 路线，而不是直接写一个重量级专用 adapter。

最小步骤：

1. 确认列表页能否拿到标题和链接
2. 判断它是卡片流还是列表流
3. 确认是否需要详情页补字段
4. 保证最终输出统一字段：
   - `source_id`
   - `title`
   - `detail_url`
   - `cover_url`
   - `publish_time`
   - `author_or_group`
   - `tags_raw`
   - `description_raw`
   - `series_name_raw`
   - `chapter_or_episode_raw`
5. 给它补一个 fixture 测试

## Troubleshooting

### 数据源 URL 非法

- 检查 `source_type` 是否和 URL 对得上
- `demo` 只能用 `demo://...`
- `pornhub` 必须是 `pornhub.com` 或其子域名
- Telegram 只支持 `https://t.me/<username>`

### 抓取为空

- 站点结构可能变化
- generic template 可能需要开启 `fetch_detail_pages`
- Pornhub 页面可能需要浏览器抓取路径

### Telegram 凭证错误

- 检查 `TELEGRAM_API_ID`
- 检查 `TELEGRAM_API_HASH`
- 检查 `TELEGRAM_SESSION_STRING` 或 `TELEGRAM_SESSION_FILE`
- 确认你访问的是公开频道

### 页面结构变化

- generic template 依赖常见 HTML 模式
- 结构变化后应补 fixture，再调整选择器或专用 adapter

### 网络 / 超时

- 调高 `REQUEST_TIMEOUT_SECONDS`
- 检查目标站点是否可访问
- 对需要浏览器抓取的站点确认 Chromium 已安装

### 反馈提交失败

- 检查当前提交的 `series_id` 是否来自同一个 `session_id`
- 未知 `feedback_type` 会在 API 层直接被拒绝

## 测试

```bash
pytest
```

当前最重要的测试覆盖：

- adapter registry 选路
- generic template 的卡片流/列表流解析
- Pornhub parser 基于 fixture 的提取
- Telegram 消息到 raw item 的映射
- 二期 ingest schema
