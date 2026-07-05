# 边界差异清单 — 设计文档 · 代码模块 · 运行时入口

> **版本**：v1.0.5（rev.2 — 证据层 + 落地合同补全）  
> **日期**：2026-06-24  
> **编码**：UTF-8（无 BOM）  
> **关联**：[memory_architecture.md](./memory_architecture.md) · [WholeDesign.md](../v1.0.4/WholeDesign.md)

---

## 0. 证据分级与统计快照

### 0.1 证据分级（必读）

| 级别 | 含义 | 本文中的用法 |
|------|------|-------------|
| **HARD** | 可机械核对 | 与 [boundary_stats.json](./boundary_stats.json) 中 `fingerprints` / `endpoints_by_file` **一致** 的数字、端点 path |
| **SOFT** | 方向性判断 | slug 命名、目标 prefix、未落地的 Facade 合同 — **不可**单独作为 PR 验收依据 |
| **BEHAVIOR** | 运行时断言 | pytest / 冒烟脚本 / 固定 API 序列 — Seam **必须**至少一条 |

**规则**：§0.2 的数字属 **HARD** 仅当同时满足：

1. 已运行 `python scripts/collect_boundary_stats.py`  
2. `meta.git_head` 与当前 `git rev-parse HEAD` 一致  
3. 关键文件 `sha256_prefix` 与 JSON 一致（见 JSON `route_fingerprints`）

若文档正文数字与 JSON 不一致，**以 JSON 为准，正文视为过期**。

### 0.2 当前 HARD 快照

| 指标 | 值 | 核对键 |
|------|-----|--------|
| 生成时间 | `2026-06-24T10:37:20Z` | JSON `meta.generated_at` |
| Git HEAD | `642c127ff5f8b1d6dff21de88941080944d017be` | JSON `meta.git_head` |
| route 文件数 | **15** | `backend.route_files` |
| route 总行数 | **5994** | `backend.route_total_lines` |
| HTTP 端点总数 | **96** | `backend.endpoint_total` |
| `archive.py` 行数 / 端点 | **192 / 5** | `fingerprints.archive.py` · `endpoint_counts_by_file.archive.py` |
| `archive.py` sha256 前缀 | `86c611b7bbb7e0bc` | 变更 archive 后必须重跑脚本 |
| `archive` 中 `/progress*` 端点 | **5** | `backend.archive_progress_endpoints` |
| 平铺 `/api` 的 router | **7 / 9** | `main_py_mounts` |
| 前端 `src/` 一级目录 | **7** | `frontend.src_top_level_dirs` |
| 前端 `home/report` 已注册 | **false** | `frontend.home_report_registered` |
| `app/stores/learning.ts` 行数 | **438** | `frontend.learning_store_fingerprint.lines` |

**重跑命令**：`python scripts/collect_boundary_stats.py`

---

## 1. Theme 模板与 slug ↔ 目录对照

每个 Theme 含：**Observed | Proposed**、差异项（证据 · 归属 · 风险）、**不改 / 改 / 验证 / 回退**，以及 **BEHAVIOR 验收**（至少一条）。

| slug                 | 中文名    | 后端目录/文件（observed → proposed）                         | 前端目录（observed → proposed）                                     |
| -------------------- | ------ | ---------------------------------------------------- | ------------------------------------------------------------- |
| `identity`           | 身份认证   | `routes/auth.py` → 保持                                | `app/` + `shared/api/auth.ts`                                 |
| `llm-connection`     | 模型连接   | `routes/archive.py` §settings → `routes/settings.py` | `settings/`                                                   |
| `world-shell`        | 世界壳    | `archive.py` §worlds → `routes/worlds.py`            | `worlds/`                                                     |
| `role-sheet`         | 角色档案   | `archive.py` §character → `routes/characters.py`     | `characters/` + `shared/api/character.ts` → `characters/api/` |
| `curriculum`         | 课程与教材  | `archive`+`textbook`+`bookshelf`+`learning_plans`    | `courses/`                                                    |
| `live-dialogue`      | 实时对话   | `routes/learning.py`                                 | `app/stores/learning.ts` → 见 §5 **分阶段**                       |
| `teaching-cognition` | 教学认知   | `services/memory_*`；读 API 在 `archive`                | `shared/api/memory.ts` → `courses/api/teaching-records.ts`    |
| `learner-trait`      | 学习者特质（世界内） | `LearnerProfile`；API 见 **§6.1** | `courses/api/course.ts` → `learner-trait.ts` |
| `user-profile`       | 用户画像（跨世界） | `UserProfile` + `services/user_profile.py`；API 见 **§6.2** | 无独立页；程序读写的聚合状态 |
| `lesson-mastery`     | 课节与掌握度 | `routes/textbook.py` canonical                       | `courses/api/course.ts`                                       |
| `timeline-anchor` | 时间线锚点 | `routes/save.py` → 保持 | store 内联 → `worlds/api/anchors.ts` |
| `plot-and-badge`     | 剧情与徽章  | `achievements.py` + engine 内嵌                        | ChatResponse 字段                                               |
| `learning-report`    | 学习报表展示 | `routes/report.py` → 保持                              | 缺 `report/views` + `#/home/report` → **§7**                   |
| `compat-surface`     | 待废弃兼容面 | `archive` diary/progress                             | `archives/`                                                   |

### 1.1 画像 vs 报表：三层分工（必读）

三者**不是**同一东西；`learning-report` **不替代** `UserProfile`。

| 层 | slug · 表/服务 | 面向谁 | 职责 | 工程角色 |
|----|---------------|--------|------|----------|
| 世界内特质 | `learner-trait` · `LearnerProfile(user_id, world_id)` | **程序**（Prompt 热路径） | 偏好、情感、元认知、dimension_scores；chat 写入 | **Domain data**（世界轴） |
| 跨世界画像 | `user-profile` · `UserProfile(user_id)` | **程序**（聚合/刷新） | 跨世界汇总后的长期结构化状态；由系统在会话后维护 | **Domain data**（用户轴） |
| 报表展示 | `learning-report` · `report.py` + Report 页 | **人**（阅读） | 读取多层数据 → 组织、解释、趋势/里程碑/建议 | **Read model / Presentation** |

**learning-report 的数据来源（只读组合，不另存画像副本）**：

```text
UserProfile
  + LearnerProfile（按 world 或汇总）
  + ConceptMastery / CourseProgress（lesson-mastery）
  + achievements / relationship history（plot-and-badge）
  + 可选 TeachingRecord 统计
    → 报表 DTO → 前端 Report.vue
```

**禁止**：在 `learning-report` 层新建与 `UserProfile` 平行的「报告用用户画像表」；报表接口 **不写** `user_profiles` 表。

---

## 2. Theme A — `main.py` 路由挂载

| | Observed | Proposed |
|---|----------|----------|
| 挂载 | 9 router；7× `prefix="/api"` | 按 slug **叠加** prefix；旧 prefix 保留 |
| 端点集合 | HARD：**96**（不变） | 拆分后仍 **96**（Seam B1 不增删 path） |

| ID | 当前证据（HARD/SOFT） | 目标 slug | 风险 |
|----|----------------------|-----------|------|
| A1 | HARD：`main_py_mounts` 7 条 `/api` | 各 slug | 低 |
| A2 | SOFT：tag `checkpoints` vs 产品「锚点」 | `timeline-anchor` | 低 |

**不改什么**：现有 path 字符串（Phase 1）。  
**改什么**：`main.py` 第二套 `include_router`。  
**怎么验证（结构）**：端点总数仍 **96**；OpenAPI path 集合 superset。  
**BEHAVIOR 验收**：`pytest backend/tests/test_schema_smoke.py`（若有）+ 手动 `GET /health` 200。  
**失败回退**：删除叠加 mount。

---

## 3. Theme B — `archive.py` 上帝路由

| | Observed | Proposed |
|---|----------|----------|
| 体量 | HARD：**2376** 行、**47** 端点 | 拆 7 文件；`archive.py` 兼容壳 **少于 100 行** |
| 覆盖 | 8 slug + `compat-surface` | 一 slug 一文件 |

**不改什么**：96 个端点 path 与 handler 行为。  
**改什么**：仅 Python 模块边界 + import。  
**怎么验证（结构）**：`fingerprints.archive.py.lines` 下降；`endpoint_total` 仍 **96**。  
**BEHAVIOR 验收**：`pytest backend/tests/test_course_apis.py backend/tests/test_archive.py`（全绿）；任取 3 个 archive 端点（如 `GET /worlds`、`GET /character`、`GET /settings`）响应 schema 与拆分前 snapshot 一致。  
**失败回退**：revert 拆分 PR。

---

## 4. Theme C/D — `ProgressFacade` 落地合同（非 HTTP 转发）

### 4.1 问题澄清

| 误解 | 本文采用 |
|------|---------|
| archive `/progress` **HTTP 转发**到 textbook | **否** — 同进程 **Python 函数调用**，非 307/反向代理 |
| 复制一套 handler 逻辑 | **否** — 单模块 **canonical 实现** |
| 目标 | 消除 **数据双写**（`ProgressTracking` vs `ConceptMastery`/`CourseProgress`） |

### 4.2 目标形状（Proposed · SOFT 直至 B2 合并）

新建 **`backend/services/progress_facade.py`**（名称固定）：

```text
progress_facade.get_lesson_progress(db, course, user_id)
    └─ 委托 teaching_planner.get_progress()          ← canonical（现 textbook.py 已用）

progress_facade.get_course_mastery(db, course_id, user_id)
    └─ 委托 mastery_tracker.get_course_mastery()

progress_facade.list_compat_progress_rows(db, user_id, course_id?)
    └─ 只读 ProgressTracking（仅供 archive GET /progress 过渡期）

progress_facade.record_review_compat(...)
    └─ Phase B2b：内部转调 mastery_tracker / FSRS；禁止新增 ProgressTracking 行
```

**路由层变化**：

| 文件 | Observed | Proposed |
|------|----------|----------|
| `textbook.py` | 直接 `import teaching_planner` | 改 `import progress_facade`（薄 wrapper） |
| `archive.py` `/progress*` | 直写 ORM **5** 端点（HARD） | handler **仅**调 `progress_facade.*` + 响应头 `Deprecation: true` + `Link: </api/courses/{id}/progress>; rel="successor-version"` |

**写入规则（BEHAVIOR 核心）**：

- **B2 完成后**：任何 **新** 掌握度变更只写 `ConceptMastery` + `CourseProgress`（经 `mastery_tracker`）。  
- `ProgressTracking`：**只读** compat，直至前端 Archive 页弃用。

**不改什么**：`ConceptMastery` 表结构；`textbook` 的 URL。  
**改什么**：抽取 Facade；archive POST `/progress` **停止 INSERT**。  
**BEHAVIOR 验收**：

1. 对话一轮后 `GET /courses/{id}/mastery` 与 B2 前 baseline 偏差在测试容忍内。  
2. `POST /progress`（archive）仍 200，但 **DB 内 ProgressTracking 行数不增加**（pytest 断言 count）。  
3. `GET /courses/{id}/progress`（textbook）与 archive `GET /progress?course_id=` 返回 **同一 canonical 课节指针**（字段 `current_lesson_index` 一致）。

**失败回退**：Feature flag `USE_PROGRESS_FACADE=false` 恢复 archive 直写（单文件开关，默认 true 仅在 staging）。

---

## 5. Theme E — `live-dialogue` 前端（承认耦合，分 PR）

### 5.1 Observed：单 store 混合职责

[`app/stores/learning.ts`](../../frontend/src/app/stores/learning.ts)（HARD：**438** 行）当前包含：

| 块 | 行号约 | 职责 | 现属 slug |
|----|--------|------|-----------|
| Session 生命周期 | 92–152, 390–396 | start/branch/history/chat/end | `live-dialogue` |
| Galgame UI 状态 | 36–50, 348–382 | mode、speaking、sprites 动画 | `live-dialogue` UI |
| 关系阶段 | 47–50, 248–257 | relationship_events | `live-dialogue` |
| 叙事/成就 toast | 55–57, 292–300 | narrativeEvents、newAchievements | `plot-and-badge` |
| 锚点 | 328–346 | create/fetch checkpoints | `timeline-anchor` |
| 知识图谱 | 315–326 | fetchKnowledgeGraph | **遗留**（后端路由已弱） |
| Memory 刷新信号 | 285–289 | `memory:fresh` 事件 | `teaching-cognition` |

**文档立场**：**不是**一个 PR 把 store 移到 `courses/stores/` 就完成边界；需 **E5a–E5e** 子 seam。

### 5.2 Proposed：分阶段迁移

| 子 PR | 提取内容 | 目标位置 | 依赖 |
|-------|---------|---------|------|
| **E5a** | Session API 调用 | `courses/api/live-dialogue.ts` | 无 |
| **E5b** | 锚点 API | `worlds/api/anchors.ts`；store 改 import | 无 |
| **E5c** | teaching-records 读 | `courses/api/teaching-records.ts` | 组件已用 event |
| **E5d** | store 文件迁移 | `courses/stores/learning.ts` + `app/stores/learning.ts` re-export | E5a–E5c |
| **E5e** | 叙事/成就 | 暂留 store；可选 `courses/stores/plot-toasts.ts` | 可选 |

**Observed | Proposed（路由 prefix）**：后端叠加 `/api/sessions` **不阻塞** E5a；可并行。

**BEHAVIOR 验收（每个子 PR）**：

- E5a：`Learning.vue` 完整流程 start → chat → end 无回归。  
- E5b：创建锚点 + branch 加载仍成功（现有 store 测试路径）。  
- E5d：`npm run build`；grep 无新增 `@/app/stores/learning` 可直接改 import（re-export 除外）。

**失败回退**：re-export 指回 `app/stores/learning.ts` 单体文件。

---

## 6. Theme F — 画像域：`learner-trait` + `user-profile`

### 6.1 `learner-trait` — 世界内学习者特质

| | Observed | Proposed |
|---|----------|----------|
| 主键 | `(user_id, world_id)` | 不变 |
| Prompt | 注入 affect / preference / metacognition / dimension_scores | 不变 |
| 写入口 | 仅 `live-dialogue` → engine | 不变 |

| 用途 | Observed（HARD） | Proposed |
|------|------------------|----------|
| 世界内读 | `GET /worlds/{world_id}/learner_profile` [`archive.py:1351`](../../backend/api/routes/archive.py#L1351) | `GET /api/learner-profiles/by-world/{world_id}`（叠加） |
| CRUD | `POST/GET/PUT /learner_profile*` archive | 迁 `routes/learner_profiles.py`；非 chat 热路径 |
| **禁止** | — | REST 直写 dimension_scores；course 轴 profile |

**BEHAVIOR**：一轮 chat 后该 world 的 `LearnerProfile` 有预期字段变化；响应 **无** TeachingRecord 长文本。

---

### 6.2 `user-profile` — 跨世界用户画像（Domain data）

| | Observed | Proposed |
|---|----------|----------|
| 主键 | `user_id` | 不变 |
| 表 | `user_profiles.profile` JSON | 不变 |
| 维护 | `user_profile.py`；session end / refresh / 懒计算 | 归 **`user-profile` router** |
| Prompt | **不注入**（[`learning.py:767`](../../backend/api/routes/learning.py#L767)） | 不变 |
| 与报表关系 | 曾被误称为「报表缓存」 | **报告的数据底座之一**；不是 Report 本身 |

| 用途 | Observed（HARD） | Proposed |
|------|------------------|----------|
| 跨世界读 | `GET /user/profile` [`learning.py:761`](../../backend/api/routes/learning.py#L761) | 迁至 `routes/user_profile.py`；path **保持** |
| 刷新 | `POST /user/profile/refresh` | 同上 |
| 写 | engine / `update_user_profile_after_chat` 等 | 仅 **`user-profile` services**；禁止 report 层写入 |

**BEHAVIOR**：`GET /user/profile` 返回聚合 JSON；`POST /user/profile/refresh` 后 `computed_at` 更新；**report 端点不修改** `user_profiles` 行。

**失败回退**：`/user/profile` 暂留 `learning.py`。

---

### 6.3 与 `learning-report` 的边界（再次强调）

| 问题 | 答案 |
|------|------|
| Report 是否存 UserProfile？ | **否** |
| UserProfile 是否等于 Report API？ | **否** — UserProfile 是 domain；Report 是 presentation |
| Report 读 UserProfile 吗？ | **是** — 只读，再叠加掌握度/成就/关系史等 |

---

## 7. Theme G — `learning-report`（学习报表展示）

> **定位**：Read model / Presentation — **解释与呈现**，不是 domain data，**不替代** `user-profile`。

### 7.1 Observed | Proposed

| | Observed | Proposed |
|---|----------|----------|
| 后端 | `routes/report.py` → `/api/report/*` | 保持；`services/report.py` **只读** 聚合 |
| 前端 | Home 有入口，**无**路由/页 | `report/views/Report.vue` + `report/api/report.ts` |
| 数据 | 读 DB 多表聚合 | 显式依赖：UserProfile + LearnerProfile + mastery + achievements + relationship |

### 7.2 报表读模型（Proposed 合同）

| 输入（只读） | 提供方 slug |
|-------------|------------|
| `UserProfile.profile` | `user-profile` |
| `LearnerProfile`（按 world 或跨 world 汇总） | `learner-trait` |
| `ConceptMastery` / 课节进度 | `lesson-mastery` |
| 成就 / 叙事里程碑 | `plot-and-badge` |
| 关系阶段历史 | `live-dialogue` / Session 衍生 |

| 输出 | 说明 |
|------|------|
| `MasteryTrendResponse` 等 DTO | 面向人的图表/文案字段；**不落库**为第二份画像 |

**不改什么**：`user_profiles` 表结构；`GET /user/profile` 语义。  
**改什么**：Report 页 + 路由；report service 文档化上述依赖。  
**BEHAVIOR**：调用 `GET /api/report/mastery-trends` **前后** `user_profiles` 表行数与 `profile` JSON 不变；页面能展示趋势文案。

### 7.3 目标路由形状（固定）

```typescript
// frontend/src/app/router/index.ts — 挂在 Home children 内
{
  path: 'report',
  name: 'Report',
  component: () => import('@/report/views/Report.vue'),
}
```

- **完整 URL（Hash 模式）**：`#/home/report`  
- **不是** 顶级 `/report`（避免脱离 Home 壳）  
- **不是** `/home/worlds/report`

**BEHAVIOR 验收**：登录后点击 Home「学习报告」进入 Report 页无 404；`GET /api/report/mastery-trends` 200 且页面渲染非空。

**失败回退**：Home 按钮临时 `disabled` + TODO；不半注册路由。

---

## 8. 冲突 · 重复 · 兼容（索引）

| 类 | ID | 摘要 | 证据 | 目标 slug |
|----|-----|------|------|-----------|
| 冲突 | C1 | progress 双写 | HARD：archive **5** 个 progress 端点 | `lesson-mastery` + Facade §4 |
| 冲突 | C4 | profile 入口分裂 | HARD：archive:1351 + learning:761 | `learner-trait` + `user-profile` §6 |
| 冲突 | C6 | report 断链 | HARD：`home_report_registered=false` | `learning-report` §7 |
| 重复 | R3 | memory-facts 双封装 | SOFT | `teaching-cognition` |
| 兼容 | L2 | ProgressTracking | HARD | Facade §4 |

---

## 9. Seam PR 顺序与 BEHAVIOR 总表

| PR | Theme | BEHAVIOR 验收（必跑） |
|----|-------|----------------------|
| B1 | archive 拆分 | §3 BEHAVIOR |
| B2 | ProgressFacade | §4.2 三条 |
| B3 | learner-trait + user-profile 路由归位 | §6.1–6.2 |
| B4 | main prefix 叠加 | §2 + 任一端点 smoke |
| B5a–e | live-dialogue 前端 | §5.2 各子项 |
| B6 | learning-report | §7.2 |

**结构冒烟（必要但不充分）**：`endpoint_total == 96`；`archive.py` 行数 `< 100`（兼容壳阶段）。

---

## 10. 文档维护与可信度

| 动作 | 责任 |
|------|------|
| 改 `archive.py` / 增删 `@router` | 重跑 `collect_boundary_stats.py` 并提交 JSON |
| 引用行数 | 同时写 `sha256_prefix` 或链到 JSON |
| Facade / 合同变更 | 升 rev 号；旧 rev 标记 superseded |

**当前 rev.2 说明**：针对 rev.1 评审 — 补充证据分级、ProgressFacade 具体形状、live-dialogue 分 PR、learner-trait 轴、report 路由形状、BEHAVIOR 验收。

**可用度**：结构讨论 + Seam 排期 **可作主文档**；**实施基线**以各 Theme 的 BEHAVIOR 块 + 最新 JSON 为准。

---

## 附录 A — route 文件指纹（HARD，摘自 JSON）

| 文件 | 行数 | sha256 前缀 | 端点数 |
|------|------|-------------|--------|
| `archive.py` | 192 | `86c611b7bbb7e0bc` | 5 |
| `characters.py` | 576 | `de5713a8e34ac7ef` | 9 |
| `worlds.py` | 775 | `97469b644d2b73dc` | 12 |
| `courses.py` | 417 | `2b7b6bd452bc891c` | 10 |
| `settings.py` | 293 | `8799888ef8e47952` | 4 |
| `learner_profiles.py` | 124 | `5fba272e8e742557` | 4 |
| `learning_diary.py` | 69 | `a2cefc22d69d1334` | 2 |
| `textbook.py` | 973 | `a4932af5f0ec71f1` | 12 |
| `learning.py` | 810 | 见 JSON | 8 |
| `save.py` | 729 | 见 JSON | 9 |

完整表：[boundary_stats.json](./boundary_stats.json) → `route_fingerprints`、`endpoints_by_file`。

---

## 附录 B — 源码入口

| 用途 | 路径 |
|------|------|
| 统计脚本 | [`scripts/collect_boundary_stats.py`](../../scripts/collect_boundary_stats.py) |
| 后端挂载 | [`backend/main.py`](../../backend/main.py) |
| 上帝路由 | [`backend/api/routes/archive.py`](../../backend/api/routes/archive.py) |
| 实时对话 | [`backend/api/routes/learning.py`](../../backend/api/routes/learning.py) |
| 前端路由 | [`frontend/src/app/router/index.ts`](../../frontend/src/app/router/index.ts) |
| 混合 store | [`frontend/src/app/stores/learning.ts`](../../frontend/src/app/stores/learning.ts) |
