# 后端数据结构和 API 接口文档

> 生成时间: 2026-04-08
> 更新状态: 整理中

---

## 1. 数据模型 (Database Models)

### 1.1 用户和认证

#### User
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| username | String(50) | 用户名，唯一 |
| password_hash | String(255) | 密码哈希 |
| role | String(20) | 角色，默认 "student" |
| encrypted_api_key | String(255) | 加密的 API Key |
| default_provider | String(50) | 默认 LLM 提供商 |
| created_at | DateTime | 创建时间 |

**关联**: worlds, characters, learner_profiles, learning_diaries, progress_trackings, sessions, checkpoints, user_profile

#### UserProfile
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 外键，关联 User，唯一 |
| profile | JSON | 跨世界汇总数据 |
| computed_at | DateTime | 计算时间 |
| created_at/updated_at | DateTime | 时间戳 |

---

### 1.2 世界和场景

#### World
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 外键，关联 User |
| name | String(100) | 世界名称 |
| description | Text | 世界描述 |
| scenes | JSON | 场景数据 |
| created_at | DateTime | 创建时间 |

**关联**: user, world_characters, courses, sessions, checkpoints, learner_profiles, knowledge, fsrs_states

#### Knowledge
| 字段 | 类型 | 说明 |
|------|------|------|
| world_id | Integer | 主键/外键，关联 World |
| graph | JSON | 知识图谱数据 |

---

### 1.3 角色系统

#### Character
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 外键，关联 User |
| name | String(100) | 角色名称 |
| type | String(20) | 类型: "sage"(导师) / "traveler"(旅人) |
| avatar | String(255) | 头像 |
| personality | Text | 性格设定 |
| background | Text | 背景故事 |
| speech_style | Text | 说话风格 |
| sprites | JSON | 角色视觉配置 (color, accentColor) |
| title | String(100) | 名片头衔 |
| tags | JSON | 角色标签列表 |
| experience_points | Integer | 经验值，默认 0 |
| level | Integer | 等级，默认 1 |
| created_at | DateTime | 创建时间 |

**关联**: user, teacher_personas, world_links

#### WorldCharacter (角色-世界关联表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| world_id | Integer | 外键，关联 World |
| character_id | Integer | 外键，关联 Character |
| role | String(20) | 角色类型: "sage" / "traveler" |
| is_primary | Boolean | 是否为主角色 |

**约束**: UniqueConstraint(world_id, character_id)

#### TeacherPersona
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| character_id | Integer | 外键，关联 Character |
| name | String(100) | 人格名称 |
| version | String(20) | 版本，默认 "1.0" |
| traits | JSON | 人格特征 |
| system_prompt_template | Text | 系统提示模板 |
| is_active | Boolean | 是否激活 |
| created_at/updated_at | DateTime | 时间戳 |

**关联**: character, sessions

---

### 1.4 课程和学习

#### Course
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| world_id | Integer | 外键，关联 World |
| name | String(100) | 课程名称 |
| description | Text | 课程描述 |
| target_level | String(50) | 目标等级 |
| meta | JSON | 扩展字段 (current_level, motivation, pace, weekly_minutes, sage_ids) |
| created_at | DateTime | 创建时间 |

**关联**: world, lesson_plans, learning_diaries, progress_trackings, sessions

#### LessonPlan
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| course_id | Integer | 外键，关联 Course |
| content | Text | 课程内容 |
| created_at | DateTime | 创建时间 |

#### LearningDiary
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| course_id | Integer | 外键，关联 Course |
| user_id | Integer | 外键，关联 User |
| date | DateTime | 日期 |
| content | Text | 日记内容 |
| reflection | Text | 反思内容 |

#### ProgressTracking
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| course_id | Integer | 外键，关联 Course |
| user_id | Integer | 外键，关联 User |
| topic | String(100) | 学习主题 |
| mastery_level | Integer | 掌握程度，默认 0 |
| last_review | DateTime | 上次复习时间 |
| next_review | DateTime | 下次复习时间 |

---

### 1.5 学习者档案

#### LearnerProfile
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 外键，关联 User |
| world_id | Integer | 外键，关联 World |
| profile | JSON | 学习者画像数据 |
| created_at/updated_at | DateTime | 时间戳 |

**层级说明**: 这是"学习追踪层"，与游戏角色层(traveler)是不同概念

---

### 1.6 会话和消息

#### Session
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| course_id | Integer | 外键，关联 Course |
| user_id | Integer | 外键，关联 User |
| world_id | Integer | 外键，关联 World |
| sage_character_id | Integer | 导师角色外键 |
| traveler_character_id | Integer | 旅人角色外键 |
| started_at | DateTime | 开始时间 |
| ended_at | DateTime | 结束时间 |
| system_prompt | Text | 系统提示 |
| relationship | JSON | 关系数据 (dimensions, stage, history) |
| teacher_persona_id | Integer | 教师人格外键 |
| learner_profile_id | Integer | 学习者档案外键 |
| parent_checkpoint_id | Integer | 父检查点外键 |
| branch_name | String(120) | 分支名称 |

**关联**: course, user, world, teacher_persona, learner_profile, chat_messages, relationship_stage_records, parent_checkpoint

#### ChatMessage
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| session_id | Integer | 外键，关联 Session |
| sender_type | String(20) | 发送者类型 |
| sender_id | Integer | 发送者 ID |
| content | Text | 消息内容 |
| timestamp | DateTime | 时间戳 |
| emotion_analysis | JSON | 情绪分析 |
| used_memory_ids | JSON | 使用的记忆 ID 列表 |

#### RelationshipStageRecord
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| session_id | Integer | 外键，关联 Session |
| stage | String(20) | 关系阶段 |
| reason | Text | 阶段变更原因 |
| updated_at | DateTime | 更新时间 |

---

### 1.7 记忆和复习系统

#### FSRSState
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| world_id | Integer | 外键，关联 World |
| concept_id | String(150) | 概念 ID |
| difficulty | Float | 难度 |
| stability | Float | 稳定性 |
| last_review | DateTime | 上次复习 |
| next_review | DateTime | 下次复习 |
| reps | Integer | 重复次数 |

**约束**: UniqueConstraint(world_id, concept_id)

---

### 1.8 检查点和存档

#### Checkpoint
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 外键，关联 User |
| world_id | Integer | 外键，关联 World |
| session_id | Integer | 外键，关联 Session (可为空) |
| save_name | String(100) | 存档名称 |
| message_index | Integer | 消息索引 |
| state | JSON | 状态数据 |
| thumbnail_path | String(255) | 缩略图路径 |
| created_at | DateTime | 创建时间 |

---

## 2. API 路由接口

### 2.1 archive.py - 资源管理

#### 角色 (Character)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /character | 创建角色 |
| GET | /character | 获取所有角色列表 |
| GET | /character/stats | 获取角色统计 |
| GET | /character/{character_id} | 获取单个角色 |
| PUT | /character/{character_id} | 更新角色 |
| DELETE | /character/{character_id} | 删除角色 |
| POST | /character/{character_id}/avatar | 上传头像 |
| POST | /character/{character_id}/levelup | 角色升级 |

#### 世界 (World)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /worlds | 创建世界 |
| GET | /worlds | 获取所有世界 |
| GET | /worlds/{world_id} | 获取单个世界 |
| PUT | /worlds/{world_id} | 更新世界 |
| DELETE | /worlds/{world_id} | 删除世界 |

#### 世界-角色关联 (WorldCharacter)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /worlds/{world_id}/characters | 添加角色到世界 |
| GET | /worlds/{world_id}/characters | 获取世界所有角色 |
| DELETE | /worlds/{world_id}/characters/{character_id} | 从世界移除角色 |
| POST | /characters/{character_id}/sprites | 上传角色精灵图 |

#### 教师人格 (TeacherPersona)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /teacher_persona | 创建人格 |
| GET | /teacher_persona | 获取所有人格 |
| PUT | /teacher_persona/{persona_id}/activate | 激活人格 |
| PUT | /teacher_persona/{persona_id} | 更新人格 |
| DELETE | /teacher_persona/{persona_id} | 删除人格 |

#### 学习者档案 (LearnerProfile)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /learner_profile | 创建档案 |
| GET | /learner_profile | 获取所有档案 |
| PUT | /learner_profile/{profile_id} | 更新档案 |

#### 课程 (Course)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /worlds/{world_id}/courses | 在世界创建课程 |
| GET | /worlds/{world_id}/courses | 获取世界所有课程 |
| POST | /courses | 创建课程 |
| GET | /courses | 获取所有课程 |
| GET | /courses/{course_id} | 获取单个课程 |
| PUT | /courses/{course_id} | 更新课程 |
| DELETE | /courses/{course_id} | 删除课程 |

#### 学习日记 (LearningDiary)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /learning_diary | 创建日记 |
| GET | /learning_diary | 获取日记列表 |

#### 进度追踪 (ProgressTracking)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /progress | 创建进度 |
| GET | /progress | 获取进度列表 |
| PUT | /progress/{progress_id} | 更新进度 |
| POST | /progress/{progress_id}/review | 复习进度 |
| GET | /progress/due | 获取待复习进度 |

---

### 2.2 learning.py - 学习会话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /courses/{course_id}/start | 开始课程学习 |
| POST | /courses/{course_id}/chat | 发送聊天消息 |
| POST | /chat/tool_confirm | 工具调用确认 |
| POST | /sessions/{session_id}/end | 结束会话 |
| GET | /sessions/{session_id}/history | 获取会话历史 |
| GET | /sessions | 获取会话列表 |
| GET | /sessions/{session_id}/emotion_trajectory | 获取情绪轨迹 |
| GET | /user/profile | 获取用户画像 |
| POST | /user/profile/refresh | 刷新用户画像 |

---

### 2.3 save.py - 存档管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /checkpoints | 创建检查点 |
| GET | /checkpoints | 获取所有检查点 |
| GET | /worlds/{world_id}/checkpoints | 获取世界检查点 |
| POST | /checkpoints/{checkpoint_id}/branch | 创建分支 |
| GET | /worlds/{world_id}/timelines | 获取时间线 |
| GET | /worlds/{world_id}/knowledge-graph | 获取知识图谱 |
| GET | /checkpoints/{checkpoint_id} | 获取检查点详情 |
| DELETE | /checkpoints/{checkpoint_id} | 删除检查点 |
| POST | /save | 创建存档 |
| GET | /save | 获取存档列表 |
| GET | /save/{save_id} | 获取存档详情 |
| DELETE | /save/{save_id} | 删除存档 |

---

### 2.4 auth.py - 认证

(需要进一步查看)

---

### 2.5 report.py - 报告

(需要进一步查看)

---

## 3. 关键数据结构

### 3.1 WorldResponse
```python
class WorldResponse(WorldCreate):
    id: int
    user_id: int
    sages: list[SageInfo] | None = None  # 世界关联的导师角色
    stageLabel: str | None = None
    relationship: dict | None = None
    courses: list["CourseResponse"] | None = None
```

⚠️ **注意**: 当前 `WorldResponse` **没有 `travelers` 字段**，需要添加！

### 3.2 SageInfo
```python
class SageInfo(BaseModel):
    id: int
    name: str
    title: str  # 来自 character.personality
    symbol: str  # 来自 character.avatar
    color: str
    accentColor: str
```

### 3.3 CharacterResponse
```python
class CharacterResponse(BaseModel):
    id: int
    user_id: int
    name: str
    type: str  # "sage" | "traveler"
    avatar: str | None
    personality: str | None
    background: str | None
    speech_style: str | None
    sprites: dict | None
    title: str | None
    tags: list | None
    experience_points: int
    level: int
    created_at: datetime
```

### 3.4 CourseResponse
```python
class CourseResponse(BaseModel):
    id: int
    world_id: int
    name: str
    description: str | None
    target_level: str | None
    meta: dict | None  # 扩展字段
    created_at: datetime
```

### 3.5 Session Relationship
```python
{
    "dimensions": {
        "trust": 0.0,
        "familiarity": 0.0,
        "respect": 0.0,
        "comfort": 0.0,
    },
    "stage": "stranger",  # stranger -> acquaintance -> friend -> partner
    "history": []
}
```

---

## 4. 待修复问题

### 4.1 WorldResponse 缺少 travelers 字段

**问题**: 前端 `WorldDetail.vue` 需要显示世界关联的 traveler 角色，但后端 `WorldResponse` 只有 `sages` 字段。

**解决方案**:
1. 添加 `_get_world_travelers()` 函数（类似 `_get_world_sages`）
2. 在 `WorldResponse` 添加 `travelers: list[SageInfo] | None = None` 字段
3. 在 `_build_world_response()` 中调用 `_get_world_travelers()`

---

## 5. 表单设计参考

### 5.1 Course.meta 字段结构
```json
{
    "current_level": "初中一年级",
    "motivation": "好奇心驱动",
    "pace": "适中",
    "weekly_minutes": 120,
    "sage_ids": [1, 2]
}
```

---

## 6. 文件路径索引

| 文件 | 说明 |
|------|------|
| backend/models/models.py | 数据库模型定义 |
| backend/api/routes/archive.py | 资源管理 API |
| backend/api/routes/learning.py | 学习会话 API |
| backend/api/routes/save.py | 存档管理 API |
| backend/api/routes/auth.py | 认证 API |
| backend/api/routes/report.py | 报告 API |
