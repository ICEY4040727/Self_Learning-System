# 协作规范

## 角色分工

| 角色         | 负责人             | 职责                                                               |
| ------------ | ------------------ | ------------------------------------------------------------------ |
| **Owner**    | 项目负责人（人类） | 最终决策、合并 PR、确定优先级、审查、验收                                      |
| **Agent**  | Claude Code        | 在现有框架内实现功能，产出代码（分支、提交、PR）、修复bug，技术调研、回复审查意见                 |


## 任务管理

**以 GitHub Issues 为主，仓库文档各版本执行记录markdown文件为辅。**

### Issue 模板

```markdown
### 标题

[简洁描述]

### 背景

[为什么需要这个功能/修复]

### 验收标准

- [ ] 条件 1
- [ ] 条件 2

### 技术说明

- 涉及模块：frontend / backend / both
- 数据库变更：是 / 否
- 依赖任务：#N 或无

### 优先级：P0 / P1 / P2

### 对应单元测试及测试通过情况与报错详情
```

### Labels

| Label          | 用途               |
| -------------- | ------------------ |
| `feature`      | 新功能             |
| `bugfix`       | Bug 修复           |
| `research`     | 技术调研/提案      |
| `P0`           | 紧急               |
| `P1`           | 重要               |
| `P2`           | 一般               |
| `approved`     | Owner 已批准，可开始开发       |
| `needs-review` | Agent提交pr后待 Owner 审查   |

### 状态流转

```
Owner创建Issue → Owner 标记 approved
  → Agent 读取 Issue 及所有评论，理解完整上下文
    → 开发并提交 PR（关联 Issue，标记 needs-review，@仓库拥有者）
      → 我审查pr， 在pr中提出修改意见
        → Agent 阅读审查意见，写文档总结本次问题详情，owner 赞同该详情总结后，进行对问题的修复并再次回复@owner
          → Owner 重新审查，若通过则合并，若不通过则提出修改意见。
```

## 协作边界

### Agent 独立执行（事后交 Owner 审查）

- 现有模块内新增/修改功能
- Bug 修复
- UI 样式和交互微调
-- 文档更新

### 必须先写方案，等 Owner 审视后再动手

- 数据库 schema 变更
- 架构级改动（新中间件、路由重组、ChromaDB 策略调整）
- 跨 3 个以上文件的结构性重构
- 有多种合理方案的技术选型

方案格式："方案 A vs 方案 B"，列出各自 trade-off，方便Owner决策


## Git 规范

### 分支命名

- `feat/#N-描述` — 新功能
- `fix/#N-描述` — Bug 修复
- `docs/描述` — 文档
- `refactor/描述` — 重构

### Commit 格式

遵循 Conventional Commits：`feat:`, `fix:`, `docs:`, `refactor:`, `test:`

### PR 规范

- **单一职责**：一个 PR 只做一件事
- **体量控制**：尽量 300 行以内
- **关联 Issue（可选）**：有 tracking issue 时在 PR 中写 `Closes #N`；小步 seam PR 可不建 issue
- **PR 描述包含**：
  - 变更概述
  - 改动清单（文件 + 说明）
  - 自查清单
  - 需要Owner重点审查的部分

### User LLM 设置写入规范（强制）

`users` 表 LLM 相关字段存在 JSON 主存储 + Legacy 列双写；**业务层禁止直接 ORM 赋值**，否则双写同步会被跳过，JSON 与 Legacy 分叉。

**受管字段**

| 字段 | 写入入口 |
| --- | --- |
| `default_provider`, `encrypted_api_key`, `model`, `llm_base_url`, `llm_provider_settings` | `backend.services.user_llm_settings.update_provider_settings()` |
| `temperature`, `max_tokens` | `backend.services.user_llm_settings.update_generation_params()` |

**强制约定**

1. 业务路由、Service、离线脚本、数据修复脚本 **不得** 出现 `user.xxx = ...` / `current_user.xxx = ...` 对上述字段的直接赋值。
2. 读取统一走 `get_effective_llm_config()` / `serialize_provider_settings()`；Legacy 列不得作为运行时数据源。
3. 离线脚本与数据修复脚本必须封装为可执行入口（如 `python -m backend.scripts.repair_user_llm_settings`），内部复用上述 write gateway；禁止手写 ORM 批量 `UPDATE`。
4. 测试代码（`backend/tests/`）可为 fixture 直接赋值；生产代码与 `scripts/` 不在豁免范围。

**唯一写网关**

`backend/services/user_llm_settings.py`（内部自动进入 `authorized_user_llm_write()` 授权上下文）

**运行时兜底**

`backend/services/user_llm_write_guard.py` 在 ORM 层拦截未授权的 User LLM 字段写入（列级 set 监听 + ORM bulk update）。生产环境默认启用；测试环境 `TESTING=1` 时关闭以便 fixture 直写。

**本地卡点**

```bash
python scripts/check_user_llm_direct_writes.py
```

基于 AST 扫描（非行级正则），可检测多行拆分赋值、括号包裹基对象、以及 `u = user; u.field = ...` 别名链。已接入 pre-commit；CI 在 lint job 中运行同一命令。

**Code Review 检查项（出现即 request changes）**

- [ ] 业务层 / 脚本是否直接赋值 User LLM 字段？
- [ ] 新增离线脚本是否复用 `update_provider_settings` / `update_generation_params`？
- [ ] 是否绕过 write gateway 直接 `db.commit()`？

**数据修复脚本模板**

参考 `backend/scripts/dba_user_llm_runner.py`（强制 `--staging-validated`，执行后自动 JSON/legacy 巡检）。

**数据库侧兜底（PostgreSQL / SQLite）**

- Alembic `2026_06_20_001`：禁止 legacy 镜像列单独 UPDATE，JSON 变更时自动同步 legacy
- PostgreSQL 生产角色：`backend/db/postgres/user_llm_roles.sql`
- PostgreSQL 审计表：`backend/db/postgres/user_llm_audit.sql`（记录 legacy-only UPDATE、关联 `app.user_llm_write_trace`）
- 巡检：`python -m backend.scripts.audit_user_llm_consistency_job --sql --fail-on-issues`
- 定时巡检（Docker Compose `user-llm-patrol` 服务，默认 03:00 + 自动修复）：`--sql --repair --fail-on-issues`
- 仅扫描：`python -m backend.scripts.audit_user_llm_consistency_job --sql --dry-run --fail-on-issues`

**可观测性（日志检索）**

| 标记 | 含义 |
| --- | --- |
| `USER_LLM_WRITE` | 经 write gateway 的正常双写（含 `trace_id` / `dual_write=true`） |
| `USER_LLM_WRITE_BLOCKED` | 裸写被 ORM 钩子拦截（无 gateway 标记） |
| `USER_LLM_SETTINGS_CONFLICT` | 乐观锁 409 冲突（并发 PUT 版本过期） |
| `USER_LLM_READ_HEAL` | 读侧 Legacy 回填：`legacy_backfill_read` / `legacy_backfill_persist` |
| `USER_LLM_AUDIT` | 定时/SQL 巡检；`event=patrol_metrics` 汇总脏数据与回填候选量 |

```bash
rg "USER_LLM_WRITE" logs/               # 正常入口
rg "USER_LLM_WRITE_BLOCKED" logs/       # 可疑裸写（需整改）
rg "USER_LLM_SETTINGS_CONFLICT" logs/   # 并发冲突压力
rg "USER_LLM_READ_HEAL" logs/           # 读侧回填 / 自动固化进度
rg "USER_LLM_AUDIT" logs/               # 巡检与告警
```

**CI / 测试分层**

| 阶段 | 命令 / 工作流 | 说明 |
| --- | --- | --- |
| pre-commit | `python scripts/check_user_llm_direct_writes.py` | 本地提交拦截裸写 |
| CI lint | 同上 | 失败阻断合并 |
| CI `user-llm-unit` | `pytest tests/user_llm/ --ignore=tests/user_llm/test_risk3_stress.py` + `PYTEST_FAIL_ON_SKIP=1` | 四大风险专项 + 契约，不允许 skip |
| 夜间 stress | `.github/workflows/user-llm-stress.yml` + `USER_LLM_STRESS=1` | 10 线程并发 + PostgreSQL 触发器 |
| 夜间 patrol | `.github/workflows/user-llm-patrol.yml` / Docker `user-llm-patrol` | 一致性巡检 + 自动修复 + 飞书告警 |

应用写 gateway 时会在 PostgreSQL 会话写入 `SET LOCAL app.user_llm_write_trace=<trace_id>`，可与 `app.user_llm_update_audit` 表关联溯源。

### PR Review 对话流程

PR 的 review 是 Owner 和 Agent 通过 PR comments 进行的持续对话，直到 Reviewer 确认可以合并：

```
Agent 提交 PR，标记 needs-review，并通过对话通知我。
  → Owner 审查，在 PR comment 中列出问题和建议
    → Creator 读 PR comments（gh pr view N --comments）
      → Creator 理解每项反馈的意图和背景
        → Agent 修复代码并推送
          → Agent 在 PR comment 中回复修复内容（逐项对应）
            → Reviewer re-review
              → 通过 → 合并 / 仍有问题 → 继续对话
```

**Agent 回复格式：**

```markdown
## Agent 修复回复

已修复 Reviewer 提出的 N 项问题：

| #   | 问题       | 修复       |
| --- | ---------- | ---------- |
| 1   | [问题描述] | [修复说明] |
| 2   | [问题描述] | [修复说明] |

请 re-review。
```

**关键规则：**

- Agent 修复后**必须在 PR comment 中回复**，说明每项修改内容，供 Reviewer 对照审查
- 不得只推送代码不回复——Reviewer 需要知道哪些改了、哪些没改、为什么
- 如果对某项建议有不同意见，在 comment 中说明理由，而非静默忽略
- 通过 `tmux send-keys` 通知对方有新 comment，避免等待

## 实时通信：tmux 跨 Session 通知

Agent 和 Reviewer 运行在独立的 tmux session 中，三方共用同一个 GitHub 账号，**GitHub 原生通知无效**（自己评论自己的 PR 不会触发通知）。因此需要 tmux 机制来实现实时通信。

### tmux Session 架构

```
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ Agent-1 (组:Agent) │  │ reviewer-0 (组:reviewer) │  │ gh-notify            │
│ (Agent 工作区)      │  │ (Reviewer 工作区)     │  │ (通知守护脚本)        │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

> **重要**: Session 名称可能动态变化 (如 Agent-1, Agent-2)，但组名固定。**优先使用组名**。

### 手动通知命令

当需要立即通知对方时（不等待守护脚本轮询），使用 `tmux send-keys`：

**Agent → Reviewer（如：PR 修复完成、需要重新审查）**

```bash
# 推荐：使用组名（稳定）
tmux send-keys -t reviewer "[Agent 通知] PR #9 已修复 Reviewer 提出的问题，请重新审查。" Enter

# 或使用具体 session 名称
tmux send-keys -t reviewer-0 "[Agent 通知] PR #9 已修复 Reviewer 提出的问题，请重新审查。" Enter
```

**Reviewer → Creator（如：审查完成、发现紧急 Bug）**

```bash
# 推荐：使用组名（稳定）
tmux send-keys -t creator "[Reviewer 通知] PR #9 审查完成，有 2 个必须修复的问题，详见 PR comment。" Enter

# 或使用具体 session 名称
tmux send-keys -t creator-1 "[Reviewer 通知] PR #9 审查完成，有 2 个必须修复的问题，详见 PR comment。" Enter
```

**注意事项：**

- 发送前**必须检查对方是否空闲**，避免打断正在进行的对话：
  ```bash
  # 检查空闲：末尾显示 ❯ 表示等待输入（使用组名）
  tmux capture-pane -t creator -p | grep -v '^$' | tail -1
  tmux capture-pane -t reviewer -p | grep -v '^$' | tail -1
  ```
- 如果对方**忙碌**（正在输出或思考），等待或记录到队列文件：
  ```bash
  echo "[通知内容]" >> /tmp/gh-notify/queue_reviewer.txt
  echo "[通知内容]" >> /tmp/gh-notify/queue_creator.txt
  ```
- 消息格式统一前缀 `[Creator 通知]` 或 `[Reviewer 通知]`，便于识别来源

### 通知触发时机

| 场景                            | 谁通知谁            | 方式                  |
| ------------------------------- | ------------------- | --------------------- |
| Reviewer 完成 PR 审查           | Reviewer → Creator  | 手动 `tmux send-keys` |
| Creator 修复 PR 问题后          | Creator → Reviewer  | 手动 `tmux send-keys` |
| Owner 给 Issue 标 `approved`    | 守护脚本 → Creator  | 自动（5 分钟内）      |
| Creator 开 PR 标 `needs-review` | 守护脚本 → Reviewer | 自动（5 分钟内）      |
| Reviewer 创建新 Issue           | 守护脚本 → Reviewer | 自动（确认收录）      |

### 自动通知守护脚本

`scripts/gh-notify-daemon.sh` 在独立 tmux session 中运行，每 5 分钟轮询 GitHub：

```bash
# 启动
tmux new-session -d -s gh-notify "bash scripts/gh-notify-daemon.sh"

# 查看日志
tmux attach -t gh-notify

# 停止
tmux kill-session -t gh-notify
```

可通过环境变量配置：

| 变量               | 默认值                             | 说明                  |
| ------------------ | ---------------------------------- | --------------------- |
| `POLL_INTERVAL`    | `300`                              | 轮询间隔（秒）        |
| `REPO`             | `ICEY4040727/Self_Learning-System` | 目标仓库              |
| `CREATOR_SESSION`  | `creator`                          | Creator tmux 组名     |
| `REVIEWER_SESSION` | `reviewer`                          | Reviewer tmux 组名    |

### 空闲检测原理

Claude Code 等待输入时，pane 末尾显示 `❯`。守护脚本通过 `tmux capture-pane` 检测此特征判断是否空闲：

- **空闲** → 立即通过 `tmux send-keys` 发送通知
- **忙碌** → 写入队列文件 `/tmp/gh-notify/queue_*.txt`，下次轮询时补发
- **积压 >3 条** → 合并为一条摘要通知，防止刷屏

## Creator 工作流程

### 接手任务时

1. **读 Issue 全文**：包括描述、验收标准、技术说明
2. **读 Issue 的所有 comments**：Reviewer/Owner 可能在 comment 中补充了方案建议、技术选型偏好、注意事项
3. 理解完整上下文后再开始编码

### 处理 PR Review 反馈时

1. **先读 PR 的所有 comments**：`gh pr view N --comments`
2. **理解 Reviewer 的意图**：Reviewer 提出建议时通常给出了理由和多种选项，不要不加思考地选最简单的
3. **做出有依据的选择**：如果 Reviewer 提供了 A/B 方案，思考哪个对项目更有价值再决定，而非默认删除或跳过
4. 修复后推送，等待 re-review

### 绝对禁止

- **不得直接推送到 main**：任何改动都必须走分支 + PR 流程，没有例外
- **不得未读 comment 就修改**：Issue/PR 的 comment 是协作的核心上下文

## 设计先行

非平凡功能的流程：

```
Reviewer 技术调研（推荐方案 + 参考实现 + 已知坑点）
  → Creator 写简短技术方案
    → Owner 确认
      → Creator 开发
```
