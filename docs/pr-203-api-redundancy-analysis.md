# API 接口冗余分析报告

> 生成时间: 2026-04-13
> 分析者: Creator (架构审查视角)
> 分析范围: backend/api/routes/

---

## 执行摘要

经分析，发现 **3 类冗余设计**，涉及 **16 个接口**：

| 类别 | 冗余程度 | 影响接口数 | 优先级 |
|------|----------|-----------|--------|
| Legacy Save 接口 | 高 | 4 | P0 |
| Timeline 接口功能重叠 | 中 | 1 | P1 |
| Course 路由分散 | 低 | 10 | P2 |

---

## 1. P0: Legacy Save 接口冗余

### 问题描述

`save.py` 中存在两套功能完全相同的接口：

| 功能 | 新版接口 (Checkpoint) | Legacy 接口 (Save) |
|------|---------------------|-------------------|
| 创建 | `POST /checkpoints` | `POST /save` |
| 列表 | `GET /checkpoints?world_id=X` | `GET /save?subject_id=X` |
| 详情 | `GET /checkpoints/{id}` | `GET /save/{save_id}` |
| 删除 | `DELETE /checkpoints/{id}` | `DELETE /save/{save_id}` |

### 代码证据

```python
# save.py:461 - Legacy 创建接口直接调用新版实现
@router.post("/save")
async def create_save_legacy(
    payload: LegacySaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = _get_owned_course(db, current_user, payload.subject_id)
    checkpoint = await create_checkpoint(  # ← 直接调用
        CheckpointCreate(
            world_id=course.world_id,
            session_id=payload.session_id,
            save_name=payload.save_name,
        ),
        db,
        current_user,
    )
    return checkpoint
```

### 影响分析

| 维度 | 影响 |
|------|------|
| 维护成本 | 两套接口需要同时维护 |
| 文档复杂度 | 前端需要了解两套语义 |
| 数据一致性 | 相同功能不同命名，容易混淆 |

### 建议行动

1. **短期**: 保持 Legacy 接口，标记为 `@deprecated`
2. **中期**: 前端迁移到 Checkpoint 接口
3. **长期**: 移除 Legacy Save 接口

---

## 2. P1: Timeline 接口功能重叠

### 问题描述

`save.py` 的 `/worlds/{world_id}/timelines` 接口返回 sessions + checkpoints，与以下接口存在功能重叠：

| 现有接口 | 功能 |
|----------|------|
| `GET /sessions` | 获取会话列表（按课程筛选） |
| `GET /checkpoints?world_id=X` | 获取检查点列表 |

### Timeline 接口返回值

```python
{
    "world_id": world_id,
    "sessions": [...],    # 与 GET /sessions 重复
    "checkpoints": [...]  # 与 GET /checkpoints 重复
}
```

### 代码证据

```python
# save.py:358
@router.get("/worlds/{world_id}/timelines")
async def get_world_timelines(...):
    # 查询 sessions
    sessions = db.query(SessionModel).filter(...)
    # 查询 checkpoints
    checkpoints = db.query(Checkpoint).filter(...)
    return {"world_id": world_id, "sessions": [...], "checkpoints": [...]}
```

### 建议行动

| 选项 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A. 保留 Timeline | 用于时间线视图的专用接口 | 减少前端请求次数 | 与其他接口重复 |
| B. 移除 Timeline | 前端组合调用 sessions + checkpoints | 单一职责 | 需要两次请求 |
| C. 重命名为 `/worlds/{id}/overview` | 明确语义为聚合视图 | 不冲突 | 仅重命名 |

**建议**: 选项 C - 重命名并明确为聚合视图

---

## 3. P2: Course 路由分散

### 问题描述

Course 相关接口分散在 `archive.py` 和 `learning.py` 两个文件：

**archive.py (CRUD + 元数据):**
| 接口 | 功能 |
|------|------|
| `POST /courses` | 创建课程 |
| `GET /courses` | 获取课程列表 |
| `GET /courses/{id}` | 获取课程详情 |
| `PUT /courses/{id}` | 更新课程 |
| `DELETE /courses/{id}` | 删除课程 |
| `GET /courses/{id}/sages` | 获取关联 Sage |
| `GET /courses/{id}/sessions` | 获取会话列表 |
| `GET /courses/{id}/memory-facts` | 获取记忆事实 |
| `POST /worlds/{wid}/courses` | 在世界下创建课程 |
| `GET /worlds/{wid}/courses` | 获取世界课程 |

**learning.py (会话操作):**
| 接口 | 功能 |
|------|------|
| `POST /courses/{id}/start` | 开始学习 |
| `POST /courses/{id}/chat` | 发送消息 |

### 分析

虽然分散，但**职责清晰**：
- `archive.py` → 资源管理 (CRUD)
- `learning.py` → 学习会话 (业务逻辑)

### 建议行动

**无需改动**。这种分散符合单一职责原则。

如需改进，可考虑未来创建独立的 `courses.py` 路由文件。

---

## 4. 其他发现

### 4.1 Character 上传接口命名不一致

| 接口 | 路径 |
|------|------|
| 头像上传 | `POST /character/{id}/avatar` (单数) |
| 精灵图上传 | `POST /characters/{id}/sprites` (复数) |

### 4.2 World/Character 关联接口

存在两套语义相似的操作：

| 操作 | 接口 1 | 接口 2 |
|------|--------|--------|
| 添加角色到世界 | `POST /worlds/{wid}/characters` | - |
| 设置主角色 | - | `PUT /worlds/{wid}/characters/{id}/set-primary` |

这些接口**职责不同**，不算冗余。

---

## 5. 优先级修复计划

### Phase 1: 标记废弃 (立即)
```python
# save.py
@router.post("/save")
@deprecated("Use POST /checkpoints instead")
async def create_save_legacy(...):
    ...
```

### Phase 2: 前端迁移 (1-2 周)
- 前端将 `/save/*` 调用迁移到 `/checkpoints/*`
- 更新 API 文档

### Phase 3: 清理移除 (下个大版本)
- 删除 `create_save_legacy` 等 4 个接口
- 删除 `LegacySaveCreate`, `LegacySaveSummary` 模型

---

## 6. 接口路径索引

| 路由文件 | 接口数 | 主要职责 |
|----------|--------|----------|
| `archive.py` | ~50 | 角色、世界、课程、日记、进度 CRUD |
| `learning.py` | ~10 | 学习会话、聊天、用户画像 |
| `save.py` | ~12 | 检查点/存档、分支、时间线 |
| `auth.py` | ~5 | 认证 |
| `report.py` | TBD | 报告 |

**总计**: ~77 个接口（不含 auth.py 和 report.py）

---

## 7. 建议

1. **立即行动**: 在 `save.py` 中添加 `@deprecated` 装饰器
2. **文档更新**: 在 API 文档中标记 Legacy 接口为废弃
3. **前端协调**: 通知前端团队 planned migration path
4. **代码审查**: 未来新增接口时检查是否与现有接口功能重叠

---

## 附录 A: 完整 Legacy 接口清单

```python
# save.py - Legacy Save 接口
POST   /save                # → use POST /checkpoints
GET    /save                # → use GET /checkpoints
GET    /save/{save_id}      # → use GET /checkpoints/{id}
DELETE /save/{save_id}      # → use DELETE /checkpoints/{id}
```

---

## 附录 B: Timeline 接口重新设计建议

```python
# 选项 C: 重命名为 overview
GET /worlds/{world_id}/overview
# 返回:
{
    "world_id": int,
    "courses": [...],      # 新增：该世界的课程列表
    "sessions": [...],     # 现有
    "checkpoints": [...],  # 现有
    "stats": {             # 新增：聚合统计
        "total_sessions": int,
        "total_checkpoints": int,
        "last_activity": datetime
    }
}
```
