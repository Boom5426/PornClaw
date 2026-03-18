<p align="center">
  <img src="assets/logo.svg" alt="PornClaw Logo" width="200" />
</p>

<h1 align="center">PornClaw</h1>

<p align="center">
  <b>Smart Series Recommendation Engine for Adult Content Sites</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green" />
</p>

---

PornClaw 是一个面向成人内容站点的系列推荐引擎原型。

它解决的是一个很具体的问题：用户给出一个内容站点 URL，系统抓取最近更新的内容，把零散条目归并成“系列”，结合用户标签偏好、自然语言偏好和交互反馈，给出可解释的 Top 5 推荐。

如果你是第一次打开这个仓库，先看下面这三件事就够了：

1. 进入 `pornclaw/`
2. 用 `demo://seed` 跑通完整流程
3. 打开浏览器看首页、候选反馈页和推荐结果页

## 这项目现在能做什么

- 输入一个数据源 URL
- 抓取最近内容并落库
- 标准化标签并聚合为系列
- 支持喜欢标签、不喜欢标签和一句自然语言偏好
- 支持候选反馈和推荐反馈
- 输出带理由的 Top 5 推荐
- 提供 API 和网页两种使用方式
- 内置 `demo://seed` 演示数据源，开箱即用

## 先看这里：最快跑起来

### 方式一：本地运行

```bash
cd pornclaw
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000`

首页默认已经填好了演示数据源 `demo://seed`，你直接点“抓取并开始推荐”就能体验完整闭环。

### 方式二：Docker

```bash
cd pornclaw
docker compose up --build
```

然后访问 `http://127.0.0.1:8000`

## 第一次使用时你会看到什么

完整流程是这样的：

1. 在首页输入 URL、喜欢标签、不喜欢标签和一句自然语言偏好
2. 系统抓取最近内容，并自动聚合成系列
3. 进入候选反馈页，对少量系列点“喜欢 / 不喜欢 / 跳过”
4. 系统生成 Top 5 推荐，并显示每条推荐理由
5. 你可以继续在推荐页点“喜欢这类 / 少推这类 / 不感兴趣”
6. 再次生成推荐时，上一轮反馈会影响排序

如果你只是想确认应用能不能跑：

- 数据源 URL 保持默认 `demo://seed`
- 随便勾两个喜欢标签
- 点“抓取并开始推荐”
- 候选页随便点几次反馈
- 进入推荐页看 Top 5 和理由

## Demo 数据源说明

为了保证新用户第一次运行就能成功，仓库内置了一个演示数据源：

- 使用方式：在首页填 `demo://seed`
- 作用：不依赖外部站点，也不依赖站点页面稳定性
- 内容：内置了 3 个演示系列，足够跑完整个推荐闭环

当前演示系列包括：

- `Campus Hearts`：romance, school, drama, longform
- `Sky Tale`：fantasy, soft, longform
- `Dark Dungeon`：dark, action, explicit

## 这个仓库怎么组织

这个仓库分成两层：

- 根目录：项目说明、资产文件、技能文档
- `pornclaw/`：真正的 Python Web 应用代码

如果你是来跑程序的，主要关注 `pornclaw/`

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

### Docker 启动

```bash
cd pornclaw
docker compose up --build
```

## 对外接口

除了网页页面，项目也提供后端接口，便于后续接前端或自动化脚本：

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | 首页表单 |
| `POST` | `/start` | 从网页启动完整流程 |
| `GET` | `/candidate-feedback/{id}` | 候选反馈页 |
| `GET` | `/recommendations/{id}` | 推荐结果页 |
| `POST` | `/source/ingest` | 抓取并创建 session |
| `POST` | `/profile/create` | 创建或更新用户画像 |
| `POST` | `/recommend` | 生成推荐结果 |
| `POST` | `/feedback` | 提交反馈 |

## 核心流程

```text
用户输入 URL + 标签偏好 + 自然语言偏好
  → Source Adapter 抓取最近条目
  → Normalize 清洗标题 / 标签
  → Aggregate 聚合为系列
  → 候选反馈补充用户画像
  → Recommend 多维度加权评分
  → Explain 生成推荐理由
  → 推荐结果页反馈 → 影响下一轮排序
```

## 推荐是怎么打分的

当前是第一阶段原型，所以推荐逻辑刻意保持可解释、可调试，不使用黑盒模型。

| 维度 | 计算方式 | 权重 |
|------|---------|------|
| 新鲜度 | `5.0 - 0.5 × min(days_old, 10)` | 基础分 |
| 标签匹配 | 命中喜欢标签 / 不喜欢标签 | `+2.5 / -4.0` |
| 反馈相似度 | 与已反馈喜欢/不喜欢系列的标签重合 | `+1.5 / -2.0` |
| 活跃度 | `min(7d_updates, 5) × 0.8` | 加分 |
| 多样性控制 | 与已喜欢系列标签过于重叠时轻微惩罚 | `-0.3` |

每条推荐都会保存评分拆解和理由文本，方便调试和解释。

## 技术栈

| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI 0.115 |
| Server | Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite |
| Templating | Jinja2 |
| HTML Parsing | BeautifulSoup4 |
| Testing | pytest + httpx |
| Container | Docker Compose |

## Project Structure

只有在你准备看代码时，这一节才需要仔细读。

```text
pornclaw/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 配置和标签映射
│   ├── db.py                      # 数据库初始化
│   ├── models/                    # SQLAlchemy ORM 模型
│   ├── services/                  # 核心业务逻辑
│   │   ├── ingest.py              # 抓取入库编排
│   │   ├── normalize.py           # 标签与标题清洗
│   │   ├── aggregate.py           # 系列聚合
│   │   ├── profile.py             # 用户画像
│   │   ├── recommend.py           # 评分与排序
│   │   ├── explain.py             # 推荐理由生成
│   │   └── preference_parser.py   # 自然语言偏好解析
│   ├── adapters/                  # 数据源适配器
│   ├── routes/                    # HTTP 路由
│   ├── templates/                 # Jinja2 模板
│   ├── static/                    # CSS
│   └── utils/                     # 通用工具
├── tests/                         # 最小测试集
├── scripts/init_db.py             # 数据库初始化脚本
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 当前状态

这个项目目前是“第一阶段闭环原型”：

- 重点是证明产品方向能跑通
- 优先本地可运行、逻辑清晰、推荐可解释
- 还没有做复杂模型、多用户系统、云部署或多站点并行抓取

## Roadmap

- [ ] 扩展成更稳的真实站点模板适配器
- [ ] 增加更多 Source Adapter
- [ ] 优化系列归并规则
- [ ] 增加更多测试覆盖
- [ ] 优化 README 和首次体验
- [ ] 引入更细的多样性控制和召回策略

## License

MIT
