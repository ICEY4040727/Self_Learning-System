# 协作规范

## 角色分工

| 角色         | 负责人             | 职责                                                               |
| ------------ | ------------------ | ------------------------------------------------------------------ |
| **Owner**    | 项目负责人（人类） | 最终决策、合并 PR、确定优先级                                      |
| **Creator**  | Claude Code        | 在现有框架内实现功能，产出是代码（分支、提交、PR）                 |
| **Reviewer** | Claude Code        | 审查代码 → 找 Bug → 搜索前沿资料，产出是报告和提案（不写实现代码） |

## 任务管理

**以 GitHub Issues 为主，仓库文件为辅。**

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
```

### Labels

| Label          | 用途               |
| -------------- | ------------------ |
| `feature`      | 新功能             |
| `bugfix`       | Bug 修复           |
| `research`     | 技术调研/提案      |
| `creator`      | Creator 负责实现   |
| `reviewer`     | Reviewer 提出/负责 |
| `P0`           | 紧急               |
| `P1`           | 重要               |
| `P2`           | 一般               |
| `approved`     | Owner 已批准       |
| `needs-review` | 待 Reviewer 审查   |

### 状态流转

```
Issue 创建 → Owner 标记 approved
  → Creator 接手开发
    → 提交 PR（关联 Issue，标记 needs-review）
      → PR 中 @reviewer 触发审查
        → Reviewer approve / request changes
          → Owner 合并
```

## 协作边界

### Creator 独立执行（事后交 Reviewer 审查）

- 现有模块内新增/修改功能
- Bug 修复
- UI 样式和交互微调

### Creator 先写方案，等 Reviewer 审视后再动手

- 数据库 schema 变更
- 架构级改动（新中间件、路由重组、ChromaDB 策略调整）
- 跨 3 个以上文件的结构性重构
- 有多种合理方案的技术选型

方案格式："方案 A vs 方案 B"，列出各自 trade-off。

### Reviewer 工作优先级

1. 有新 PR → 代码审查
2. 无新 PR → 排查现有代码 Bug，提交 Issue（`bugfix` + `reviewer`）
3. 无 Bug → 前沿调研，提交提案 Issue（`research` + `reviewer`）

Reviewer 审查代理规范：见 [.github/agents/reviewer-pr-auditor.agent.md](.github/agents/reviewer-pr-auditor.agent.md)

### 分歧处理

Creator 和 Reviewer 各自在 Issue 中陈述理由，Owner 最终裁决。

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
- **必须关联 Issue**：`Closes #N`
- **禁止只写**：`Related to #N`（不会自动闭合 issue）
- **PR 描述包含**：
  - 变更概述
  - 改动清单（文件 + 说明）
  - 自查清单
  - Reviewer 关注点

### PR Review 对话流程

PR 的 review 是 Creator 和 Reviewer 通过 PR comments 进行的持续对话，直到 Reviewer 确认可以合并：

```
Creator 提交 PR
  → Reviewer 审查，在 PR comment 中列出问题和建议
    → Creator 读 PR comments（gh pr view N --comments）
      → Creator 理解每项反馈的意图和背景
        → Creator 修复代码并推送
          → Creator 在 PR comment 中回复修复内容（逐项对应）
            → Reviewer re-review
              → 通过 → 合并 / 仍有问题 → 继续对话
```

**Creator 回复格式：**

```markdown
## Creator 修复回复

已修复 Reviewer 提出的 N 项问题：

| #   | 问题       | 修复       |
| --- | ---------- | ---------- |
| 1   | [问题描述] | [修复说明] |
| 2   | [问题描述] | [修复说明] |

请 re-review。
```

**关键规则：**

- Creator 修复后**必须在 PR comment 中回复**，说明每项修改内容，供 Reviewer 对照审查
- 不得只推送代码不回复——Reviewer 需要知道哪些改了、哪些没改、为什么
- 如果对某项建议有不同意见，在 comment 中说明理由，而非静默忽略
- 通过 `tmux send-keys` 通知对方有新 comment，避免等待

## 实时通信：tmux 跨 Session 通知

Creator 和 Reviewer 运行在独立的 tmux session 中，三方共用同一个 GitHub 账号，**GitHub 原生通知无效**（自己评论自己的 PR 不会触发通知）。因此需要 tmux 机制来实现实时通信。

### tmux Session 架构

```
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ creator-1 (组:creator) │  │ reviewer-0 (组:reviewer) │  │ gh-notify            │
│ (Creator 工作区)      │  │ (Reviewer 工作区)     │  │ (通知守护脚本)        │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

> **重要**: Session 名称可能动态变化 (如 creator-1, creator-2)，但组名固定。**优先使用组名**。

### 手动通知命令

当需要立即通知对方时（不等待守护脚本轮询），使用 `tmux send-keys`：

**Creator → Reviewer（如：PR 修复完成、需要重新审查）**

```bash
# 推荐：使用组名（稳定）
tmux send-keys -t reviewer "[Creator 通知] PR #9 已修复 Reviewer 提出的问题，请重新审查。" Enter

# 或使用具体 session 名称
tmux send-keys -t reviewer-0 "[Creator 通知] PR #9 已修复 Reviewer 提出的问题，请重新审查。" Enter
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
