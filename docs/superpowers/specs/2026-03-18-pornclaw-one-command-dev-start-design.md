# PornClaw One-Command Dev Start Design

**Goal**

把本地开发启动流程从多条手工命令压缩成一条仓库根目录命令：`python dev.py`。这个入口需要覆盖第一次启动的环境准备，同时保持后续重复运行足够快，并继续保留现有手动命令作为备用路径。

**Chosen Direction**

采用仓库根目录的 `dev.py` 作为唯一推荐入口。

- 用户不再需要先 `cd pornclaw`
- 入口不依赖 `bash`、`make` 或 `just`
- Windows、Linux、macOS 都能直接用 `python dev.py`
- 脚本负责把当前工作目录和命令都切换到 `pornclaw/` 语境中执行

相比 `make dev`，这个方案的跨平台摩擦更小。相比只在 `pornclaw/scripts/` 下加脚本，这个方案对第一次打开仓库的人更直接。

**Architecture**

新增仓库根目录文件 `dev.py`，它只负责“开发启动编排”，不承载业务逻辑。实际应用结构仍然保持现在的 FastAPI monolith，不改 `app.main:app`、数据库模型、路由或推荐逻辑。

`dev.py` 的固定执行顺序如下：

1. 解析仓库根目录与 `pornclaw/` 目录
2. 检查并创建 `pornclaw/.venv`
3. 使用 `pornclaw/.venv` 里的 Python 解释器执行后续所有命令
4. 在需要时安装 `pornclaw/requirements.txt`
5. 运行 `python scripts/init_db.py`
6. 在需要时尝试安装 Playwright Chromium
7. 启动 `uvicorn app.main:app --reload`

这个脚本需要是幂等的：已经准备好的环境不会被重复破坏，只会在必要时补齐缺失步骤。

**Bootstrap Rules**

为了避免“每次启动都重新装依赖”，脚本应维护两个轻量状态：

- Python 依赖安装状态
- Playwright Chromium 安装状态

推荐做法：

- 依赖部分基于 `requirements.txt` 内容哈希做失效判断
  - 第一次启动时安装依赖
  - 之后只有 `requirements.txt` 变化时才重新执行 `pip install -r requirements.txt`
- Playwright 部分采用“首次自动安装”策略
  - 默认尝试安装 Chromium
  - 成功后写入 repo-local 标记
  - 后续启动跳过该步骤

这样可以同时满足：

- 第一次启动足够省心
- 后续启动不会因为重复安装依赖而变慢

**Playwright Behavior**

Playwright 对 Pornhub 浏览器抓取路径有价值，但不是 demo 流程的必要条件。因此浏览器安装采用“默认自动尝试，但失败不阻断 demo 启动”的策略。

具体规则：

- 默认行为：首次运行时自动执行 `python -m playwright install chromium`
- 如果安装成功：写入安装标记，后续直接跳过
- 如果安装失败：
  - 打印明确 warning
  - 继续启动应用
  - 告诉用户 Pornhub / 浏览器依赖路径可能不可用
- 提供 `--skip-playwright` 逃生参数，用于网络差、离线或只跑 demo 的场景

这个取舍的核心是：启动体验优先，而不是把所有首次准备失败都升级成致命错误。

**CLI Surface**

推荐先只暴露一个主命令和一个逃生参数：

```bash
python dev.py
python dev.py --skip-playwright
```

不在这一版加入更多控制参数，如自定义 host、port、reload 开关。当前目标是把“开发启动入口”简化为稳定的一条命令，而不是把它演化成完整的进程管理器。

**Console Output**

脚本应输出明确、低噪音的阶段信息，例如：

- `Ensuring virtual environment`
- `Installing Python dependencies`
- `Initializing database`
- `Ensuring Playwright Chromium`
- `Starting development server`

如果某一步失败，输出中应带上：

- 实际执行的命令
- 非零退出码
- 下一步建议

这样用户不用猜卡在哪一环。

**Files**

- Create: `dev.py`
  - 仓库根目录的一键启动入口
- Modify: `README.md`
  - 仓库根 README 改为主推 `python dev.py`
- Modify: `pornclaw/README.md`
  - 应用级 README 同步主入口和 fallback 手动命令
- Modify: `pornclaw/tests/conftest.py` or add a new test module helper if needed
  - 让测试能导入根目录 `dev.py`
- Create: `pornclaw/tests/test_dev_entry.py`
  - 覆盖脚本的核心分支与幂等逻辑

**Testing**

需要覆盖的测试重点：

1. 已存在 `.venv` 时不会重复创建环境
2. `requirements.txt` 未变化时不会重复执行 `pip install`
3. `requirements.txt` 变化时会重新安装依赖
4. `--skip-playwright` 会跳过浏览器安装步骤
5. Playwright 安装失败时会给 warning，但不会阻止开发服务器启动分支
6. 命令构造始终使用 `pornclaw/.venv` 里的 Python，而不是系统 Python

测试应尽量以函数级别进行，通过 mock/subprocess monkeypatch 验证命令编排，而不是在测试中真的创建 venv 或安装浏览器。

**README Changes**

README 应改成下面这种信息结构：

主路径：

```bash
python dev.py
```

说明：

- 第一次运行会自动准备 `.venv`、安装依赖、初始化数据库
- 首次会尝试安装 Chromium；若失败会给 warning，但 demo 流程仍可继续

备用手动路径：

- 保留当前详细命令块
- 作为 troubleshooting / manual setup 段落出现

**Non-Goals**

- 不替代 Docker 启动方式
- 不做生产部署入口
- 不在这一版引入 `make`、`just`、`uv` 等额外工具依赖
- 不把启动脚本扩展成复杂的多命令 CLI

**Success Criteria**

以下条件同时满足时，设计算完成：

1. 新用户在仓库根目录执行 `python dev.py` 可以启动项目
2. 第二次启动不会重复执行重型初始化步骤
3. 没装 Playwright Chromium 时，脚本会尽量自动补齐
4. Chromium 安装失败不会阻断 demo 路线
5. README 主路径缩短为一条命令
