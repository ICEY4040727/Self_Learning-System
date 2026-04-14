# API 接口冗余分析报告

> 生成时间: 2026-04-13
> 分析者: Creator (架构审查视角)
> 分析范围: backend/api/routes/
> **重要**: 本报告发现的冗余问题**已存在于 main 分支**，非 PR #203 引入。本次分析仅是系统性梳理。

---

## 执行摘要

经分析，发现 **3 类冗余设计**，涉及 **16 个接口**：

| 类别 | 冗余程度 | 影响接口数 | 优先级 |
|------|----------|-----------|--------|
| Legacy Save 接口 | 高 | 4 | P0 |
| Timeline 接口功能重叠 | 中 | 1 | P1 |
| Course 路由分散 | 低 | 10 | P2 |

---

## 0. PR #203 关联性结论

### 问题：这些冗余是否由 PR #203 引入？

**答案：否。**

| 问题 | 是否由 PR #203 引入 | 引入时间/来源 |
|------|---------------------|---------------|
| Legacy Save 接口冗余 | **否** | `6b47632` - API compatibility fix (PR #135) |
| Timeline 接口重叠 | **否** | 已存在于 main 分支 |
| Course 路由分散 | **否** | 架构设计决策，非 bug |

### 证据

```bash
# main 分支中已存在 Legacy Save 接口
$ git show main:backend/api/routes/save.py | grep "def.*save_legacy"
462:async def create_save_legacy(
481:async def list_save_legacy(
524:async def get_save_legacy(
578:async def delete_save_legacy(
```

### 结论

> **PR #203 是 UI polish 工作（统一页面风格、修复滚动问题），不应承担这些历史债务的修复责任。**
>
> 本报告分析的问题属于**历史遗留的技术债务**，应在独立的技术债务清理迭代中处理。

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

---

## 2. P1: Timeline 接口功能重叠

### 问题描述

`save.py` 的 `/worlds/{world_id}/timelines` 接口返回 sessions + checkpoints，与以下接口存在功能重叠：

| 现有接口 | 功能 |
|----------|------|
| `GET /sessions` | 获取会话列表（按课程筛选） |
| `GET /checkpoints?world_id=X` | 获取检查点列表 |

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

Course 相关接口分散在 `archive.py` 和 `learning.py` 两个文件。

### 分析

虽然分散，但**职责清晰**：
- `archive.py` → 资源管理 (CRUD)
- `learning.py` → 学习会话 (业务逻辑)

### 建议行动

**无需改动**。这种分散符合单一职责原则。

---

## 4. 技术债务清理迭代方案

### 方案概览

| 阶段 | 目标 | 预计工作量 | 风险 |
|------|------|-----------|------|
| Phase 0 | 评估与确认 | 0.5 天 | 低 |
| Phase 1 | 标记废弃 | 0.5 天 | 低 |
| Phase 2 | 前端迁移 | 2-3 天 | 中 |
| Phase 3 | 后端清理 | 1 天 | 低 |
| Phase 4 | 验证与部署 | 0.5 天 | 中 |

**总计**: 约 5 个工作日

---

### Phase 0: 评估与确认 (0.5 天)

**目标**: 确认前端是否仍在使用 Legacy 接口

```bash
# 检查前端代码中的调用
cd frontend
grep -r "api/save" src/
grep -r "'/save" src/
grep -r '"/save' src/
```

**输出清单**:
- [ ] 列出所有使用 `/save/*` 的组件
- [ ] 评估迁移工作量
- [ ] 与前端确认迁移计划

**验收标准**: 生成《前端 Legacy API 调用清单》

---

### Phase 1: 标记废弃 (0.5 天)

**目标**: 在代码中标记 Legacy 接口为废弃

#### 1.1 添加 deprecation 警告

```python
# backend/api/routes/save.py

import warnings

def _deprecated_save_warning():
    warnings.warn(
        "Legacy /save/* endpoints are deprecated. Use /checkpoints/* instead.",
        DeprecationWarning,
        stacklevel=3
    )

@router.post("/save")
async def create_save_legacy(...):
    _deprecated_save_warning()
    # ... 现有代码

@router.get("/save")
async def list_save_legacy(...):
    _deprecated_save_warning()
    # ... 现有代码

@router.get("/save/{save_id}")
async def get_save_legacy(...):
    _deprecated_save_warning()
    # ... 现有代码

@router.delete("/save/{save_id}")
async def delete_save_legacy(...):
    _deprecated_save_warning()
    # ... 现有代码
```

#### 1.2 更新 API 文档

```python
"""
Legacy Save Endpoints (Deprecated)

.. deprecated:: 1.1
    Use POST /checkpoints instead of POST /save
    Use GET /checkpoints instead of GET /save
    Use GET /checkpoints/{id} instead of GET /save/{id}
    Use DELETE /checkpoints/{id} instead of DELETE /save/{id}

These endpoints are maintained for backward compatibility only
and will be removed in version 2.0.
"""
```

**验收标准**:
- [ ] Legacy 接口调用时触发 deprecation 警告
- [ ] API 文档标记为废弃
- [ ] 日志中记录 Legacy 接口调用情况

---

### Phase 2: 前端迁移 (2-3 天)

**目标**: 前端完全迁移到 Checkpoint 接口

#### 2.1 迁移映射表

| 旧接口 | 新接口 | 参数变化 |
|--------|--------|----------|
| `POST /save` | `POST /checkpoints` | `subject_id` → `world_id` |
| `GET /save?subject_id=X` | `GET /checkpoints?world_id=X` | 同名 |
| `GET /save/{id}` | `GET /checkpoints/{id}` | 同名 |
| `DELETE /save/{id}` | `DELETE /checkpoints/{id}` | 同名 |

#### 2.2 组件迁移清单

| 组件 | 当前使用接口 | 迁移后 | 优先级 |
|------|-------------|--------|--------|
| `Archive.vue` | `/save/*` | `/checkpoints/*` | P0 |
| `CheckpointPanel.vue` | `/save/*` | `/checkpoints/*` | P0 |
| 其他组件 | - | - | - |

#### 2.3 测试计划

```javascript
// frontend/e2e/checkpoint-migration.spec.mjs
import { test, expect } from '@playwright/test';

test.describe('Checkpoint API Migration', () => {
  test('should use /checkpoints for creating save', async ({ page }) => {
    // 监听网络请求
    const apiCalls = [];
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiCalls.push(request.url());
      }
    });

    // 执行存档操作
    await page.goto('/archive');
    await page.click('[data-testid="create-checkpoint-btn"]');

    // 验证没有调用 /save
    expect(apiCalls.some(url => url.includes('/save'))).toBeFalsy();
    expect(apiCalls.some(url => url.includes('/checkpoints'))).toBeTruthy();
  });
});
```

**验收标准**:
- [ ] 前端代码无 `/save/*` 调用
- [ ] 所有 E2E 测试通过
- [ ] 手动测试存档功能正常

---

### Phase 3: 后端清理 (1 天)

**目标**: 移除 Legacy 接口代码

#### 3.1 删除清单

```bash
# 删除以下函数和模型
- create_save_legacy()
- list_save_legacy()
- get_save_legacy()
- delete_save_legacy()
- LegacySaveCreate
- LegacySaveSummary
```

#### 3.2 清理后的 save.py 结构

```python
# backend/api/routes/save.py (清理后)

from datetime import UTC, datetime
# ... imports

router = APIRouter()

# ========== Checkpoint Endpoints ==========
@router.post("/checkpoints", response_model=CheckpointResponse)
async def create_checkpoint(...): ...

@router.get("/checkpoints", response_model=list[CheckpointResponse])
async def list_checkpoints(...): ...

@router.get("/worlds/{world_id}/checkpoints", response_model=list[CheckpointResponse])
async def list_world_checkpoints(...): ...

@router.post("/checkpoints/{checkpoint_id}/branch")
async def branch_from_checkpoint(...): ...

@router.get("/checkpoints/{checkpoint_id}")
async def get_checkpoint(...): ...

@router.delete("/checkpoints/{checkpoint_id}")
async def delete_checkpoint(...): ...

@router.get("/worlds/{world_id}/timelines")
async def get_world_timelines(...): ...

@router.get("/worlds/{world_id}/knowledge-graph")
async def get_knowledge_graph(...): ...

# ========== Import/Export (Phase 1 #193) ==========
@router.get("/checkpoints/{checkpoint_id}/export")
async def export_checkpoint(...): ...

@router.post("/checkpoints/import")
async def import_checkpoint(...): ...
```

**验收标准**:
- [ ] 代码中无 Legacy 相关函数
- [ ] 无未使用的 import
- [ ] Ruff lint 通过

---

### Phase 4: 验证与部署 (0.5 天)

**目标**: 确保迁移后系统正常工作

#### 4.1 验证清单

- [ ] 后端单元测试通过
- [ ] 前端 E2E 测试通过
- [ ] 手动测试存档创建/加载/删除
- [ ] 手动测试分支功能
- [ ] 手动测试导入/导出

#### 4.2 回滚计划

如果出现问题：
1. 立即回滚到迁移前的 commit
2. 保留 Legacy 接口
3. 分析失败原因
4. 重新规划迁移

---

### 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 前端有未发现的 Legacy 调用 | 中 | 高 | Phase 0 全面检查 + 测试 |
| 迁移后功能回归 | 低 | 高 | 完整的 E2E 测试 |
| 用户收藏的书签失效 | 低 | 低 | 返回 301 重定向 |

---

### 后续优化建议

完成 Legacy Save 清理后，可考虑：

1. **Timeline 接口重构** (P1)
   - 重命名为 `/worlds/{id}/overview`
   - 添加更多聚合统计

2. **Character 接口命名统一** (P2)
   - 统一使用单数或复数形式
   - `/character/{id}/avatar` → `/characters/{id}/avatar`

3. **API 版本管理** (长期)
   - 引入 `/api/v1/` 前缀
   - 便于未来不兼容升级

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

---

## 附录 C: 历史追溯

### Legacy Save 接口引入时间线

| Commit | 描述 | 影响 |
|--------|------|------|
| `beec7cf` | World system WIP | 首次引入 Checkpoint 接口 |
| `6b47632` | API compatibility fix | **新增 Legacy Save 接口** |
| `b937a00` | address reviewer feedback | 修复 Legacy Save 过滤逻辑 |
| `1f13f18` | migrate archive page | 前端使用 `/save/*` 路径 |

### 设计原因

当时存在**前端已经使用 `/save/*` 路径**的情况，为了不破坏前端，后端保留了 Legacy 接口作为适配层。

---


   任务清单
   • [x]
     Phase 0: 前端 Legacy API 调用检查 ✅
   • [ ]
     Phase 1: 后端标记 Legacy 接口为废弃
   • [ ]
     Phase 2: 等待一个版本周期
   • [ ]
     Phase 3: 移除 Legacy 接口代码
