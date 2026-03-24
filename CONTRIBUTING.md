# 协作规范

## 角色分工

| 角色 | 负责人 | 职责 |
|------|--------|------|
| **Owner** | 项目负责人（人类） | 最终决策、合并 PR、确定优先级 |
| **Creator** | Claude Code | 在现有框架内实现功能，产出是代码（分支、提交、PR） |
| **Reviewer** | Claude Code | 审查代码 → 找 Bug → 搜索前沿资料，产出是报告和提案（不写实现代码） |

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

| Label | 用途 |
|-------|------|
| `feature` | 新功能 |
| `bugfix` | Bug 修复 |
| `research` | 技术调研/提案 |
| `creator` | Creator 负责实现 |
| `reviewer` | Reviewer 提出/负责 |
| `P0` | 紧急 |
| `P1` | 重要 |
| `P2` | 一般 |
| `approved` | Owner 已批准 |
| `needs-review` | 待 Reviewer 审查 |

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
- **PR 描述包含**：
  - 变更概述
  - 改动清单（文件 + 说明）
  - 自查清单
  - Reviewer 关注点

## 设计先行

非平凡功能的流程：

```
Reviewer 技术调研（推荐方案 + 参考实现 + 已知坑点）
  → Creator 写简短技术方案
    → Owner 确认
      → Creator 开发
```
