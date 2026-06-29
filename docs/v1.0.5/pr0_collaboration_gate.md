# PR-0 协作门禁清单

> 版本：v1.0.5
> 日期：2026-06-24
> 适用范围：Self_Learning-System 重构期的人-agent 协作执行合同
> 上级文档：[memory_architecture.md](./memory_architecture.md) / [boundary_diff_inventory.md](./boundary_diff_inventory.md)

---

## 1. 目标

本文件不再讨论“应该设计成什么”。
本文件只约束“接下来怎么协作重构”，用于把 v1.0.5 从设计文档转成可执行门禁。

PR-0 的职责只有三件事：

1. 冻结当前重构基线。
2. 固定后续 seam 的落地顺序。
3. 统一人-agent 在每个 seam 上的输入、输出、验收与回退。

---

## 2. 单一准绳

后续所有 PR 必须同时服从以下两份文档：

- 语义准绳：[memory_architecture.md](./memory_architecture.md)
- 边界准绳：[boundary_diff_inventory.md](./boundary_diff_inventory.md)

若实现、旧注释、历史讨论、临时想法与这两份文档冲突：

- 记忆语义问题，以 `memory_architecture.md` 为准。
- 模块拆分顺序、路径归位、验收口径，以 `boundary_diff_inventory.md` 为准。

---

## 3. 当前冻结基线

本轮协作基线以以下快照为准：

- Git HEAD：`457b4cca93c9921b0fd7c0a945f2ff9a0791791d`
- 基线文档目录：`docs/v1.0.5/`
- 基线统计文件：[boundary_stats.json](./boundary_stats.json)

进入任一 seam 开发前，agent 必须先完成一次基线核对：

1. 运行 `python scripts/collect_boundary_stats.py`
2. 核对输出中的 `meta.git_head`
3. 核对关键 fingerprint 与 [boundary_stats.json](./boundary_stats.json) 是否一致

若不一致：

- 先停止进入新 seam
- 先补一次“基线漂移说明”
- 再决定是更新基线还是回到旧基线

---

## 4. 人-Agent 分工

### 4.1 人负责裁决

人负责以下决策，agent 不自行扩张：

- 本轮只做哪些 seam
- 哪些旧 API path 在本轮不能改
- 哪些行为必须保持完全兼容
- 哪些地方允许先做 alias / facade / re-export 过渡
- 当前 PR 是否满足“可以合并”的产品语义标准

### 4.2 Agent 负责执行

agent 负责以下工作，默认持续推进到可验收：

- 读取相关 seam 文档与代码上下文
- 提取当前基线证据
- 实施最小可验证改动
- 运行测试或构造行为验证
- 回填文档、说明风险、准备回退路径

### 4.3 明确禁止

未经人明确确认，agent 不做以下事情：

- 同一 PR 同时改 memory 语义和 frontend 体验
- 改已有 API path 语义后不提供兼容层
- 在 report 层新增并行画像存储
- 因“顺手”把多个 seam 合并成大重构
- 跳过 BEHAVIOR 验收只看结构变动

---

## 5. Git 分支与合并策略

> 适用场景：单人 Owner + 2～3 个 agent 并行小步推进 seam；无多人 Code Review，但仍需保持 `main` 稳定与分支隔离。

### 5.1 分支模型

```text
main（稳定、可随时跑通）
  ├── feat/progress-facade    ← Seam A 任务分支
  ├── feat/archive-split      ← Seam B 任务分支
  └── feat/…                  ← 其它 seam / 子任务
```

约定：

- `main` 是唯一稳定主干；任意 merge 点后应能跑通当前关注的测试。
- **一个 agent 独占一条任务分支**，不与其它 agent 并行改同一分支。
- 分支命名沿用仓库惯例：`feat/<seam-或任务名>`，与 [§7 每个 Seam 的统一合同](#7-每个-seam-的统一合同) 一一对应。

### 5.2 推荐日常流程

单人 + 多 agent 场景下，允许本地小步 commit，但**凡是进入远程协作、需要 CI、需要 Reviewer 审核、或需要合并到 `main` 的改动，一律必须走 PR**。  
创建 PR 时**必须使用仓库 PR 模板**：[`.github/pull_request_template.md`](../../.github/pull_request_template.md)。不得手写空白描述，不得省略模板字段。

```bash
# 开新 seam / 子任务
git checkout main && git pull
git checkout -b feat/<任务名>

# agent 小步开发（每个可描述的小改动即 commit）
git add … && git commit -m "feat: …"

# 任务完成、准备合入 main 前
git fetch origin
git rebase origin/main          # 冲突在此解决；团队也可统一改用 merge origin/main
# 运行 BEHAVIOR 验收（见各 seam 门禁）
git checkout main && git merge feat/<任务名>
git push origin main
git branch -d feat/<任务名>
```

开发过程中若 agent 会话可能中断，可随时 `git push -u origin feat/<任务名>` 作远程备份；**合入 main 仍按上表最后四步执行**。

### 5.3 merge 与 rebase 选用

| 场景 | 推荐做法 |
|------|----------|
| 任务分支尚未合入 `main`，需对齐最新主干 | `git rebase origin/main`（Owner 独占分支，可用 `--force-with-lease` push） |
| 某 seam 已合入 `main`，其它活跃分支需跟上 | 在对应分支上 `git rebase main` |
| 分支已 push 且可能有其它 agent 仍在使用 | 用 `git merge origin/main`，避免 rebase + force push |
| 合入 `main` | 本地 `git merge feat/<任务名>` 后 `git push origin main` |
| 需要 PR 记录或等 CI 再合 | push 分支 → **按仓库模板填写 PR 描述** → 平台 merge → 本地 `git pull --rebase` 同步 `main` |

### 5.4 多 Agent 并行时的硬规则

1. **一 agent 一分支一 seam（或子任务）**——禁止多个 agent 同时改同一分支或同一组未协调文件。
2. **合入 main 前先拉最新 main 并对齐**——不在 stale 分支上直接 merge。
3. **一次只推进一个 seam 进 main**——与 [§4.3 明确禁止](#43-明确禁止) 及 [§10 合并门禁](#10-合并门禁) 一致；其它 seam 在各自分支上等待，不夹带进当前 merge。
4. **main 永远可运行**——merge 前至少完成当前 seam 要求的 BEHAVIOR 证据，不能「先合再补测」。
5. **远程 PR 一律套模板**——PR body 必须基于 [`.github/pull_request_template.md`](../../.github/pull_request_template.md) 填写，并包含有效的 `Closes #N` / `Fixes #N` / `Resolves #N`。

### 5.5 明确禁止（Git 层）

未经 Owner 确认，agent 不得：

- 直接向 `main` push 未验收的半成品
- 在多个活跃任务分支之间 cherry-pick 大段未关联改动
- 对已被其它 agent 使用的共享分支 force push
- 跳过 rebase/merge 对齐步骤，在严重漂移的分支上硬合 `main`
- 为「省事」把多个 seam 压进一次 merge

---

## 6. 固定执行顺序

v1.0.5 建议按以下顺序推进。后一个 seam 默认依赖前一个 seam 已稳定。

1. `ProgressFacade`
2. `archive.py` split
3. `learner-trait` / `user-profile` / `learning-report` 边界归位
4. `live-dialogue` 前端 store 拆分

顺序说明：

- `ProgressFacade` 优先，因为它先切断 `ProgressTracking` 的双写风险。
- `archive.py` 第二，因为它主要是模块边界搬运，语义风险低于 memory 主链路改写。
- profile/report 第三，因为它依赖前两步边界先清晰。
- 前端 learning store 最后，因为它最容易在 UI 层把多个 slug 再次混回去。

---

## 7. 每个 Seam 的统一合同

每个 seam PR 必须在描述中显式回答 4 个问题：

1. 不改什么
2. 改什么
3. 怎么验证
4. 失败怎么回退

且必须同时提供三类证据：

- `HARD`：统计、fingerprint、路径集合、文件体量等结构证据
- `BEHAVIOR`：测试、接口调用、烟雾验证、关键业务断言
- `ROLLBACK`：回退开关、re-export、compat router、revert 策略

缺任意一类，默认不算通过。

---

## 8. 分 Seam 门禁

### 8.1 Seam A: `ProgressFacade`

目标：

- 建立统一进度读取与兼容写入入口
- 停止 archive `/progress` 继续直接制造新双写

不改什么：

- 不改 `textbook` canonical URL
- 不改 `ConceptMastery` 与 `CourseProgress` 的权威地位
- 不要求本 PR 删除所有 compat 接口

怎么验证：

- `GET /courses/{id}/progress` 与 archive `GET /progress?course_id=` 的 canonical 指针一致
- archive `POST /progress` 仍可兼容返回成功
- 新请求不再新增 `ProgressTracking` 行数

失败怎么回退：

- 通过单点开关恢复 archive 直写
- 或完整 revert 本 PR，不影响后续 seam

### 8.2 Seam B: `archive.py` split

目标：

- 将上帝路由拆回 slug 对应文件
- 保留兼容面，先不动 URL 语义

不改什么：

- 不改现有 endpoint path
- 不改 handler 对外响应 schema
- 不借拆分机会重写业务逻辑

怎么验证：

- endpoint 总数保持不变
- 关键 archive 接口响应与拆分前一致
- `archive.py` 体量显著下降，兼容壳保留

失败怎么回退：

- 整个拆分 PR 可独立 revert
- compat shell 保留到新路由稳定后再删

### 8.3 Seam C: `learner-trait` / `user-profile` / `learning-report`

目标：

- 把 domain data 与 presentation 边界写实
- 明确 Report 只读聚合，不再被误当成画像主存储

不改什么：

- 不让 report 写 `user_profiles`
- 不让 `UserProfile` 变成新的前端展示缓存副本
- 不改变 chat 主链路里的画像注入职责边界

怎么验证：

- `GET /user/profile` 仍返回聚合 JSON
- refresh 行为只更新 user-profile 维护数据
- report 接口只读多源数据，不触发表写入

失败怎么回退：

- `/user/profile` 可暂留原位置
- 新 router 失败时回切旧挂载

### 8.4 Seam D: `live-dialogue` 前端 store 拆分

目标：

- 把 `app/stores/learning.ts` 的跨域职责拆开
- 先拆 API 与边界，再迁 store 所在目录

不改什么：

- 不在一个 PR 里重做整个 Learning UI
- 不改现有用户流程：start -> chat -> branch -> end
- 不先删兼容 re-export

怎么验证：

- `npm run build` 通过
- Learning 主流程无回归
- 新增 import 不再继续指向旧 `app/stores/learning`

失败怎么回退：

- 通过 re-export 指回原 store
- 子 PR 独立 revert，不影响后端 seam

---

## 9. PR 模板要求

后续每个 seam PR **必须直接使用** [`.github/pull_request_template.md`](../../.github/pull_request_template.md)。

最低要求：

- 不得新建空白 PR 描述替代模板
- 不得删除模板中的 `Linked Issues`
- `Linked Issues` 必须填写真实 issue 编号，并使用自动关闭关键字：`Closes #N` / `Fixes #N` / `Resolves #N`
- 若本 PR 是 seam PR，还必须在模板字段中把 seam 范围写清楚

此外，每个 seam PR 描述至少应覆盖以下信息：

```md
## Seam

## 不改什么

## 本次改动

## HARD 证据

## BEHAVIOR 证据

## 回退方案

## 是否影响下一个 seam
```

---

## 10. 合并门禁

一个 seam PR 只有同时满足以下条件才允许合并：

1. 本 seam 的“目标”是单一的，没有夹带第二主题。
2. 兼容面仍在，或已经被等价验证替代。
3. 有至少一条结构证据。
4. 有至少一条行为证据。
5. 有清晰回退路径。
6. 文档已同步更新到 `docs/v1.0.5/` 或相关说明文件。
7. PR 描述使用仓库模板，且 `Linked Issues` 满足 CI 自动关闭规则。

若只完成代码改动、未完成证据闭环，则状态只能算“已实现，未验收”，不能算“完成”。

---

## 11. 本轮起始建议

PR-0 之后，建议立刻进入的不是“大一统 memory 重写”，而是：

1. 先做 `ProgressFacade`
2. 验证 compat 读写行为
3. 再进入 `archive.py` 拆分

这样做的原因很直接：

- 先消除双写，再整理边界，风险最小
- 先做后端 seam，再动前端协作面，回归范围可控
- 先把“唯一入口”建立起来，后续 agent 才不会在旧入口上继续加债

---

## 12. 执行约束一句话

后续所有 agent 在 v1.0.5 阶段的默认工作方式是：

**一次只推进一个 seam，只做最小可验证改动，只在证据闭环后进入下一个 seam。**
