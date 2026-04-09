# Implementation Plan: WorldHub 页面设计与实现

## [Overview]

为 Self_Learning-System 创建新的 **WorldHub** 页面，作为单世界资源管理中心。WorldHub 采用层级导航（URL驱动）设计，按数据拓扑关系组织页面结构：世界 → 课程 → 会话 → 检查点。

**页面定位**：快速查看和删除对应资源的管理页面。

**视觉设计**：采用图片/缩略图展示，增强视觉效果。

现有 Archive 页面保持不变，后续再处理其重构问题。

## [Types]

### 新增前端类型（frontend/src/types/index.ts）

```typescript
// WorldHub 相关类型

// 世界概览
export interface WorldOverview {
  id: number
  name: string
  description: string | null
  scenes: { background?: string; menu_background?: string } | null
  created_at: string
  // 统计信息
  course_count: number
  session_count: number
  checkpoint_count: number
  character_count: number
  // 当前关系状态
  relationship: {
    stage: RelationshipStage
    dimensions: Record<string, number>
  } | null
}

// 课程列表项
export interface CourseListItem {
  id: number
  world_id: number
  name: string
  description: string | null
  target_level: string | null
  created_at: string
  // 统计
  session_count: number
  progress_count: number
  diary_count: number
}

// 会话列表项
export interface SessionListItem {
  id: number
  world_id: number
  course_id: number
  course_name: string
  started_at: string
  ended_at: string | null
  relationship_stage: RelationshipStage
  message_count: number
  parent_checkpoint_id: number | null
  branch_name: string | null
}

// 检查点列表项
export interface CheckpointListItem {
  id: number
  world_id: number
  session_id: number | null
  save_name: string
  message_index: number
  created_at: string
  thumbnail_path: string | null
  // 关联信息
  session_course_name?: string
  branch_name?: string
}
```

## [Files]

### 新增前端文件

| 文件路径 | 目的 |
|---------|------|
| `frontend/src/views/WorldHub.vue` | WorldHub 主页面容器 |
| `frontend/src/views/worldhub/WorldList.vue` | 世界列表视图 |
| `frontend/src/views/worldhub/WorldDetail.vue` | 世界概览视图 |
| `frontend/src/views/worldhub/CourseList.vue` | 课程列表视图 |
| `frontend/src/views/worldhub/SessionList.vue` | 会话列表视图 |
| `frontend/src/views/worldhub/CheckpointList.vue` | 检查点列表视图 |
| `frontend/src/views/worldhub/components/WorldCard.vue` | 世界卡片组件 |
| `frontend/src/views/worldhub/components/CourseRow.vue` | 课程行组件 |
| `frontend/src/views/worldhub/components/SessionRow.vue` | 会话行组件 |
| `frontend/src/views/worldhub/components/CheckpointRow.vue` | 检查点行组件（带缩略图） |

### 修改的前端文件

| 文件路径 | 修改内容 |
|---------|---------|
| `frontend/src/router/index.ts` | 添加 WorldHub 路由 |
| `frontend/src/types/index.ts` | 添加 WorldHub 相关类型 |
| `frontend/src/api/client.ts` | 添加 worldHubApi 方法 |

### 路由结构

```
/worldhub                           → 世界列表 (WorldList)
/worldhub/:worldId                  → 世界概览 (WorldDetail)
/worldhub/:worldId/courses          → 课程列表 (CourseList)
/worldhub/:worldId/sessions         → 会话列表 (SessionList)
/worldhub/:worldId/checkpoints      → 检查点列表 (CheckpointList)
```

## [Functions]

### 新增后端端点

#### GET /api/worlds/{world_id}/overview
获取世界概览统计信息（带计数）

#### GET /api/worlds/{world_id}/sessions
获取世界会话列表（带消息数）

#### GET /api/worlds/{world_id}/checkpoints
获取世界检查点列表（带缩略图路径）

### 新增前端 API 方法

```typescript
// frontend/src/api/client.ts

export const worldHubApi = {
  // 世界列表（带概览）
  getWorlds: (): Promise<WorldOverview[]> =>
    client.get('/worlds'),
  
  // 世界概览
  getWorldOverview: (worldId: number): Promise<WorldOverview> =>
    client.get(`/worlds/${worldId}`),
  
  // 课程列表
  getWorldCourses: (worldId: number): Promise<CourseListItem[]> =>
    client.get(`/worlds/${worldId}/courses`),
  
  // 会话列表
  getWorldSessions: (worldId: number): Promise<SessionListItem[]> =>
    client.get(`/worlds/${worldId}/sessions`),
  
  // 检查点列表
  getWorldCheckpoints: (worldId: number): Promise<CheckpointListItem[]> =>
    client.get(`/worlds/${worldId}/checkpoints`),
  
  // 删除操作（复用现有端点）
  deleteWorld: (worldId: number) => client.delete(`/worlds/${worldId}`),
  deleteCourse: (courseId: number) => client.delete(`/courses/${courseId}`),
  deleteSession: (sessionId: number) => client.delete(`/sessions/${sessionId}`),
  deleteCheckpoint: (checkpointId: number) => client.delete(`/checkpoints/${checkpointId}`),
}
```

## [Dependencies]

### 前端依赖
- 复用现有依赖

### 后端依赖
- 复用现有依赖

## [Testing]

### 后端测试
- `backend/tests/test_worldhub.py` - 新增 WorldHub API 测试

### 前端测试
- 路由跳转测试
- 删除功能测试

## [Implementation Order]

### Phase 1: 后端扩展

1. **扩展 archive.py 世界端点**
   - 新增世界概览端点 GET /api/worlds/{id}/overview
   - 新增带统计的会话列表端点
   - 新增带缩略图路径的检查点列表端点

### Phase 2: 前端基础结构

2. **添加路由配置** (`router/index.ts`)
3. **添加类型定义** (`types/index.ts`)
4. **添加 API 方法** (`api/client.ts`)

### Phase 3: 核心组件开发

5. **创建 WorldHub 主容器** (`WorldHub.vue`)
6. **创建世界列表视图** (`WorldList.vue`) - 图片卡片展示
7. **创建世界概览视图** (`WorldDetail.vue`) - 封面图展示
8. **创建课程列表视图** (`CourseList.vue`)
9. **创建会话列表视图** (`SessionList.vue`)
10. **创建检查点列表视图** (`CheckpointList.vue`) - 缩略图网格

### Phase 4: 删除功能

11. **添加删除确认对话框**
12. **实现删除操作**
13. **删除后刷新列表**

---

## [UI Layout Reference]

### WorldHub 主容器

```
┌─────────────────────────────────────────────────────────────────────┐
│ ← 返回 Home                    WorldHub                              │
├─────────────────────────────────────────────────────────────────────┤
│ /worldhub > [世界名] > [资源类型]     ← 面包屑导航                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                     路由视图内容                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 世界列表视图

```
┌─────────────────────────────────────────────────────────────────────┐
│ 世界列表                                          [+ 创建世界]        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────┐  ┌─────────────────────────┐           │
│  │                         │  │                         │           │
│  │    [封面图]             │  │    [封面图]             │           │
│  │                         │  │                         │           │
│  │  🌍 雅典学院            │  │  🏯 三国世界            │           │
│  │  ───────────────        │  │  ───────────────        │           │
│  │  课程: 3  会话: 12      │  │  课程: 5  会话: 8       │           │
│  │  检查点: 5              │  │  检查点: 3              │           │
│  │                         │  │                         │           │
│  │  [进入]    [删除]       │  │  [进入]    [删除]       │           │
│  └─────────────────────────┘  └─────────────────────────┘           │
│                                                                     │
│  ┌─────────────────────────┐                                        │
│  │                         │                                        │
│  │    [封面图]             │                                        │
│  │                         │                                        │
│  │  🚀 星际探索            │                                        │
│  │  ───────────────        │                                        │
│  │  课程: 2  会话: 1       │                                        │
│  │  检查点: 0              │                                        │
│  │                         │                                        │
│  │  [进入]    [删除]       │                                        │
│  └─────────────────────────┘                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 世界概览视图

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    [世界封面大图]                              │    │
│  │                                                             │    │
│  │  雅典学院                                                    │    │
│  │  古希腊哲学学习世界...                                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌────────────┬────────────┬────────────┬────────────┐              │
│  │   课程     │   会话     │  检查点    │   角色     │              │
│  │    3      │    12     │    5      │    2      │              │
│  └────────────┴────────────┴────────────┴────────────┘              │
│                                                                     │
│  当前关系阶段: 朋友                                                 │
│  信任 ████████░░ 80%                                              │
│  默契 ██████░░░░ 60%                                              │
│                                                                     │
│  [课程列表]  [会话历史]  [检查点]  [删除世界]                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 课程列表视图

```
┌─────────────────────────────────────────────────────────────────────┐
│ 世界: 雅典学院 > 课程                              [+ 新建课程]      │
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │ 课程名称        │ 目标等级 │ 会话数 │ 进度数 │ 日记数 │ 操作 │    │
│ ├─────────────────────────────────────────────────────────────┤    │
│ │ 哲学导论        │  初级    │   5    │   8    │   3   │ [删除]│   │
│ │ 逻辑学基础      │  中级    │   3    │   5    │   1   │ [删除]│   │
│ │ 伦理学探讨      │  高级    │   4    │   6    │   2   │ [删除]│   │
│ └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 会话列表视图

```
┌─────────────────────────────────────────────────────────────────────┐
│ 世界: 雅典学院 > 会话历史                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  🟢 哲学导论 - 会话 #12                          2026-04-05 │    │
│  │     关系: 朋友 | 消息: 45 | 30分钟                    [删除]│    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  🟢 哲学导论 - 会话 #11                          2026-04-03 │    │
│  │     关系: 相识 | 消息: 32 | 25分钟                    [删除]│    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 检查点列表视图（带缩略图网格）

```
┌─────────────────────────────────────────────────────────────────────┐
│ 世界: 雅典学院 > 检查点                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐            │
│  │  [缩略图]     │ │  [缩略图]     │ │  [缩略图]     │            │
│  │               │ │               │ │               │            │
│  │  柏拉图对话   │ │  苏格拉底对话 │ │  早期存档     │            │
│  │  2026-04-05   │ │  2026-04-03   │ │  2026-04-01   │            │
│  │  会话#12      │ │  会话#11      │ │  会话#8       │            │
│  │               │ │               │ │               │            │
│  │  [加载][删除] │ │  [加载][删除] │ │  [加载][删除] │            │
│  └───────────────┘ └───────────────┘ └───────────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## [缩略图设计说明]

### 检查点缩略图来源

1. **自动截图**：用户存档时自动截取当前对话页面作为缩略图
2. **存储位置**：与检查点数据关联存储
3. **显示效果**：网格卡片形式展示

### 世界封面图来源

1. **世界场景配置**：使用 world.scenes.menu_background 或 scenes.background
2. **默认封面**：如无配置显示默认占位图

---

## [API Response Examples]

### GET /api/worlds/{world_id}/overview

```json
{
  "id": 1,
  "name": "雅典学院",
  "description": "古希腊哲学学习世界",
  "scenes": { "background": "https://example.com/athens.jpg" },
  "created_at": "2026-01-01T00:00:00Z",
  "course_count": 3,
  "session_count": 12,
  "checkpoint_count": 5,
  "character_count": 2,
  "relationship": {
    "stage": "friend",
    "dimensions": { "trust": 0.8, "familiarity": 0.6, "respect": 0.85, "comfort": 0.7 }
  }
}
```

### GET /api/worlds/{world_id}/sessions

```json
[
  {
    "id": 12,
    "world_id": 1,
    "course_id": 1,
    "course_name": "哲学导论",
    "started_at": "2026-04-05T10:00:00Z",
    "ended_at": "2026-04-05T10:30:00Z",
    "relationship_stage": "friend",
    "message_count": 45,
    "parent_checkpoint_id": null,
    "branch_name": null
  }
]
```

### GET /api/worlds/{world_id}/checkpoints

```json
[
  {
    "id": 5,
    "world_id": 1,
    "session_id": 12,
    "save_name": "柏拉图对话",
    "message_index": 45,
    "created_at": "2026-04-05T10:30:00Z",
    "thumbnail_path": "/checkpoints/thumbnails/5.png",
    "session_course_name": "哲学导论",
    "branch_name": "主线"
  }
]
```
