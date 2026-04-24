存储设施设计方案
现状盘点
当前系统有 3 种存储方式并存：

| 数据 | 存储位置 | 大小级别 | 问题 |
|------|---------|---------|------|
| 用户/世界/角色元数据 | SQLite `*.db` | 几 KB/条 | ✅ 没问题 |
| MemoryFact 内容 | SQLite `content` TEXT | 50-500 字/条 | ⚠️ 当前够用，但检索全靠ILIKE，无语义索引 |
| Checkpoint 存档 | 本地文件 `data/saves/{user_id}/` | 1-10 MB/个 | ✅ 已实现`SaveFileManager` |
| Phase 2C 教材文件 | 本地文件 `data/materials/{user_id}/` | 1-50 MB/个 | 🆕 需新建 |
| Phase 2D 叙事配置 | World.scenes JSON 列 | 几 KB/世界 | ⚠️ 适合外置 |


三种存储方式详解

## 方式一：SQLite 关系型数据库

**存储形式**：单文件数据库 `data/socratic_learning.db`，通过 SQLAlchemy ORM 读写。

**具体存储内容**：

| 表名 | 存什么 | 典型数据示例 |
|------|--------|-------------|
| `users` | 用户账号（用户名、密码哈希、角色） | `id=1, username="alice", role="student"` |
| `worlds` | 世界/课程（名称、描述、scenes JSON） | `id=1, name="魔法学院", scenes={...}` |
| `characters` | 角色（sage导师/traveler旅人，人格参数、立绘配置） | `id=3, name="苏格拉底", type="sage", traits={strictness:0.7,...}` |
| `world_characters` | 世界与角色的关联（多对多） | `world_id=1, character_id=3, role="sage"` |
| `courses` / `lesson_plans` | 课程和课时计划 | `id=5, name="Python入门", meta={...}` |
| `sessions` | 学习会话（关联课程、角色、关系状态） | `id=10, relationship={trust:0.5,...}` |
| `chat_messages` | 对话记录（每条消息的发送者、内容、情感分析） | `id=100, content="递归是什么？"` |
| `memory_facts` | **记忆事实**（AI从对话中提取的学生认知） | `id=1, fact_type="concept_struggle", content="学生对递归有困难"` |
| `learner_profiles` | 学习者档案（偏好、元认知趋势） | `profile={visual_examples:true,...}` |
| `checkpoints` | 存档索引（file_path 指向文件，state 为旧存档兼容） | `id=1, file_path="1/checkpoint_1_xxx.json"` |
| `fsrs_states` | 间隔重复状态（每个知识点的难度、稳定性） | `concept_id="递归", difficulty=4.2` |
| `relationship_stages` | 关系阶段变化记录 | `stage="friend", reason="连续5次会话"` |
| `progress_trackings` | 学习进度（每个主题的掌握度） | `topic="循环", mastery_level=45` |

**特点**：结构化、有 Schema 约束、支持复杂查询（WHERE/JOIN/ORDER BY）、事务安全。

### 现状审计：前后端对接情况

> 以下审计基于 v1.0.1 框架细化整理后的代码实际状态，逐表追踪"后端路由 → 前端 API 模块 → 前端 View"的调用链。

#### 审计总表

| # | DB 表 | 后端路由文件 | 后端 API 端点 | 前端 API 模块 | 前端 View | 对接状态 |
|---|-------|------------|-------------|-------------|----------|---------|
| 1 | users | auth.py | POST /register, POST /login, GET /me | authApi (auth.ts) | Login.vue | ✅ 正常 |
| 2 | worlds | archive.py | CRUD /worlds | worldApi (world.ts) | Worlds.vue, WorldDetail.vue | ✅ 正常 |
| 3 | characters | archive.py | CRUD /character + /levelup + /avatar | characterApi (character.ts) | Character.vue, WorldDetail.vue | ✅ 正常 |
| 4 | world_characters | archive.py | /worlds/{id}/characters POST/GET/DELETE | worldApi (world.ts) | WorldDetail.vue | ✅ 正常 |
| 5 | courses | archive.py | CRUD /courses, /worlds/{id}/courses | worldApi + courseApi | WorldDetail.vue, CoursePage.vue | ✅ 正常 |
| 6 | lesson_plans | archive.py | 暂无独立端点 | ❌ 无前端调用 | ❌ 无 | ⚠️ 仅 DB 存在，无 API 暴露 |
| 7 | sessions | learning.py | POST /courses/{id}/start, GET /sessions, POST /sessions/{id}/end | learningStore 直接用 client | Learning.vue (via store) | ✅ 正常（store 绕过 api 模块） |
| 8 | chat_messages | learning.py | POST /courses/{id}/chat, GET /sessions/{id}/history | learningStore 直接用 client | Learning.vue (via store) | ✅ 正常 |
| 9 | memory_facts | archive.py | GET /courses/{id}/memory-facts | memoryApi + courseApi | Learning.vue, CoursePage.vue | ✅ 正常 |
| 10 | learner_profiles | archive.py | POST/GET/PUT /learner_profile | ❌ 无前端调用 | ❌ 无 | ⚠️ 后端有 CRUD，前端未接入 |
| 11 | checkpoints | save.py | CRUD + /branch + /export + /import + /timelines | learningStore 直接用 client | Learning.vue (via store) | ✅ 正常 |
| 12 | fsrs_states | archive.py | POST /progress/{id}/review, GET /progress/due | archiveApi | Archive.vue | ⚠️ 间接触达 |
| 13 | relationship_stages | 无独立端点 | 随 session 写入 | ❌ 无 | ❌ 无 | ⚠️ 仅 DB 存在 |
| 14 | progress_trackings | archive.py | CRUD /progress + /review + /due | archiveApi | Archive.vue | ✅ 正常 |
| 15 | learning_diaries | archive.py | POST/GET /learning_diary | archiveApi | Archive.vue | ✅ 正常 |
| 16 | user_profiles | learning.py | GET /user/profile, POST /user/profile/refresh | userProfileApi | Home.vue | ✅ 正常 |

#### 关键发现

**🔴 问题 1：learningStore 绕过 API 模块直接用 client**

stores/learning.ts 直接 import client 发请求（如 /checkpoints/{id}/branch、/courses/{id}/start、/courses/{id}/chat），没有走 worldApi 或 courseApi。

- 影响：后端路由路径变更需在 store 和 api 模块两处修改
- v1.0.1 框架细化 Issue #29 已记录此问题但未修复

**🟡 问题 2：3 张表无前端入口**

| 表 | 状态 | 原因 |
|----|------|------|
| lesson_plans | 无 API 端点 | 课程计划生成功能未实现（Phase 2B 范畴） |
| learner_profiles | 后端有 CRUD，前端未调用 | 创建世界时后端自动创建，但前端无查看/编辑入口 |
| relationship_stages | 无独立端点 | 关系阶段变化随 session 写入，仅在存档快照中间接读取 |

**🟡 问题 3：reports.py 聚合查询**

report.py 提供 /mastery-trends、/relationship-history、/world-comparison、/milestones 等聚合端点，前端 reportApi 定义了但暂无独立 Report 页面。


---

## 方式二：本地文件系统 — 存档文件

**存储形式**：JSON 文件，存放在 `data/saves/{user_id}/` 目录下，由 `SaveFileManager`（`backend/services/save_file_manager.py`）管理。

**具体存储内容**：

每个存档是一个 JSON 文件，包含一次"游戏存档"的完整快照：

```json
{
  "version": "2.0",
  "checkpoint_id": 123,
  "created_at": "2026-04-14T10:00:00Z",
  "session_meta": {
    "session_id": 456,
    "course_id": 789,
    "world_id": 1,
    "sage_character_id": 1,
    "traveler_character_id": 2,
    "relationship_stage": "friend"
  },
  "relationship": {
    "dimensions": {"trust": 0.8, "familiarity": 0.6, "respect": 0.7, "comfort": 0.5},
    "stage": "friend",
    "history": []
  },
  "chat_history": [
    {"sender_type": "sage", "content": "你好，欢迎来到魔法学院", "timestamp": "...", "emotion_analysis": null},
    {"sender_type": "traveler", "content": "递归是什么？", "timestamp": "..."}
  ],
  "learner_profile_snapshot": {"level": "beginner", "preferences": {}},
  "memory_snapshot": {
    "memory_ids": [1, 2, 3],
    "facts": [
      {"id": 1, "fact_type": "concept_struggle", "content": "学生对递归有困难", "salience": 0.8}
    ]
  },
  "progress_snapshot": {
    "topics": [{"topic": "Python basics", "mastery_level": 45}]
  }
}
```

**文件命名规则**：`checkpoint_{checkpoint_id}_{timestamp}.json`，如 `checkpoint_123_20260414100000.json`

**与数据库的关系**：`checkpoints` 表中 `file_path` 字段存储相对路径（如 `1/checkpoint_123_20260414100000.json`），作为索引指向文件。旧存档 `file_path` 为 NULL，数据存在 `state` JSON 列中。

**特点**：大块数据（完整对话历史可达数 MB）、按 ID 整体读写、不需要结构化查询。

> **疑问：`chat_messages` 表和存档文件里的 `chat_history` 有什么区别？为什么不直接用其中一个？**
>
> 它们是**同一段对话数据的两种形态**，用途完全不同：
>
> | 维度 | `chat_messages` 表（SQLite） | 存档文件 `chat_history`（JSON） |
> |------|---------------------------|-------------------------------|
> | **是什么** | 对话的**原始记录**，实时逐条写入 | 对话的**时间点快照**，存档时一次性打包 |
> | **写入时机** | 每条消息发送时立即 INSERT 一行 | 用户点击"存档"时，从 `chat_messages` 查出当前 session 的所有消息，序列化进 JSON |
> | **数据范围** | 只存当前 session 的消息（通过 `session_id` 关联） | 当前 session 中截至存档点的消息（由存档时的 `message_index` 决定截断位置） |
> | **查询方式** | `SELECT * FROM chat_messages WHERE session_id=10`（结构化） | 整个 JSON 一次性读入内存（非结构化） |
> | **生命周期** | 随 session 存在，session 删除则消息删除 | 独立于 session，即使 session 被删除，存档文件仍然保留完整快照 |
> | **用途** | 学习过程中的实时对话展示、记忆提取、情感分析 | "读档"时恢复完整上下文、导出/分享、备份 |
>
> **类比**：
> - `chat_messages` = 微信聊天记录（实时收发，存在 app 数据库里）
> - 存档文件的 `chat_history` = 你把聊天记录导出成文件保存（静态快照，不怕 app 卸载）
>
> **为什么两个都要**：
> 1. 学习过程中需要**实时查询**消息（展示对话界面、提取记忆）→ 用 `chat_messages`
> 2. 存档需要**独立于数据库**的完整快照（数据库可能被清理/迁移）→ 用 JSON 文件
> 3. 存档中包含的不只是对话，还有关系状态、记忆快照、进度快照等**跨表聚合数据**，这些无法用单张表表达

> **追问：Checkpoint 具体是怎么工作的？从"用户点存档"到"文件落盘"的完整流程是什么？**
>
> ### 存档（Save）流程
>
> ```
> 用户点击"存档"按钮
>        ↓
> 前端 POST /checkpoints { world_id, session_id, save_name: "第三章-递归入门" }
>        ↓
> 后端 create_checkpoint() 执行：
>        ↓
> ① 验证世界和会话归属当前用户
>        ↓
> ② 在 checkpoints 表 INSERT 一行（此时只有最小元数据 state + message_index）
>    state = { relationship: {...}, course_id: 789, sage_character_id: 1, traveler_character_id: 2 }
>    ↓ flush → 获得 checkpoint.id（如 123）
>        ↓
> ③ 调用 _build_full_save_data() 从多张表聚合完整快照：
>    ├─ sessions 表 → session_meta（课程ID、世界ID、角色ID、关系阶段）
>    ├─ chat_messages 表 → chat_history（SELECT 前 message_index 条消息）
>    ├─ learner_profiles 表 → learner_profile_snapshot
>    ├─ memory_facts 表 → memory_snapshot（TOP 50 by salience）
>    └─ progress_trackings 表 → progress_snapshot
>        ↓
> ④ SaveFileManager.write_save_file() → 写入 data/saves/1/checkpoint_123_20260414100000.json
>        ↓
> ⑤ 更新 checkpoints 表的 file_path 和 file_size_bytes
>        ↓
> ⑥ db.commit() → 事务提交，存档完成
> ```
>
> ### 读档（Load）流程
>
> ```
> 用户选择一个存档点击"读档"
>        ↓
> 前端 GET /checkpoints/123
>        ↓
> 后端 get_checkpoint() 执行：
>        ↓
> ① 从 checkpoints 表查到记录，发现有 file_path = "1/checkpoint_123_20260414100000.json"
>        ↓
> ② SaveFileManager.read_save_file() → 读取 JSON 文件，解析为 dict
>        ↓
> ③ 返回完整的存档数据（含 chat_history、relationship、memory_snapshot 等）
>        ↓
> 前端拿到数据，恢复对话界面到存档时的状态
> ```
>
> ### 删档流程
>
> ```
> DELETE /checkpoints/123
> ① 查到 checkpoint 记录
> ② 如果有 file_path → SaveFileManager.delete_save_file() 删除 JSON 文件
> ③ db.delete(checkpoint) → 删除数据库记录
> ```
>
> ### 分支（Branch）流程
>
> ```
> POST /checkpoints/123/branch { branch_name: "试试另一种学法" }
> ① 读取存档 123 的完整数据
> ② 创建一个新的 Session，parent_checkpoint_id = 123
> ③ 新会话继承存档时的 relationship、learner_profile 等
> ④ 用户从存档点开始新的学习路径（不影响原存档）
> ```
>
> **类比**：Checkpoint = Galgame 的存档系统
> - 存档 = 截图保存当前剧情进度（对话、好感度、事件状态全部打包）
> - 读档 = 载入截图，回到那个时间点
> - 分支 = 从某个存档点开始走不同的剧情线（周目概念）

---


### 现状审计：存档文件前后端对接

> 基于 v1.0.1 框架细化整理后的代码实际状态。

#### 后端组件

| 组件 | 文件 | 行数 | 功能 |
|------|------|------|------|
|  |  | 162 行 | 存档文件读写删、目录管理 |
|  路由 |  | 700 行 | 8 个端点：CRUD + branch + timelines + export + import |
|  | save.py 内 | ~95 行 | 从 5 张表聚合完整快照数据 |

#### 后端 API 端点 → 前端调用对照

| # | 端点 | 功能 | 前端调用者 | 状态 |
|---|------|------|----------|------|
| 1 |  | 创建存档 |  | ✅ 正常 |
| 2 |  | 列出所有存档 | ❌ 无前端调用 | ⚠️ 未使用 |
| 3 |  | 列出世界的存档 |  | ✅ 正常 |
| 4 |  | 读取单个存档详情 | ❌ 无前端调用 | ⚠️ 未使用 |
| 5 |  | 删除存档 | ❌ **前端未调用** | 🔴 **bug** |
| 6 |  | 分支存档 |  | ✅ 正常 |
| 7 |  | 获取时间线 |  定义了但无 View 使用 | ⚠️ 未使用 |
| 8 |  | 导出存档 | ❌ 无前端调用 | ⚠️ 未使用 |
| 9 |  | 导入存档 | ❌ 无前端调用 | ⚠️ 未使用 |

#### 前端存档交互流程



#### 关键发现

**🔴 Bug：删除存档只做了前端过滤**

 在  第 326 行：

仅从本地数组移除，**没有调用 **。后端的  和  都不会执行。刷新页面后，被"删除"的存档会重新出现。

**🟡  默认值不一致**

| 来源 | 默认值 |
|------|--------|
|   | （相对 CWD） |
|  fallback |  |
| save_plan 文档描述 |  |

config 默认值是 ，与文档描述的  不一致。

**🟡 Export/Import 功能后端已完成但前端未接入**

后端  实现了完整的导出（v2.0 格式 + v1.0 兼容）和导入功能，但前端无任何调用入口。

**🟡 Timelines 功能未使用**

 在  中有定义，但没有 View 渲染时间线界面。


## 方式三：本地文件系统 — 教材文件（Phase 2C 新建）

**存储形式**：原始文件存放在 `data/materials/{user_id}/` 目录下（PDF/TXT/EPUB 原文件），解析后的纯文本存在 `materials` 表的 `parsed_content` TEXT 列中。

**具体存储内容**：

| 存什么 | 存在哪 | 格式 |
|--------|--------|------|
| 原始教材文件 | `data/materials/{user_id}/{uuid}_{filename}` | PDF/TXT/EPUB 二进制文件 |
| 解析后的纯文本 | `materials.parsed_content` (DB) | 纯文本字符串 |
| AI 分析结果（知识点列表、教学顺序） | `materials.analysis_result` (DB) | JSON |
| 解析状态 | `materials.parse_status` (DB) | 字符串枚举：pending/parsing/parsed/failed |

**原始文件保留原因**：供重新解析用（如更换解析引擎、调整解析参数时不需要重新上传）。

**特点**：文件体积大（1-50 MB）、一次性写入、偶尔重新解析、不需要查询文件内容（查询的是 DB 中的分析结果）。

---


### 现状审计：教材文件（Phase 2C 规划中）

> 方式三是 Phase 2C 新建功能，**当前无任何实现代码**。以下基于 plan.md 中的设计进行审计。

#### 当前状态

| 维度 | 状态 |
|------|------|
| DB 模型（Material 类） | ❌ 未创建（plan.md 有设计） |
| 文件存储目录 | ❌ 不存在（计划 `data/materials/{user_id}/`） |
| 上传 API | ❌ 未实现（计划 `POST /materials/upload`） |
| 解析引擎 | ❌ 未实现（PDF/TXT/EPUB 解析） |
| AI 分析 | ❌ 未实现（知识点提取、教学顺序） |
| 课程生成 | ❌ 未实现（Material → Course 转换） |
| 前端组件 | ❌ 未创建（上传、状态查看、课程生成） |

#### 规划中的数据流（按用户操作时序）

> 回答三个核心问题：用户在哪里操作？操作后哪些数据在什么时刻被创建？数据在三种存储间如何流动？

##### 场景 A：用户上传教材

**在哪里**：`WorldDetail.vue` 世界详情页（绑定到特定世界）或设置页（全局材料管理区，plan.md C5 讨论区有规划）

```
用户在 WorldDetail 页点击"上传教材"按钮
    ↓ 选择 PDF/TXT/EPUB 文件（≤50MB）
    ↓
【前端】POST /materials/upload  (multipart/form-data)
    参数: file=PDF二进制, world_id=1
    ↓
【后端 upload_material()】
    ① 验证文件类型 + 大小
    ② 写入文件: data/materials/1/uuid_python_crash_course.pdf   ← 方式三（文件存储）
    ③ INSERT materials 表:                                      ← 方式一（SQLite）
       id=5, user_id=1, world_id=1
       original_filename="python_crash_course.pdf"
       file_path="data/materials/1/uuid_python_crash_course.pdf"
       parse_status="pending"
       parsed_content=NULL, analysis_result=NULL
    ④ 触发后台解析任务（async）
    ⑤ 返回 { material_id: 5, status: "pending" }
    ↓
【前端】轮询 GET /materials/5/status → { status: "parsing" }
    显示解析进度条
```

**此时存储变化**：
| 存储 | 新增内容 |
|------|---------|
| 方式三（文件） | `data/materials/1/uuid_python_crash_course.pdf`（原始 PDF） |
| 方式一（SQLite） | `materials` 表新增 1 行（元数据 + pending 状态） |

---

##### 场景 B：系统解析教材（后台自动）

**用户感知**：在 WorldDetail 页看到解析进度条从"解析中"变为"解析完成"

```
后台任务自动执行（用户无需操作）
    ↓
【MaterialParser.parse_pdf()】
    ① 读取文件: data/materials/1/uuid_python_crash_course.pdf  ← 方式三（读文件）
    ② pymupdf 提取文本，按章节分割
    ③ UPDATE materials SET parsed_content="第一章 导论...（150000字）",
       parse_status="parsed", chapter_count=12                 ← 方式一（SQLite TEXT）
    ↓
【MaterialParser.analyze_with_llm()】
    ④ 分章节将 parsed_content 送入 LLM
    ⑤ LLM 返回分析结果:
       {
         "knowledge_points": [
           {"name":"递归","bloom_level":"understand","prerequisites":["函数"],"chapter":3},
           {"name":"函数","bloom_level":"apply","prerequisites":[],"chapter":1},
           ...共 45 个知识点
         ],
         "teaching_order": ["变量","函数","递归",...],
         "difficulty_assessment": "intermediate",
         "suggested_session_count": 15
       }
    ⑥ UPDATE materials SET analysis_result={上述JSON}          ← 方式一（SQLite JSON）
```

**什么是 MemoryFact 种子？（基于代码实际定义）**

根据 `memory_facts.py` 中 `create_seed_memories()` 的实际代码，**MemoryFact 种子是指从学生的 traveler 角色和 learner_profile 中提取的初始认知事实**，让 AI 导师在第一次对话时就了解学生的基本情况。

**当前代码中种子的实际来源和内容**（`memory_facts.py` L148-301）：

| 种子内容 | 来源 | fact_type | salience |
|---------|------|-----------|----------|
| 学生名字 | `traveler_character.name` | `student_state` | 0.9 |
| 学习方向标签 | `traveler_character.tags` | `preference` | 0.7 |
| 学习背景 | `traveler_character.background` | `student_state` | 0.6 |
| 性格特点 | `traveler_character.personality` | `preference` | 0.5 |
| 已有学习经历 | `learner_profile.learning_stats.total_sessions` | `student_state` | 0.8 |
| 平均掌握度 | `learner_profile.learning_stats.average_mastery` | `concept_mastered` | 0.85 |
| 学习偏好 | `learner_profile.preference_stability` | `preference` | 0.75 |
| 元认知趋势 | `learner_profile.metacognition_trend` | `student_state` | 0.6 |

**关键：这些种子都是关于"学生是谁"的认知，不是关于"教材教什么"的知识点。**

当前代码中的 6 种 fact_type（来自 `memory_facts.py` L22-27 和 `memory_extractor.py` L132）：
- `student_state` — 学生的状态/背景
- `concept_struggle` — 学生对某个概念的困难
- `concept_mastered` — 学生已掌握的概念
- `preference` — 学生的偏好
- `event` — 发生的事件
- `commitment` — 学生的承诺/目标

**Phase 2C 计划新增**：从教材提取知识点作为种子，这将是一个**全新的 fact_type**（暂定 `knowledge_seed`，尚未在代码中定义），让 AI 导师不仅知道"学生是谁"，还知道"这本教材要教什么"。

**此时存储变化**：
| 存储 | 变化 |
|------|------|
| 方式一（SQLite） | `materials` 表的 `parsed_content`（TEXT，~150KB）和 `analysis_result`（JSON）被填入 |

---

##### 场景 C：用户基于教材生成课程

**在哪里**：`WorldDetail.vue`，教材解析完成后出现"生成课程"按钮

```
用户点击"生成课程"按钮
    ↓
【前端】POST /materials/5/generate-course  { world_id: 1 }
    ↓
【后端 generate_course()】
    ① 读取 materials.analysis_result                         ← 方式一（SQLite）
    ↓
    ② INSERT courses 表:                                      ← 方式一（SQLite）
       id=10, name="Python Crash Course", world_id=1,
       source_material_id=5, meta={...}
    ↓
    ③ 为每个知识点创建 MemoryFact 种子（🆕 Phase 2C 新增逻辑）:  ← 方式一（SQLite）
       INSERT memory_facts (共 45 条):
         id=100: fact_type="knowledge_seed"（🆕 全新 fact_type）,
                 content="递归：函数调用自身的编程技术",
                 concept_tags=["递归","函数"], salience=0.9
         id=101: fact_type="knowledge_seed",
                 content="函数：封装可复用代码块",
                 concept_tags=["函数"], salience=0.8
         ...
       这些种子让 AI 导师知道教材覆盖了哪些知识点
       ⚠️ 注意：当前代码的种子来自 traveler 角色信息（见场景 B 说明），
       这里是 Phase 2C 新增的第二类种子——教材知识点种子
    ↓
    ④ 为每个知识点创建初始进度跟踪:                           ← 方式一（SQLite）
       INSERT progress_trackings (共 45 条):
         topic="递归", mastery_level=0
         topic="函数", mastery_level=0
         ...
    ↓
    ⑤ 确保 learner_profile 存在:                              ← 方式一（SQLite）
       若无则 INSERT learner_profiles:
         user_id=1, world_id=1, profile={level:"beginner"}
    ↓
    ⑥ 返回 { course_id: 10, knowledge_points_count: 45 }
```

**此时存储变化**：
| 存储 | 新增内容 |
|------|---------|
| 方式一（SQLite） | `courses` +1 行、`memory_facts` +45 行（种子）、`progress_trackings` +45 行、`learner_profiles` +1 行（若不存在） |

---

##### 场景 D：用户开始学习

**在哪里**：`WorldDetail.vue` 或 `CoursePage.vue`，点击"开始学习"

```
用户点击"开始学习"
    ↓
【前端】POST /courses/10/start  { world_id:1, sage_character_id:3, traveler_character_id:4 }
    ↓
【后端 start_learning()】
    ① INSERT sessions 表:                                     ← 方式一（SQLite）
       id=20, course_id=10, world_id=1,
       sage_character_id=3, traveler_character_id=4,
       relationship={ stage:"stranger", dimensions:{...} }
    ↓
    ② 查询 memory_facts:                                      ← 方式一（SQLite）
       SELECT * FROM memory_facts WHERE character_id=3
       ORDER BY salience DESC LIMIT 20
       → 得到 20 条种子事实（教材知识点）
    ↓
    ③ 构建 prompt: "你是苏格拉底，在赛博朋克世界中教授递归..."
       将 20 条种子事实注入 prompt 上下文
    ↓
    ④ 调用 LLM → 得到开场白
    ↓
    ⑤ INSERT chat_messages (第1条):                           ← 方式一（SQLite）
       session_id=20, sender_type="sage",
       content="欢迎来到数据之城，旅人。今天我们要学习一个强大的技术..."
    ↓
    ⑥ 返回 { session_id:20, message:{...} }
```

**此时存储变化**：
| 存储 | 新增内容 |
|------|---------|
| 方式一（SQLite） | `sessions` +1 行、`chat_messages` +1 行 |

---

##### 场景 E：用户在学习中对话

**在哪里**：`Learning.vue`（主学习界面）

```
用户输入"递归和循环有什么区别？"
    ↓
【前端】POST /courses/10/chat  { message:"递归和循环有什么区别？" }
    ↓
【后端 chat()】
    ① INSERT chat_messages (用户消息):                        ← 方式一（SQLite）
       session_id=20, sender_type="traveler",
       content="递归和循环有什么区别？"
    ↓
    ② 查询 memory_facts:                                      ← 方式一（SQLite）
       → 45 条种子事实 + 已有观察事实
       → 按相关度/salience 筛选 TOP 20
    ↓
    ③ 构建 prompt（含历史对话 + 记忆上下文）
    ↓
    ④ 调用 LLM → AI 导师回复
    ↓
    ⑤ INSERT chat_messages (AI回复):                          ← 方式一（SQLite）
       session_id=20, sender_type="sage",
       content="好问题！循环是重复执行，递归是函数调用自身..."
    ↓
    ⑥ 【记忆提取】从对话中提取新 MemoryFact:                   ← 方式一（SQLite）
       INSERT memory_facts:
         id=200, fact_type="concept_struggle",
         content="学生对递归和循环的区别存在困惑",
         salience=0.7
       → 这是"观察事实"，区别于教材的"种子事实"
    ↓
    ⑦ 【关系更新】更新 session.relationship:
       trust: 0.3→0.35 (互动积极)
    ↓
    ⑧ 【进度更新】UPDATE progress_trackings:
       topic="递归", mastery_level: 0→15
```

**此时存储变化**：
| 存储 | 新增/变化 |
|------|---------|
| 方式一（SQLite） | `chat_messages` +2 行、`memory_facts` +1 行（观察事实）、`sessions.relationship` 更新、`progress_trackings` 更新 |

---

##### 场景 F：用户存档

**在哪里**：`Learning.vue`，点击 HUD 栏的"存档"按钮

```
用户点击"存档"
    ↓
【前端】POST /checkpoints  { world_id:1, session_id:20, save_name:"第三章-递归入门" }
    ↓
【后端 create_checkpoint()】
    ① INSERT checkpoints 表:                                  ← 方式一（SQLite 索引）
       id=30, session_id=20, save_name="第三章-递归入门",
       state={ relationship:{...}, course_id:10 }
    ↓
    ② _build_full_save_data() 聚合多表数据:
       ├ sessions 表 → session_meta
       ├ chat_messages 表 → chat_history（20 条消息）
       ├ memory_facts 表 → memory_snapshot（45 种子 + 3 观察 = TOP 50）
       ├ progress_trackings 表 → progress_snapshot（"递归":15, "函数":30, ...）
       └ learner_profiles 表 → learner_profile_snapshot
    ↓
    ③ 写入 JSON 文件:                                         ← 方式二（存档文件）
       data/saves/1/checkpoint_30_20260424170000.json
       {
         "version": "2.0",
         "checkpoint_id": 30,
         "chat_history": [...20条消息...],
         "memory_snapshot": { facts: [...50条记忆...] },
         "progress_snapshot": { topics: [...45个知识点进度...] }
       }
    ↓
    ④ UPDATE checkpoints SET file_path="1/checkpoint_30_xxx.json",
       file_size_bytes=245760                                 ← 方式一（SQLite）
```

**此时存储变化**：
| 存储 | 新增内容 |
|------|---------|
| 方式一（SQLite） | `checkpoints` +1 行（含 file_path 索引） |
| 方式二（存档文件） | `data/saves/1/checkpoint_30_xxx.json`（~240KB） |

**注意**：存档中包含了教材种子事实（`memory_snapshot.facts` 中 `fact_type="knowledge_seed"` 的条目），这意味着**方式三的数据通过方式一的中转，最终也流入了方式二的存档文件**。

---

##### 全生命周期数据流总图

```
┌─────────────┐     上传        ┌──────────────┐
│   用户上传    │ ─────────────→ │ 方式三：文件存储 │ ← data/materials/1/xxx.pdf
│   PDF 教材    │                │ （原始文件保留） │
└─────────────┘                └──────┬───────┘
                                      │ 解析（读取文件）
                                      ↓
                              ┌──────────────┐
                              │  方式一：SQLite  │ ← materials.parsed_content (TEXT)
                              │  （结构化数据）  │ ← materials.analysis_result (JSON)
                              └──────┬───────┘
                                     │ 生成课程
                    ┌────────────────┼────────────────┐
                    ↓                ↓                ↓
              courses 表      memory_facts 表    progress_trackings
             （新课程）      （45条种子事实）     （45条初始进度）
                    │                │
                    │   开始学习      │  注入 prompt
                    ↓                ↓
              sessions 表 ←── 查询 memory_facts
                    │
                    │ 对话过程
                    ↓
              chat_messages 表  →  提取新 memory_facts（观察事实）
              sessions.relationship 更新
              progress_trackings.mastery_level 更新
                    │
                    │ 存档
                    ↓
          _build_full_save_data() 聚合 5 张表
                    │
                    ↓
          ┌──────────────┐
          │ 方式二：存档文件 │ ← data/saves/1/checkpoint_30_xxx.json
          │  （完整快照）   │    含 session_meta + chat_history +
          └──────────────┘    memory_snapshot + progress_snapshot
```


---

### 跨存储交互分析：三种方式如何协作

> 分析三种存储方式之间的数据流动关系，特别关注方式三加入后产生的新交互。

#### 交互矩阵

| 触发动作 | 涉及的存储方式 | 数据流 |
|---------|-------------|--------|
| 上传教材 | 三 → 一 | PDF 写入文件系统，元数据写入 SQLite |
| 解析教材 | 三 → 一 | 读取文件，提取文本写入 SQLite TEXT 列 |
| AI 分析 | 一 → LLM → 一 | 读 SQLite 文本，AI 返回 JSON 写入 SQLite |
| 生成课程 | 一 → 一 | SQLite analysis_result → 新建 Course 行 |
| 生成记忆种子 | 一 → 一 | SQLite analysis_result → 新建 MemoryFact 行 |
| 开始学习 | 一 → 一 | Course/Character → 新建 Session 行 |
| 对话过程 | 一 | ChatMessage 实时写入 SQLite |
| 记忆提取 | 一 → 一 | 对话内容 → 新建/更新 MemoryFact |
| 存档 | 一 → 二 | 多张表聚合 → 写入 JSON 文件 |
| 读档 | 二 → 一 | 读 JSON 文件 → 恢复 Session → 查询 SQLite |
| 分支 | 二 → 一 | 读存档 → 新建 Session + 复制 ChatMessage |
| 删除世界 | 一 + 二 + 三 | SQLite 级联删除 + 存档文件删除 + 教材文件删除 |

#### 关键交互详解

**1. 方式三 → 方式一：教材驱动课程生成**

这是最核心的新交互。教材上传后经过解析+AI分析，最终转化为方式一中的多张 SQLite 表数据：

```
Material（方式三文件 + 方式一元数据）
    ↓ generate_course()
    ├→ Course（方式一 courses 表）      ← 新建课程
    ├→ MemoryFact（方式一 memory_facts 表）← 知识图谱种子
    ├→ ProgressTracking（方式一）       ← 初始进度
    └→ LearnerProfile（方式一）         ← 若不存在则创建
```

**影响**：Phase 2C 完成后，SQLite 中 `courses` 表的数据来源从"用户手动创建"变为"AI 自动生成 + 手动创建"双入口。`memory_facts` 表也将新增一类数据：教材提取的"种子事实"（区别于对话中提取的"观察事实"）。

**2. 方式一 → 方式二：存档聚合方式三的数据**

Phase 2C 后，`_build_full_save_data()` 需要考虑教材相关的数据：

| 存档字段 | 当前来源 | Phase 2C 后新增 |
|---------|---------|---------------|
| session_meta | sessions 表 | 不变 |
| chat_history | chat_messages 表 | 不变 |
| memory_snapshot | memory_facts（按 character） | 🆕 需包含教材种子事实 |
| progress_snapshot | progress_trackings | 不变（但课程来源变为教材） |
| learner_profile_snapshot | learner_profiles | 不变 |
| | | 🆕 **material_snapshot**：可选，记录存档时的教材分析结果 |

**3. 方式三 + 方式二：教材文件与存档文件的存储基础设施共享**

两者都是文件存储，但特征不同：

| 维度 | 教材文件（方式三） | 存档文件（方式二） |
|------|----------------|----------------|
| 写入频率 | 一次性（上传时） | 每次存档 |
| 文件格式 | 二进制（PDF/EPUB） | JSON |
| 大小 | 1-50 MB | 1-10 MB |
| 关联元数据 | Material 表索引 | Checkpoint 表索引 |
| 是否需要 StorageBackend | ✅ 是（新功能应走统一接口） | ⚠️ 已有 SaveFileManager |

**结论**：Phase 2A 规划的 `StorageBackend` 统一抽象层应在方式三实现前就绪。`SaveFileManager` 可重构为其实现之一，教材文件存储作为另一个 `namespace`（`materials`）接入。

**4. 删除世界的级联影响**

Phase 2C 后，删除一个世界需要清理三种存储：

```
DELETE /worlds/{id}
    ↓ SQLite: CASCADE 删除 worlds, courses, sessions, chat_messages,
    ↓         memory_facts, progress_trackings, checkpoints, materials
    ↓ 文件: SaveFileManager 删除 data/saves/{uid}/ 中相关存档
    ↓ 文件: StorageBackend 删除 data/materials/{uid}/ 中相关教材
    ↓
    当前问题：删除世界时是否会清理存档文件和教材文件？
    → checkpoints 有 file_path，但 archive.py 删除世界时未检查
    → materials 表尚未实现，暂无问题
```


## 对比总结

| 维度 | SQLite 数据库 | 存档文件 | 教材文件 |
|------|-------------|---------|---------|
| **物理位置** | `data/socratic_learning.db` 单文件 | `data/saves/{uid}/` JSON 文件 | `data/materials/{uid}/` 原始文件 |
| **数据量** | 几百~几千条小记录 | 几十 MB/存档 | 几 MB~50 MB/文件 |
| **读写模式** | 高频、结构化查询 | 低频、整体读写 | 极低频、一次性写入 |
| **管理方式** | SQLAlchemy ORM | `SaveFileManager` 类 | 🆕 待建（将走 `StorageBackend`） |
| **适合场景** | 索引、元数据、需要 WHERE/JOIN 的数据 | 完整快照、大 JSON 块 | 二进制大文件、原始数据保留 |

---

## 概念澄清：全量记忆 vs 用户画像

> 参见 `plan.md` 中的「概念澄清与架构设计讨论」章节获取完整论述。

**关键区分**：

| 概念 | 是什么 | 存储位置 |
|------|--------|---------|
| **全量记忆**（Full Context） | `chat_messages` 表中的全部对话消息，按 `session_id` 查询后全量注入 API | SQLite `chat_messages` 表 |
| **用户画像**（User Profile） | 从对话中**抽象提取**的结构化认知事实（MemoryFact + LearnerProfile） | SQLite `memory_facts` + `learner_profiles` 表 |

- **全量记忆**用于同一次 Session 内的上下文连续性（AI 自然记得本次对话的所有内容）
- **MemoryFact**（用户画像的原子单元）用于跨 Session、跨课程、Token 压缩时的认知继承
- 两者互补，不是替代关系

**Token 压缩提示**：当对话历史超过模型上下文窗口的 80% 时，系统自动压缩旧消息为 MemoryFact 摘要，并在前端展示压缩通知（告知用户节省了多少 Token）。详见 `plan.md` 中的「Token 压缩提示」设计。

---

核心问题
与其说"记忆要不要迁移到文件"，不如问一个更根本的问题：我们需要什么样的存储基础设施？

当前有 3 个独立的存储入口（SQLite 直接操作、`SaveFileManager`、即将有的教材上传），没有一个统一的抽象层。

方案：统一存储抽象层 StorageBackend
设计一个 StorageBackend 接口，所有文件/大内容存储都走这个层：


# backend/services/storage.py

class StorageBackend(ABC):
    """统一存储后端接口"""
    
    @abstractmethod
    def write(self, namespace: str, key: str, data: bytes | str) -> str:
        """写入数据，返回存储路径/标识"""
    
    @abstractmethod
    def read(self, namespace: str, key: str) -> bytes | None:
        """读取数据"""
    
    @abstractmethod
    def delete(self, namespace: str, key: str) -> bool:
        """删除数据"""
    
    @abstractmethod
    def list_keys(self, namespace: str, prefix: str = "") -> list[str]:
        """列出某个命名空间下的所有键"""

class LocalFileStorage(StorageBackend):
    """本地文件系统实现（默认）"""
    # data/storage/{namespace}/{key}
    # 例: data/storage/memories/{char_id}_{fact_id}.json
    # 例: data/storage/materials/{user_id}_{material_id}.pdf
    # 例: data/storage/narratives/{world_id}.json
    # 例: data/storage/saves/{user_id}_{checkpoint_id}.json

class S3Storage(StorageBackend):
    """S3/MinIO 实现（未来可选）"""


namespace 设计：
• saves → 存档 JSON（替代现有 SaveFileManager）
• materials → 教材文件（PDF/TXT）
• memories → 记忆内容（从 SQLite 迁出）
• narratives → 叙事配置 JSON
• exports → 导出数据

MemoryFact 的具体迁移策略
迁移前（当前）：

SQLite memory_facts 表:
    id | character_id | fact_type | content | concept_tags | salience | ...
    1  | 3            | struggle  | "学生对递归..." | ["递归"] | 0.8 | ...


迁移后：

SQLite memory_facts 表 (只保留索引和元数据):
    id | character_id | fact_type | content_ref | concept_tags | salience | t_valid |
t_invalid | ...
    1  | 3            | struggle  | "memories/3_1.json" | ["递归"] | 0.8 | ... | NULL |
...

文件 data/storage/memories/3_1.json:
    {"content": "学生对递归终止条件理解有误，混淆了基准情形和递归步骤", ...}


但是——我要提出一个重要的问题：

MemoryFact 真的需要迁移到文件吗？
让我重新审视数据特征：

| 特征 | MemoryFact | 教材文件 | 存档 |
|------|-----------|---------|------|
| 单条大小 | 50-500 字 | 1-50 MB | 1-10 MB |
| 查询频率 | **每轮对话都查** | 上传时一次 | 读档时一次 |
| 查询复杂度 | 按 tags/salience/fact_type 过滤 | 按 ID | 按 ID |
| 写入频率 | 每轮对话可能写入 | 一次性 | 每次存档 |
| 总量级 | 几百条/用户 | 几个/世界 | 几十个/世界 |


关键洞察：MemoryFact 的特征其实是高查询频率 + 小条目 +
结构化查询——这恰恰是关系型数据库擅长的场景。而教材文件和存档才是文件存储的典型场景。

修正方案

SQLite（结构化索引 + 高频查询）：
    ✅ MemoryFact 全部字段（content 留在 SQLite）
    ✅ 新增 t_valid/t_invalid 时态字段
    ✅ 新增 recall_count 追踪
    ✅ concept_tags JSON 索引

文件存储（大内容 + 低频访问）：
    ✅ Checkpoint 存档（已有 SaveFileManager）
    ✅ 教材文件（Phase 2C 新建）
    ✅ 叙事配置（Phase 2D 新建）

统一抽象层 StorageBackend：
    ✅ 统一管理所有文件存储
    ✅ 重构 SaveFileManager 为其实现之一


换言之：MemoryFact 不迁移到文件，但其他文件存储统一到 StorageBackend。

对 Phase 2A 的影响
Phase 2A 不做存储介质迁移，但做两件事：
1. A5 时态字段激活（t_valid/t_invalid）— 在 SQLite 中加列
2. 新增 A6：StorageBackend 基础设施 — 为 Phase 2C/2D 铺路