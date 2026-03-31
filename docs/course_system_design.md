# World 系统架构设计

> **文档类型**：Reviewer 架构设计（Owner 确认后 Creator 实施）
> **日期**：2026-03-31（v3，整合 SQLite 单文件 + JSON 列存储方案）
> **已确认决策**：World 概念、双角色、版本控制式存档、SQLite 单文件存储、知识图谱 JSON 列、去掉 ChromaDB/Neo4j/PostgreSQL

---

## 一、核心概念

### 1.1 三个实体

**World（世界）**：用户进入的完整沉浸式环境——自己的世界观、场景集、角色组合。在 Galgame 中就是"一个游戏"。

**Course（课程）**：World 中的学习内容。不限于传统学科，可以是"战略思维"、"谈判术"、任何要学的东西。一个 World 下多门课程。

**Character（角色）**：分两类。Sage（知者）= 教师，有人格模板和立绘。Traveler（旅者）= 用户本人，可有立绘但不生成内心独白。一个 World 可有多个 Sage。

```
World "雅典学院"
├── 世界观：古希腊哲学之城
├── 场景集：{academy: "学院回廊.jpg", market: "市集.jpg", garden: "橄榄树下.jpg"}
├── Characters
│   ├── 苏格拉底 (sage) ← 有 TeacherPersona
│   ├── 柏拉图 (sage)   ← 有 TeacherPersona
│   └── 我 (traveler)
├── Courses
│   ├── 哲学导论
│   ├── 逻辑学
│   └── 伦理学
├── Knowledge（知识图谱）→ 跨所有课程统一，JSON 列
├── 关系阶段 → 跨所有课程统一
└── 回忆库（检查点 + 时间线分叉）→ 按 World 组织
```

### 1.2 已确认设计决策

1. 旅者可上传立绘，无则显示默认图片
2. 回忆库需要场景缩略图
3. 允许一个 World 有多个 Sage
4. 旅者无内心独白——旅者就是用户本人
5. 存档基于版本控制模型（COMMIT/BRANCH，不覆盖）
6. 存储：SQLite 单文件，知识图谱用 JSON 列
7. 去掉 ChromaDB 和 Neo4j

---

## 二、存储架构

### 2.1 单文件 SQLite

所有数据存在一个 `socratic_learning.db` 文件中。

**为什么不用 PostgreSQL**：个人本地应用，单用户，无需独立数据库服务。SQLite 嵌入应用内，零配置。

**为什么不用纯 JSON 文件**：对话消息会无限增长（数千条），JSON 文件每次追加需全量读写。SQLite 追加一行不需要读取已有数据。

**为什么知识图谱用 JSON 列而不是关系表**：知识图谱是图结构，拆成 nodes 表 + edges 表再 JOIN 是用错误的模型存正确的数据。JSON 列直接存图对象，读出来直接给 LLM 推理、给 D3 渲染，不需要 SQL→JSON 的转换。

**为什么不用 ChromaDB**：个人知识图谱几十到几百个概念，不需要向量索引加速。LLM 本身就是最好的语义匹配引擎——给它整个知识图谱 JSON，它自己判断哪些概念与当前问题相关。

### 2.2 表结构总览

```
socratic_learning.db
│
├── users               # 用户认证
├── worlds              # 世界定义（JSON 列存场景集）
├── world_characters    # 世界-角色多对多
├── characters          # 角色定义（JSON 列存 sprites）
├── teacher_personas    # 教师人格模板
├── courses             # 课程定义（原 subjects）
├── sessions            # 时间线（含分叉指针）
├── chat_messages       # 对话消息（高频追加，行存储）
├── checkpoints         # 检查点/存档（JSON 列存状态快照）
├── knowledge           # 知识图谱（JSON 列存整个图）
├── learner_profiles    # 学习者画像（JSON 列）
├── fsrs_states         # 间隔重复状态（原子读写）
└── learning_diaries    # 学习日记
```

### 2.3 每张表的详细设计

#### users（认证）

```sql
CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    encrypted_api_key TEXT,        -- LLM API Key（加密存储）
    default_provider TEXT,         -- "claude" | "openai" | "ollama"
    created_at  TEXT DEFAULT (datetime('now'))
);
```

**存储原因**：密码哈希需要索引查找（按 username），认证是事务性操作。
**简化**：去掉 `tenant_id`（单用户本地应用不需要多租户）。

#### worlds（世界定义）

```sql
CREATE TABLE worlds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    name        TEXT NOT NULL,               -- "雅典学院"
    description TEXT,                        -- 世界观描述
    scenes      JSON DEFAULT '{}',           -- {"academy":"path","market":"path","garden":"path"}
    created_at  TEXT DEFAULT (datetime('now'))
);
```

**scenes 用 JSON 列**：一个 World 有 N 个场景，数量不固定。JSON 比建子表简单。读取时 `json_extract(scenes, '$.academy')` 取单个场景。

**一条实际数据**：
```json
{
  "id": 1,
  "name": "雅典学院",
  "description": "古希腊哲学之城，阳光下的石柱广场，思想在这里自由碰撞",
  "scenes": {
    "academy": "/assets/scenes/academy.jpg",
    "market": "/assets/scenes/market.jpg",
    "garden": "/assets/scenes/garden.jpg"
  }
}
```

#### characters（角色定义）

```sql
CREATE TABLE characters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    name        TEXT NOT NULL,               -- "苏格拉底"
    type        TEXT DEFAULT 'sage',         -- "sage" | "traveler"
    personality TEXT,                        -- 性格描述
    background  TEXT,                        -- 角色背景
    speech_style TEXT,                       -- 说话风格
    sprites     JSON DEFAULT '{}',           -- {"default":"path","happy":"path","thinking":"path","concerned":"path"}
    created_at  TEXT DEFAULT (datetime('now'))
);
```

**不变的字段**：和当前基本一致。新增 `type` 区分知者/旅者。

#### world_characters（世界-角色关联）

```sql
CREATE TABLE world_characters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id      INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
    character_id  INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    role          TEXT NOT NULL,              -- "sage" | "traveler"
    is_primary    INTEGER DEFAULT 0,         -- 1=主角色
    UNIQUE(world_id, character_id)
);
```

**为什么用中间表**：World 和 Character 是多对多——同一个"苏格拉底"可以出现在"雅典学院"和"古罗马议事堂"两个世界中。

#### teacher_personas（教师人格）

```sql
CREATE TABLE teacher_personas (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id            INTEGER REFERENCES characters(id) ON DELETE CASCADE,
    name                    TEXT NOT NULL,           -- "默认人格"
    version                 TEXT DEFAULT '1.0',
    traits                  JSON,                    -- ["温和","反问","哲学思维"]
    system_prompt_template  TEXT,                     -- 人格描述（2-4句）
    is_active               INTEGER DEFAULT 0,
    created_at              TEXT DEFAULT (datetime('now'))
);
```

**不变**：和当前基本一致。去掉 `tenant_id`。

#### courses（课程，原 subjects）

```sql
CREATE TABLE courses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id    INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,               -- "哲学导论"
    description TEXT,
    target_level TEXT,                       -- "理解基本概念"
    created_at  TEXT DEFAULT (datetime('now'))
);
```

**变化**：`character_id` FK 改为 `world_id` FK。`scene_background` 移到 World。

#### sessions（时间线）

```sql
CREATE TABLE sessions (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id                INTEGER REFERENCES worlds(id),
    course_id               INTEGER REFERENCES courses(id),
    user_id                 INTEGER REFERENCES users(id),
    sage_character_id       INTEGER REFERENCES characters(id),
    traveler_character_id   INTEGER REFERENCES characters(id),
    teacher_persona_id      INTEGER REFERENCES teacher_personas(id),
    relationship_stage      TEXT DEFAULT 'stranger',
    parent_checkpoint_id    INTEGER REFERENCES checkpoints(id),  -- 分叉来源（NULL=根时间线）
    branch_name             TEXT,                                -- 可选，用户命名
    started_at              TEXT DEFAULT (datetime('now')),
    ended_at                TEXT
);
```

**新增字段说明**：
- `sage_character_id` + `traveler_character_id`：明确记录本次对话的两个角色
- `parent_checkpoint_id`：不为 NULL 时表示这是从某个检查点分叉出来的时间线
- `branch_name`：用户给分叉命名（如"换个思路"）

#### chat_messages（对话消息）

```sql
CREATE TABLE chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    sender_type     TEXT NOT NULL,            -- "user" | "sage"
    content         TEXT NOT NULL,
    emotion_analysis JSON,                    -- {"emotion_type":"curiosity","valence":0.7,"confidence":0.85}
    timestamp       TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_messages_session ON chat_messages(session_id);
```

**为什么是 SQLite 行存储**：这是唯一会无限增长的表。每轮对话 INSERT 一行，不需要读取已有数据。索引保证按 session_id 查询是 O(log N)。

#### checkpoints（检查点/存档）

```sql
CREATE TABLE checkpoints (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER REFERENCES users(id),
    world_id            INTEGER REFERENCES worlds(id),
    session_id          INTEGER REFERENCES sessions(id),
    save_name           TEXT NOT NULL,            -- "逻辑突破"
    message_index       INTEGER NOT NULL,         -- 对话到第几条
    state               JSON NOT NULL,            -- 状态快照（见下）
    thumbnail_path      TEXT,                     -- 场景缩略图路径
    created_at          TEXT DEFAULT (datetime('now'))
);
```

**state JSON 内容**：
```json
{
  "relationship_stage": "friend",
  "emotion": "curiosity",
  "expression": "thinking",
  "scene_key": "garden",
  "sage_character_id": 1,
  "traveler_character_id": 3,
  "course_id": 2,
  "last_reply_preview": "你刚才的推理非常精彩！"
}
```

**为什么 state 用 JSON 列**：快照是一次写入、偶尔读取的文档。字段组合随版本可能变化。JSON 列比固定列更灵活。

#### knowledge（知识图谱）

```sql
CREATE TABLE knowledge (
    world_id    INTEGER PRIMARY KEY REFERENCES worlds(id),
    graph       JSON NOT NULL DEFAULT '{}'
);
```

**一个 World 一行。整个知识图谱是一个 JSON 对象。**

**graph JSON 结构**（7 种记忆分类，详见 `learning_memory_theory.md`）：

```json
{
  "concepts": {
    "recursion": {
      "type": "knowledge",
      "name": "递归",
      "mastery": 0.7,
      "bloom_level": "apply",
      "content": "理解了递归是函数调用自身来解决子问题的方法，能写阶乘函数",
      "t_valid": "2026-03-29T16:30",
      "t_invalid": null,
      "episodes": ["session:5#msg:15", "session:5#msg:22"],
      "edges": {
        "termination": {"type": "prerequisite_of", "t_valid": "2026-03-29T16:35"},
        "factorial": {"type": "example_of", "t_valid": "2026-03-29T16:32"},
        "iteration": {"type": "alternative_to", "t_valid": "2026-03-29T16:40"}
      }
    },
    "recursion_misconception_1": {
      "type": "misconception",
      "name": "递归必须函数自调用",
      "severity": "moderate",
      "related_concept": "recursion",
      "content": "学生认为递归只能通过函数调用自身实现，不知道可以用栈模拟",
      "t_valid": "2026-03-29T16:32",
      "t_invalid": "2026-03-29T17:15",
      "corrected_by": "session:5#msg:45"
    },
    "write_recursive_function": {
      "type": "skill",
      "name": "编写递归函数",
      "proficiency": 0.6,
      "related_concept": "recursion",
      "content": "能写阶乘和斐波那契，但复杂递归（树遍历）仍需引导",
      "demonstrations": ["session:5#msg:30", "session:5#msg:38"],
      "t_valid": "2026-03-29T16:35",
      "t_invalid": null
    },
    "termination": {
      "type": "knowledge",
      "name": "终止条件",
      "mastery": 0.3,
      "bloom_level": "remember",
      "content": "能说出需要终止条件，但不清楚为什么没有终止条件会导致栈溢出",
      "t_valid": "2026-03-29T16:35",
      "t_invalid": null,
      "episodes": ["session:5#msg:23"],
      "edges": {}
    }
  },
  "episodes": [
    {
      "type": "episode",
      "session_id": 5,
      "message_range": [30, 38],
      "t_valid": "2026-03-29T16:45",
      "summary": "学生通过阶乘例子理解了为什么需要 base case。关键转折：教师问'如果没有终止条件会怎样'，学生自己推导出无限递归→栈溢出",
      "significance": "breakthrough",
      "related_concepts": ["recursion", "termination"]
    }
  ]
}
```

**type 字段值域**（来源见 `learning_memory_theory.md`）：

| type | 来源理论 | 含义 | 时态行为 |
|------|---------|------|---------|
| `knowledge` | Bloom Factual/Conceptual + ITS Overlay | 事实/概念知识 + 掌握度 | 随存档回滚 |
| `misconception` | ITS Perturbation Model | 错误认知（比"不知道"更危险） | 随存档回滚 |
| `skill` | Bloom Procedural + KT Skill | 程序性能力（能做什么） | 随存档回滚 |
| `episode` | 认知科学 Episodic Memory | 关键交互事件摘要 | 随存档回滚 |

**bloom_level**（仅 knowledge 类型）：`remember` → `understand` → `apply` → `analyze` → `evaluate` → `create`

**severity**（仅 misconception 类型）：`minor`（表述不精确）/ `moderate`（导致错误但可局部纠正）/ `critical`（根本性错误）

**significance**（仅 episode 类型）：`breakthrough` / `struggle` / `correction` / `connection`

**边关系类型**：
| 关系 | 教学意义 |
|------|---------|
| `prerequisite_of` | 学 B 之前要先会 A |
| `builds_on` | B 在 A 基础上深化 |
| `example_of` | A 是 B 的具体实例 |
| `alternative_to` | A 和 B 是不同方法 |
| `contradicts` | A 和 B 矛盾 |
| `part_of` | A 是 B 的组成部分 |
```

**为什么一个 World 只有一行**：
- 一个 World 的知识概念最多几百个，JSON 几十 KB
- 读取：`SELECT graph FROM knowledge WHERE world_id = ?` → 一次查询拿到整个图
- 更新单概念掌握度：`UPDATE knowledge SET graph = json_set(graph, '$.concepts.recursion.mastery', 0.8) WHERE world_id = ?`
- 整个图交给 LLM 推理 / D3 渲染，无需额外转换

**时态过滤（读档时）**：
```python
# Python 侧过滤，不用 SQL
graph = json.loads(row["graph"])
checkpoint_time = "2026-03-29T16:30"
valid_concepts = {
    k: v for k, v in graph["concepts"].items()
    if v["t_valid"] <= checkpoint_time
    and (v["t_invalid"] is None or v["t_invalid"] > checkpoint_time)
}
```

#### learner_profiles（学习者画像）

```sql
CREATE TABLE learner_profiles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    world_id    INTEGER REFERENCES worlds(id),
    profile     JSON DEFAULT '{}',
    updated_at  TEXT DEFAULT (datetime('now'))
);
```

**profile JSON**（累积记忆，3 类 — 详见 `learning_memory_theory.md`）：

```json
{
  "preferences": {
    "visual_examples": {"value": 0.8, "t_updated": "2026-03-29T16:30", "evidence": "多次要求画图解释"},
    "analogy_based": {"value": 0.7, "t_updated": "2026-03-28T14:00", "evidence": "用做菜类比递归时理解最快"},
    "pace": {"value": "slow_deliberate", "t_updated": "2026-03-29", "evidence": "不喜欢被催促"}
  },
  "affect": {
    "frustration_tolerance": {"value": "low", "t_updated": "2026-03-29T16:40", "evidence": "连续3轮卡住会沮丧"},
    "curiosity_baseline": {"value": "high", "t_updated": "2026-03-28T10:00", "evidence": "经常主动追问延伸问题"},
    "encouragement_response": {"value": "strong", "t_updated": "2026-03-29T16:45", "evidence": "被肯定后积极性明显提升"}
  },
  "metacognition": {
    "planning": {"value": "moderate", "t_updated": "2026-03-29", "evidence": "偶尔主动规划，多数时候跟着教师走"},
    "monitoring": {"value": "weak", "t_updated": "2026-03-29", "evidence": "经常说'我懂了'但做题时暴露出不理解"},
    "regulating": {"value": "moderate", "t_updated": "2026-03-29", "evidence": "提示后能换思路，但不会主动尝试"},
    "reflecting": {"value": "strong", "t_updated": "2026-03-28", "evidence": "每次对话结束前能准确总结学到的内容"}
  }
}
```

| 类别 | 来源理论 | 含义 | 时态行为 |
|------|---------|------|---------|
| `preferences` | ITS Learner Characteristics | 学习偏好（怎么学最有效） | 累积，每个 trait 带 t_updated |
| `affect` | Jarvis Emotional State Tracking | 情感模式（情绪反应规律） | 累积，每个 trait 带 t_updated |
| `metacognition` | MSKT 四维度 | 元认知能力（自我调控学习） | 累积，每个 trait 带 t_updated |

**时态行为**：不随存档回滚——这些是关于学习者**作为人**的特征。但每个 trait 有 `t_updated`，分叉时间线按 `t_updated <= checkpoint_time` 取历史值（避免使用检查点之后才观察到的特征）。

#### fsrs_states（间隔重复）

```sql
CREATE TABLE fsrs_states (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id    INTEGER REFERENCES worlds(id),
    concept_id  TEXT NOT NULL,              -- "recursion"
    difficulty  REAL,
    stability   REAL,
    last_review TEXT,
    next_review TEXT,
    reps        INTEGER DEFAULT 0,
    UNIQUE(world_id, concept_id)
);
```

**为什么单独建表不用 JSON**：FSRS 算法需要原子的读-改-写。SQLite 事务保证 `SELECT → 计算 → UPDATE` 的原子性。

---

## 三、数据流

### 3.1 一轮对话的完整流程

```
用户发送消息
  │
  ├─ 1. INSERT chat_messages（SQLite 事务开始）
  │
  ├─ 2. 构建 LLM prompt（工作记忆组装）
  │     ├── 静态层：teacher_persona.system_prompt_template
  │     ├── 动态层（按记忆分类组装，顺序有意义）
  │     │   ├── STAGE_PROMPTS[session.relationship_stage]
  │     │   ├── SCAFFOLD_INSTRUCTIONS[compute_scaffold(emotion, mastery)]
  │     │   ├── 【知识状态】knowledge 类型按 bloom_level 分组（已掌握/学习中/初识）
  │     │   ├── 【程序性技能】skill 类型按 proficiency 排列
  │     │   ├── 【⚠️ 误解】misconception 类型（未纠正的，带 severity）
  │     │   ├── 【近期事件】episode 类型（最近 3 条，按 significance 排序）
  │     │   ├── 【学习偏好】profile.preferences
  │     │   ├── 【情感模式】profile.affect
  │     │   └── 【元认知】profile.metacognition
  │     └── 最近 N 条 chat_messages → SELECT ... ORDER BY id DESC LIMIT 20
  │
  ├─ 3. 调用 LLM → 获得回复
  │
  ├─ 4. 情感分析（dynamic_analyzer）
  │
  ├─ 5. INSERT chat_messages（教师回复）
  │
  ├─ 6. 知识图谱更新（LLM 提取概念 → json_set 更新 knowledge.graph）
  │
  ├─ 7. 关系阶段检查（是否进化）
  │
  └─ 8. COMMIT（SQLite 事务结束——消息+知识+阶段 一致性保证）
```

### 3.2 存档（COMMIT）

```python
def create_checkpoint(db, session_id, save_name):
    session = db.execute("SELECT * FROM sessions WHERE id = ?", [session_id]).fetchone()
    msg_count = db.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id = ?", [session_id]).fetchone()[0]
    last_msg = db.execute(
        "SELECT content, emotion_analysis FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT 1",
        [session_id]
    ).fetchone()

    emotion = json.loads(last_msg["emotion_analysis"] or "{}").get("emotion_type", "neutral")

    db.execute("""
        INSERT INTO checkpoints (user_id, world_id, session_id, save_name, message_index, state)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        session["user_id"],
        session["world_id"],
        session_id,
        save_name,
        msg_count,
        json.dumps({
            "relationship_stage": session["relationship_stage"],
            "emotion": emotion,
            "expression": EXPRESSION_MAP.get(emotion, "default"),
            "scene_key": current_scene,
            "sage_character_id": session["sage_character_id"],
            "traveler_character_id": session["traveler_character_id"],
            "course_id": session["course_id"],
            "last_reply_preview": last_msg["content"][:80],
        })
    ])
    db.commit()
```

### 3.3 读档（BRANCH）

```python
def branch_from_checkpoint(db, checkpoint_id, user_id):
    cp = db.execute("SELECT * FROM checkpoints WHERE id = ?", [checkpoint_id]).fetchone()
    state = json.loads(cp["state"])

    # 1. 创建新 Session（分叉）
    db.execute("""
        INSERT INTO sessions
        (world_id, course_id, user_id, sage_character_id, traveler_character_id,
         teacher_persona_id, relationship_stage, parent_checkpoint_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        cp["world_id"], state["course_id"], user_id,
        state["sage_character_id"], state["traveler_character_id"],
        get_active_persona(state["sage_character_id"]),
        state["relationship_stage"], checkpoint_id
    ])
    new_session_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # 2. 复制检查点之前的消息
    db.execute("""
        INSERT INTO chat_messages (session_id, sender_type, content, emotion_analysis, timestamp)
        SELECT ?, sender_type, content, emotion_analysis, timestamp
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY id
        LIMIT ?
    """, [new_session_id, cp["session_id"], cp["message_index"]])

    db.commit()

    # 3. 知识图谱：读档时 Python 侧按 t_valid <= checkpoint_time 过滤
    #    不需要复制或修改 knowledge 表——同一个 World 共享知识，时态过滤在读取时做

    return new_session_id
```

### 3.4 知识图谱检索（替代 ChromaDB）

```python
def get_relevant_knowledge(db, world_id, user_message, checkpoint_time=None):
    """获取知识图谱，交给 LLM 判断相关性"""
    row = db.execute("SELECT graph FROM knowledge WHERE world_id = ?", [world_id]).fetchone()
    if not row:
        return ""

    graph = json.loads(row["graph"])

    # 时态过滤（如果在分叉时间线中）
    if checkpoint_time:
        filtered = {}
        for concept_id, concept in graph.get("concepts", {}).items():
            if concept["t_valid"] <= checkpoint_time:
                if concept["t_invalid"] is None or concept["t_invalid"] > checkpoint_time:
                    filtered[concept_id] = concept
        graph["concepts"] = filtered

    # 返回整个图（或摘要）给 LLM
    # LLM 自己判断哪些概念与 user_message 相关
    return json.dumps(graph, ensure_ascii=False, indent=2)
```

**为什么让 LLM 自己判断相关性**：
- 知识图谱几十 KB，在 LLM 的 context window 内（100K+ tokens）
- LLM 的语义理解能力远超向量相似度
- 不需要额外的嵌入模型和向量数据库

**当图太大时的优化**：如果某个 World 的知识概念超过 200 个（几十 KB 以上），可以先只传概念名+掌握度列表（不含 content），让 LLM 选出相关概念，再查询详情。两步检索，仍然不需要向量。

### 3.5 知识图谱更新（LLM 提取概念）

```python
def update_knowledge_after_chat(db, world_id, user_msg, teacher_reply, emotion):
    """每轮对话后，让 LLM 提取/更新知识概念"""

    # 读取当前知识图谱
    row = db.execute("SELECT graph FROM knowledge WHERE world_id = ?", [world_id]).fetchone()
    graph = json.loads(row["graph"]) if row else {"concepts": {}}

    # 让 LLM 分析这轮对话，提取知识变化
    extraction_prompt = f"""根据以下对话，分析学生的知识状态变化。

当前知识图谱：
{json.dumps(graph, ensure_ascii=False)}

本轮对话：
学生：{user_msg}
教师：{teacher_reply}
学生情绪：{emotion}

请输出 JSON，格式：
{{
  "updates": [
    {{"concept": "概念名", "mastery_delta": 0.1, "status": "learning", "insight": "新的理解描述"}},
  ],
  "new_concepts": [
    {{"name": "新概念", "mastery": 0.2, "content": "...", "edges": {{"existing_concept": "prerequisite_of"}}}}
  ]
}}
只输出 JSON。如果没有知识变化，输出 {{"updates":[],"new_concepts":[]}}"""

    result = await llm_adapter.chat(messages=[{"role": "user", "content": extraction_prompt}], ...)
    changes = json.loads(result)

    # 应用变化
    now = datetime.utcnow().isoformat()
    for update in changes.get("updates", []):
        concept_id = update["concept"]
        if concept_id in graph["concepts"]:
            old_mastery = graph["concepts"][concept_id]["mastery"]
            graph["concepts"][concept_id]["mastery"] = min(1.0, max(0, old_mastery + update["mastery_delta"]))
            if update.get("insight"):
                graph["concepts"][concept_id]["content"] = update["insight"]
            graph["concepts"][concept_id]["status"] = update.get("status", "learning")

    for new_concept in changes.get("new_concepts", []):
        graph["concepts"][new_concept["name"]] = {
            "name": new_concept["name"],
            "mastery": new_concept["mastery"],
            "status": "new",
            "content": new_concept.get("content", ""),
            "t_valid": now,
            "t_invalid": None,
            "episodes": [],
            "edges": new_concept.get("edges", {})
        }
        # 给 edges 加时态
        for target, edge_type in new_concept.get("edges", {}).items():
            graph["concepts"][new_concept["name"]]["edges"][target] = {
                "type": edge_type, "t_valid": now
            }

    # 写回（SQLite 事务内，和消息 INSERT 一起 COMMIT）
    db.execute("UPDATE knowledge SET graph = ? WHERE world_id = ?",
               [json.dumps(graph, ensure_ascii=False), world_id])
```

---

## 四、知识图谱可视化

### 4.1 API

```
GET /api/worlds/{world_id}/knowledge-graph
参数：?checkpoint_time=2026-03-29T16:30（可选，用于查看某个检查点时刻的知识状态）

返回：
{
  "nodes": [
    {"id": "recursion", "name": "递归", "mastery": 0.7, "status": "learning"},
    {"id": "termination", "name": "终止条件", "mastery": 0.3, "status": "confused"}
  ],
  "edges": [
    {"source": "recursion", "target": "termination", "type": "prerequisite_of"},
    {"source": "factorial", "target": "recursion", "type": "has_example"}
  ]
}
```

后端实现：从 `knowledge.graph` JSON 提取 nodes 和 edges，做时态过滤（如有 checkpoint_time），转成 D3 格式返回。

### 4.2 前端渲染（D3.js force-directed）

```
HudBar 新增：[📊 知识图谱]

点击弹出全屏 overlay：
┌──────────────────────────────────────┐
│  我的知识网络 — 雅典学院              │
│  ┌────────────────────────────────┐  │
│  │     ◉ 递归(0.7)               │  │
│  │    ╱         ╲                │  │
│  │   ◎ 阶乘     ◌ 终止条件(0.3)  │  │
│  │              ╲                │  │
│  │               ◉ 栈(0.6)      │  │
│  └────────────────────────────────┘  │
│  节点大小=掌握度  颜色=状态           │
│  🟢已掌握  🟡学习中  🔴困惑  ⚪未接触  │
│  点击节点查看详情                      │
└──────────────────────────────────────┘
```

节点大小 = mastery 值。颜色 = status。边类型用不同样式（实线/虚线/红线）。

---

## 五、API 设计

### 5.1 World CRUD

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/worlds` | 创建世界 |
| GET | `/api/worlds` | 列出用户所有世界 |
| GET | `/api/worlds/{id}` | 世界详情（含角色、课程列表） |
| PUT | `/api/worlds/{id}` | 更新世界 |
| DELETE | `/api/worlds/{id}` | 删除世界（级联删除课程、时间线、检查点、知识） |

### 5.2 World-Character 关联

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/worlds/{id}/characters` | 添加角色到世界（指定 role） |
| DELETE | `/api/worlds/{id}/characters/{char_id}` | 移除角色 |

### 5.3 Course CRUD（原 Subject）

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/worlds/{world_id}/courses` | 创建课程 |
| GET | `/api/worlds/{world_id}/courses` | 列出世界下的课程 |

### 5.4 学习流程

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/courses/{id}/start` | 开始学习（返回 session_id + 角色信息 + 场景集） |
| POST | `/api/courses/{id}/chat` | 发送消息 |
| GET | `/api/sessions/{id}/history` | 获取对话历史 |

### 5.5 存档系统

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/checkpoints` | 创建检查点（COMMIT） |
| GET | `/api/worlds/{id}/checkpoints` | 获取世界的所有检查点 |
| POST | `/api/checkpoints/{id}/branch` | 从检查点分叉新时间线（BRANCH） |
| GET | `/api/worlds/{id}/timelines` | 获取世界的所有时间线 |

### 5.6 知识图谱

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/worlds/{id}/knowledge-graph` | 获取知识图谱（D3 格式，支持 checkpoint_time 过滤） |

---

## 六、前端变更

### 6.1 Home.vue — 世界入口

```
主菜单 → "开始学习"
  → 世界列表（"雅典学院" / "三国军帐" / [+ 创建新世界]）
    → 选择世界
      → 回忆库（时间线列表 + 检查点列表）
        → 选择 "继续" / "从检查点分叉" / "新的旅程"
          → 选择课程（对话框选择面板）
            → 进入 Learning.vue
```

### 6.2 Learning.vue — 双角色布局

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
│ [存档][读档][跳过][自动][回忆]   │
│ [知识图谱][设置][返回]           │
└─────────────────────────────────┘
```

### 6.3 知识图谱页面

- HudBar 新增 `📊 知识图谱` 按钮
- 全屏 overlay，D3.js force-directed 渲染
- 节点可点击查看详情（概念名、掌握度、学习历史、关联概念）
- 可按 checkpoint_time 查看"那个时候我知道什么"

---

## 七、Migration 路径

### 从当前系统迁移

```
Phase 0: 基础设施切换
  ├── PostgreSQL → SQLite（改 DATABASE_URL + SQLAlchemy 微调）
  ├── 去掉 ChromaDB 依赖（替换 memory.py 为知识图谱服务）
  ├── 去掉 Docker 中的 PostgreSQL + ChromaDB 容器
  └── 更新 requirements.txt

Phase 1: 数据模型扩展
  ├── 创建 worlds 表 + world_characters 表
  ├── 创建 knowledge 表（JSON 列）
  ├── 创建 checkpoints 表
  ├── courses 表（rename subjects + 加 world_id）
  ├── sessions 加分叉字段
  ├── characters 加 type 字段
  └── 自动迁移：为每个现有 Character 创建 World

Phase 2: 后端 API
  ├── World CRUD + WorldCharacter 关联
  ├── Checkpoint COMMIT/BRANCH
  ├── 知识图谱 API
  ├── learning_engine 集成知识图谱（替代 ChromaDB 检索）
  └── 知识提取（LLM 每轮对话后更新 knowledge.graph）

Phase 3: 前端
  ├── Home.vue 世界入口 + 回忆库
  ├── Learning.vue 双角色布局
  ├── 知识图谱可视化（D3.js）
  └── Character.vue 角色类型选择

Phase 4: 清理
  ├── 删除旧字段（courses.character_id 等）
  ├── 删除 ChromaDB/Neo4j 相关代码
  └── 更新部署文档
```

---

## 八、风险评估

| 风险 | 影响 | 缓解 |
|------|------|------|
| SQLite 并发限制 | 单用户本地 app 不存在此问题 | 如果未来做多用户 Web 版，切回 PostgreSQL（SQLAlchemy 只改连接字符串） |
| 知识图谱 JSON 过大 | 单个 World 200+ 概念时 JSON 可能几百 KB | 分两步检索：先传概念列表让 LLM 选，再查详情 |
| LLM 知识提取不准确 | 概念和关系可能有误 | 用户可在知识图谱界面手动修正；提取结果是建议不是确定 |
| 数据迁移丢失 | 现有 PostgreSQL 数据 | 写迁移脚本；SQLite 迁移前先备份 |
| 双角色布局移动端拥挤 | 体验差 | 移动端只显示当前说话的角色 |

---

*本文档由 Reviewer 编写。Owner 已确认所有核心决策。待 Owner 最终审批后拆分为独立 Issue，Creator 按 Phase 顺序实施。*
