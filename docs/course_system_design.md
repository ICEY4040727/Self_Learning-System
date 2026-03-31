# 世界系统 + 双角色模型 + 三层记忆架构 — 技术设计文档

> **文档类型**：Reviewer 架构设计（Owner 确认后 Creator 实施）
> **关联**：design_UI.md、galgame_visual_guide.md
> **日期**：2026-03-29（v2，基于 Owner 确认的世界观、存档方案、记忆架构）
> **前提**：Galgame UI 重构基本完成后执行

---

## 一、核心概念

### World（世界）— 取代原 Course

World 是用户进入的**完整沉浸式环境**——有自己的世界观、场景、角色。在 Galgame 中，World 就是"游戏"本身。

```
World "雅典学院"
├── 世界观：古希腊哲学之城，阳光石柱广场
├── 场景集：学院回廊、市集、橄榄树下
├── Characters
│   ├── 苏格拉底 (sage，知者)
│   └── 我 (traveler，旅者)
├── Courses
│   ├── 哲学导论
│   ├── 逻辑学
│   └── 伦理学
├── 关系阶段 → 跨所有课程统一
├── 记忆 → 跨所有课程统一
└── 回忆库（存档）→ 按 World 组织
```

### Course（课程）— 取代原 Subject

World 中的具体学习内容。一个 World 可以有多门课程。课程不限于传统学科——可以是"战略思维"、"谈判术"、任何要学的东西。

数据库：原 `subjects` 表重命名为 `courses`（Migration 中执行 `ALTER TABLE subjects RENAME TO courses`）。

### Character 双角色

| 类型 | 角色 | 说明 |
|------|------|------|
| sage（知者） | 教师 | 有 TeacherPersona、立绘、表情切换 |
| traveler（旅者） | 用户自己 | 可上传立绘，无则显示默认；不生成内心独白 |

一个 World 可以有多个 sage（如"三国"中诸葛亮+赵云都可以教学）。

### 设计决策（Owner 确认）

1. 旅者可上传立绘，无则显示默认图片
2. 回忆库需要场景缩略图
3. "进度"概念另议
4. 允许一个 World 有多个 sage
5. 旅者无内心独白——旅者就是用户本人
6. 存档基于版本控制模型（COMMIT/BRANCH，不是快照覆盖）

---

## 二、数据模型

### 当前 → 目标对比

```
当前：
User → Character → Course → Session → ChatMessage
                 → TeacherPersona ↗

目标：
User → World ←→ Character (多对多，via WorldCharacter)
         ↓           ↓
       Course     type: "traveler" | "sage"
         ↓
       Session (时间线，可分叉)
         ↓
       ChatMessage
         ↓
    三层记忆：PostgreSQL + ChromaDB(时态) + Neo4j(知识图谱)
```

### 新增表

#### `worlds` 表

```sql
worlds
├── id              INTEGER PRIMARY KEY
├── tenant_id       INTEGER FK → tenants.id
├── user_id         INTEGER FK → users.id
├── name            VARCHAR(100) NOT NULL      -- "雅典学院"
├── description     TEXT                       -- 世界观描述
├── scene_backgrounds JSON                     -- {"default": "url", "library": "url", "garden": "url"}
├── created_at      DATETIME
```

注意：`scene_backgrounds` 是 JSON（一个 World 有多个场景），不是单个 String。

#### `world_characters` 多对多中间表

```sql
world_characters
├── id              INTEGER PRIMARY KEY
├── world_id        INTEGER FK → worlds.id
├── character_id    INTEGER FK → characters.id
├── role            VARCHAR(20) NOT NULL       -- "traveler" | "sage"
├── is_primary      BOOLEAN DEFAULT FALSE      -- 主角色标记
└── UNIQUE(world_id, character_id)
```

### 修改表

#### `characters` 新增

```sql
+ type  VARCHAR(20) DEFAULT 'sage'   -- "traveler" | "sage"
```

现有 Character 全部默认 `type = 'sage'`。

#### `courses`（原 `subjects`）新增

```sql
+ world_id  INTEGER FK → worlds.id (nullable，迁移期间)
-- character_id 保留，迁移完成后删除
-- scene_background 保留，迁移到 World 后删除
```

#### `sessions` 新增（支持分叉）

```sql
+ world_id               INTEGER FK → worlds.id
+ sage_character_id       INTEGER FK → characters.id
+ traveler_character_id   INTEGER FK → characters.id
+ parent_checkpoint_id    INTEGER FK → saves.id    -- 从哪个检查点分叉（NULL=根时间线）
+ branch_name             VARCHAR(100)              -- 可选，用户命名
```

#### `saves` 改造（检查点模型）

```sql
saves（重新定义为检查点）
├── id                    INTEGER PRIMARY KEY
├── user_id               INTEGER FK → users.id
├── world_id              INTEGER FK → worlds.id        -- 替代原 subject_id
├── session_id            INTEGER FK → sessions.id      -- 属于哪个时间线
├── save_name             VARCHAR(100)
├── message_index         INTEGER                        -- 对话到第几条
├── checkpoint_timestamp  DATETIME                       -- 精确时间点
├── state_snapshot        JSON                           -- 见下
├── thumbnail_path        VARCHAR(255)                   -- 场景缩略图
├── created_at            DATETIME

-- state_snapshot:
{
  "relationship_stage": "friend",
  "emotion": "curiosity",
  "expression": "thinking",
  "scene_key": "garden",
  "sage_character_id": 1,
  "traveler_character_id": 2,
  "last_teacher_reply": "你觉得这个定理...",
  "course_id": 3,
  "valid_memory_ids": ["mem_001", "mem_002"]
}
```

---

## 三、三层记忆架构

### 总览

```
┌─ PostgreSQL（关系层）─────────────────────────┐
│ chat_messages: 情景记忆（完整对话记录）          │
│ sessions: 时间线（含分叉关系）                  │
│ saves: 检查点（版本控制式存档）                  │
│ learner_profiles: 事实记忆（跨时间线累积）       │
└──────────────────────────────────────────────┘
              ↕ 双向关联
┌─ ChromaDB（向量层）──────────────────────────┐
│ 语义记忆：从对话中提取的认知摘要                 │
│ 每条记忆带:                                    │
│   t_valid: 认知形成时间                        │
│   t_invalid: 认知被推翻时间（NULL=仍有效）       │
│   episode_id: 来源消息 ID                      │
│   concept_ids: 关联的知识图谱节点 ID            │
└──────────────────────────────────────────────┘
              ↕ 概念 ID 关联
┌─ Neo4j（图层）───────────────────────────────┐
│ 概念节点: (Concept {name, mastery, t_updated})│
│ 关系边（带时态）:                               │
│   prerequisite_of — A 是 B 的前置知识           │
│   builds_on      — A 在 B 基础上深化            │
│   contradicts    — A 和 B 矛盾                 │
│   example_of     — A 是 B 的实例                │
│ 时态属性:                                      │
│   edge.t_valid   — 关系何时被发现               │
│   edge.t_invalid — 何时被推翻                   │
└──────────────────────────────────────────────┘
```

### 第 1 层：工作记忆（每轮重建，不存储）

**是什么**：发送给 LLM 的完整 prompt，从其他三层提取数据临时组装。

**组装过程**（`learning_engine.build_system_prompt()`）：
```
静态层:
  教师人格模板（来自 TeacherPersona）
  苏格拉底教学法规则（硬编码）
  Mermaid 图表指南（硬编码）

动态层（每轮不同）:
  ① 关系阶段指令 ← Session.relationship_stage
  ② 脚手架等级    ← 由 emotion + mastery 计算
  ③ 学习者画像    ← LearnerProfile（第 4 层事实记忆）
  ④ 相关语义记忆  ← ChromaDB 混合检索（第 3 层）
  ⑤ 知识图谱上下文 ← Neo4j 图遍历（第 3 层）

对话历史:
  最近 N 条 chat_messages ← PostgreSQL（第 2 层情景记忆）
```

### 第 2 层：情景记忆（PostgreSQL `chat_messages`）

**是什么**：一次对话的完整记录。按时间线（Session）隔离。

**数据结构**：
```sql
chat_messages
├── id               INTEGER PRIMARY KEY
├── session_id       INTEGER FK → sessions.id
├── sender_type      VARCHAR(20)          -- "user" | "teacher"
├── content          TEXT
├── timestamp        DATETIME
├── emotion_analysis JSON                 -- {"emotion_type": "curiosity", "valence": 0.7}
└── used_memory_ids  JSON                 -- ["mem_001"] 本轮检索到的语义记忆
```

**检索**：`SELECT * FROM chat_messages WHERE session_id = ? ORDER BY timestamp`

**与存档的关系**：检查点记录 `message_index`。分叉时复制该 index 之前的消息到新 Session。

### 第 3 层：语义记忆（ChromaDB 时态向量）+ 知识图谱（Neo4j）

**语义记忆（ChromaDB）**——每条是从对话中提取的认知摘要：

```
Collection: "learning_memories"

id:        "mem_003"
document:  "学生理解了递归基本概念，能正确写出阶乘函数，但对终止条件的必要性需更多引导"
metadata:  {
  "user_id": 1,
  "world_id": 1,
  "session_id": 5,
  "episode_id": 42,              -- 来源消息 ID（溯源）
  "t_valid": "2026-03-29T16:30", -- 认知形成时间
  "t_invalid": null,             -- NULL=仍有效；被推翻时填入时间
  "concept_ids": ["c_recursion", "c_termination"],
  "memory_type": "learning_insight"
}
embedding: FLOAT[384]             -- 自动生成
```

**知识图谱（Neo4j）**——概念之间的结构化关系：

```cypher
-- 概念节点
(:Concept {id: "c_recursion", name: "递归", user_id: 1, world_id: 1,
           mastery: 0.7, t_updated: "2026-03-29T16:35"})

(:Concept {id: "c_termination", name: "终止条件", user_id: 1, world_id: 1,
           mastery: 0.3, t_updated: "2026-03-29T16:35"})

-- 关系边（带时态）
(c_recursion)-[:PREREQUISITE_OF {t_valid: "2026-03-29T16:30", t_invalid: null}]->(c_termination)
(c_factorial)-[:EXAMPLE_OF {t_valid: "2026-03-29T16:32", t_invalid: null}]->(c_recursion)
```

**混合检索（每轮对话时）**：

```python
async def retrieve_context(user_message, session):
    checkpoint_time = session.created_from_checkpoint_time or datetime.max

    # 1. ChromaDB 语义搜索（时态过滤）
    vector_results = chromadb.query(
        query_texts=[user_message],
        n_results=5,
        where={
            "user_id": user_id,
            "world_id": world_id,
            "t_valid": {"$lte": checkpoint_time},
            "$or": [
                {"t_invalid": None},
                {"t_invalid": {"$gt": checkpoint_time}}
            ]
        }
    )

    # 2. Neo4j 图遍历（从命中概念出发，找关联）
    concept_ids = extract_concept_ids(vector_results)
    graph_context = neo4j.query("""
        MATCH (c:Concept)-[r*1..2]-(related:Concept)
        WHERE c.id IN $ids AND c.user_id = $uid
          AND r.t_valid <= $time
          AND (r.t_invalid IS NULL OR r.t_invalid > $time)
        RETURN related.name, related.mastery, type(r)
    """, ids=concept_ids, uid=user_id, time=checkpoint_time)

    # 3. 合并
    return format_context(vector_results, graph_context)
```

### 第 4 层：事实记忆（PostgreSQL `learner_profiles`）

**是什么**：跨所有时间线累积的学习者画像。只增长不回滚。

**数据结构**：
```sql
learner_profiles
├── user_id          INTEGER FK → users.id
├── course_id        INTEGER FK → courses.id (nullable)
├── learning_style   JSON    -- {"visual": 0.7, "auditory": 0.3}
├── cognitive_traits JSON    -- {"abstraction": "high"}
├── emotional_traits JSON    -- {"frustration_tolerance": "low"}
├── knowledge_graph  JSON    -- 简化版，Neo4j 的摘要
└── updated_at       DATETIME
```

**与存档的关系**：检查点保存快照，但读档时**不回滚**。多条时间线的学习成果都累积到同一个 Profile。

---

## 四、存档系统（版本控制模型）

### COMMIT（存档）

```python
async def create_checkpoint(session_id, save_name, user):
    session = db.query(Session).get(session_id)
    messages = get_messages(session_id)
    last_teacher = find_last_teacher_message(messages)

    # 1. 保存对话状态
    checkpoint = Save(
        user_id=user.id,
        world_id=session.world_id,
        session_id=session_id,
        save_name=save_name,
        message_index=len(messages),
        checkpoint_timestamp=datetime.utcnow(),
        state_snapshot={
            "relationship_stage": session.relationship_stage,
            "emotion": last_teacher.emotion_analysis.get("emotion_type"),
            "expression": EXPRESSION_MAP.get(emotion, "default"),
            "scene_key": current_scene_key,
            "last_teacher_reply": last_teacher.content[:100],
            "course_id": session.course_id,
        }
    )

    # 2. 记录有效语义记忆 ID（时态快照）
    checkpoint.state_snapshot["valid_memory_ids"] = get_valid_memory_ids(
        user_id, checkpoint.checkpoint_timestamp
    )

    db.add(checkpoint)
    db.commit()
```

### BRANCH（读档 = 从检查点分叉）

```python
async def load_checkpoint(checkpoint_id, user):
    checkpoint = db.query(Save).get(checkpoint_id)

    # 1. 创建新 Session（分叉）
    new_session = Session(
        world_id=checkpoint.world_id,
        course_id=checkpoint.state_snapshot["course_id"],
        user_id=user.id,
        relationship_stage=checkpoint.state_snapshot["relationship_stage"],
        parent_checkpoint_id=checkpoint.id,
        sage_character_id=checkpoint.state_snapshot.get("sage_character_id"),
        traveler_character_id=checkpoint.state_snapshot.get("traveler_character_id"),
    )
    db.add(new_session)
    db.flush()

    # 2. 复制检查点之前的消息到新时间线
    old_messages = get_messages(
        checkpoint.session_id,
        limit=checkpoint.message_index
    )
    for msg in old_messages:
        db.add(ChatMessage(
            session_id=new_session.id,
            sender_type=msg.sender_type,
            content=msg.content,
            timestamp=msg.timestamp,
            emotion_analysis=msg.emotion_analysis,
        ))

    db.commit()
    # 3. 新时间线的语义检索自动按 checkpoint_timestamp 过滤
    return new_session
```

### 回忆库 UI

```
┌─ World: 雅典学院 ──────────────────────┐
│                                        │
│  📌 主时间线                            │
│  ├── "初见苏格拉底"  msg#1-20           │
│  │    2026-03-28 | 陌生人 | 平静        │
│  │    「你好，我是苏格拉底...」          │
│  │                                      │
│  └── "逻辑突破"  msg#21-45             │
│       2026-03-29 | 朋友 | 兴奋          │
│       「你刚才的推理非常精彩！」          │
│                                        │
│  📌 从"初见苏格拉底"分叉的时间线        │
│  └── "换个话题"  msg#1-20 + 新对话      │
│       2026-03-30 | 熟人 | 好奇          │
│       「我们来聊聊伦理学吧」             │
│                                        │
│  [+ 新的旅程]                           │
└────────────────────────────────────────┘
```

---

## 五、API 变更

### 新增

| 端点 | 说明 |
|------|------|
| `POST /api/worlds` | 创建世界 |
| `GET /api/worlds` | 列出用户的世界 |
| `GET /api/worlds/{id}` | 世界详情（含角色、科目） |
| `PUT /api/worlds/{id}` | 更新世界 |
| `DELETE /api/worlds/{id}` | 删除世界 |
| `POST /api/worlds/{id}/characters` | 为世界添加角色 |
| `DELETE /api/worlds/{id}/characters/{cid}` | 从世界移除角色 |
| `GET /api/worlds/{id}/timelines` | 获取世界的所有时间线（Session 列表） |
| `GET /api/worlds/{id}/checkpoints` | 获取世界的回忆库（存档列表） |
| `POST /api/checkpoints` | 创建检查点（COMMIT） |
| `POST /api/checkpoints/{id}/branch` | 从检查点分叉（BRANCH） |

### 修改

| 端点 | 变更 |
|------|------|
| `POST /courses/{id}/start` | 增加 `world_id`；返回 `sage_sprites` + `traveler_sprites` + `scene_backgrounds` |
| `POST /courses/{id}/chat` | 语义检索增加时态过滤 + Neo4j 图遍历 |

---

## 六、前端变更

### Home.vue — 世界入口

```
主菜单 → "开始学习" → 世界列表（"雅典学院" / "三国军帐" / ...）
                        ↓
                    选择世界 → 回忆库
                                ↓
                            选择时间线 或 "新的旅程"
                                ↓
                            选择科目（对话框选择）
                                ↓
                            进入 Learning.vue
```

### Learning.vue — 双角色

```
┌─────────────────────────────────┐
│          世界场景背景              │
│                                 │
│   ┌───┐              ┌───┐     │
│   │知者│              │旅者│     │
│   │左侧│              │右侧│     │
│   └───┘              └───┘     │
│                                 │
│ ┌─────────────────────────────┐ │
│ │    对话框（名牌切换）         │ │
│ └─────────────────────────────┘ │
│ [HUD]                           │
└─────────────────────────────────┘
```

---

## 七、Migration 策略（4 步渐进）

### Migration 003: 新增（非破坏性）

- 创建 `worlds` 表
- 创建 `world_characters` 表
- `characters` 加 `type` 字段（default='sage'）
- 原 `subjects` 重命名为 `courses` + 加 `world_id`（nullable）
- `sessions` 加 `world_id` + `sage_character_id` + `traveler_character_id` + `parent_checkpoint_id`
- `saves` 加 `world_id` + `message_index` + `checkpoint_timestamp` + `state_snapshot` + `thumbnail_path`

### Migration 004: 数据迁移

- 为每个 Character 自动创建 World
- 建立 WorldCharacter 关联
- courses.world_id 回填
- Session/Save 的 world_id 回填

### Migration 005: 激活 Neo4j

- `KNOWLEDGE_GRAPH_ENABLED=true`
- ChromaDB metadata 增加 `t_valid` / `t_invalid` / `concept_ids`

### Migration 006: 清理（高风险，最后执行）

- `courses.character_id` 删除
- `courses.scene_background` 删除
- `saves` 旧字段清理

---

## 八、实施顺序

```
Phase 1: 后端模型扩展
  ├── Migration 003（新增表和字段）
  ├── World CRUD API
  ├── WorldCharacter 关联 API
  └── 检查点 COMMIT/BRANCH API

Phase 2: 数据迁移 + 记忆架构
  ├── Migration 004（自动迁移数据）
  ├── Migration 005（激活 Neo4j + ChromaDB 时态）
  ├── 混合检索（ChromaDB + Neo4j）
  └── learning_engine 集成

Phase 3: 前端迁移
  ├── Home.vue 世界入口
  ├── Learning.vue 双角色布局
  ├── Character.vue 角色类型
  └── 回忆库 UI

Phase 4: 清理
  ├── Migration 006
  ├── 旧 API deprecated
  └── 文档更新
```

---

## 九、风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| Neo4j 增加部署复杂度 | 运维负担 | Docker profile 可选启用；不启用时 fallback 到纯 ChromaDB |
| 三层记忆检索延迟 | 对话响应变慢 | 向量搜索和图遍历并行执行；设超时 fallback |
| Migration 004 数据迁移出错 | 数据丢失 | 先备份；migration 有 downgrade |
| 双角色布局移动端拥挤 | 体验差 | 移动端只显示当前说话的角色 |
| 旅者 prompt 设计 | 影响对话质量 | 旅者无内心独白，只是视觉存在 |

---

*本文档由 Reviewer 编写。Owner 已确认核心概念（World、版本控制存档、三层记忆）。待 Owner 最终审批后拆分为独立 Issue，Creator 按 Phase 顺序实施。*
