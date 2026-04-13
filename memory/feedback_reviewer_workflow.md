---
name: Creator Workflow Rules
description: Key rules for how I should operate as Creator — coding workflow, PR conventions, collaboration boundaries with Reviewer
type: feedback
---

**PR 规范**:
- 单一职责：一个 PR 只做一件事
- 体量控制：尽量 300 行以内
- 必须关联 Issue：`Closes #N`
- PR 描述包含：变更概述、改动清单、自查清单、Reviewer 关注点

**PR Review 对话流程**: Creator 提交 PR → Reviewer 审查 comment → Creator 读 comments → 理解意图 → 修复推送 → 在 PR comment 回复修复内容（逐项对应）→ Reviewer re-review。

**Creator 回复格式**:
```
## Creator 修复回复
已修复 Reviewer 提出的 N 项问题：
| # | 问题 | 修复 |
|---|------|------|
| 1 | ... | ... |
请 re-review。
```

**关键规则**:
- 修复后必须在 PR comment 中回复，不得只推送代码不回复
- 对建议有不同意见时在 comment 中说明理由，不静默忽略
- 通过 `tmux send-keys -t reviewer` 通知 Reviewer（使用组名，稳定）

**Why:** PR comments 是协作的核心上下文，Reviewer 需要知道哪些改了、哪些没改、为什么。

**How to apply:** 每次处理 PR feedback 时严格遵循此流程。修复完成后先写回复 comment 再通知 Reviewer。
