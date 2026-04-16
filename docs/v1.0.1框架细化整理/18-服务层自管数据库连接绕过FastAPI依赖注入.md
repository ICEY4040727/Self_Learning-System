# 问题 18: 服务层自管数据库连接绕过 FastAPI 依赖注入

## ✅ 已解决

**解决方案**: 
1. `dynamic_analyzer.py` 中已清理（SessionLocal 已移除）
2. `learning_engine.py` 中已清理（PR #243）
   - 删除 SessionLocal 导入
   - db 参数改为必填
   - 删除 own_db fallback 逻辑

**验证**: `grep "SessionLocal" backend/services/learning_engine.py` 无结果

**关联**: #242 — 已合并


## 问题类型
架构问题 / 潜在资源泄漏

## 涉及文件
- `backend/services/dynamic_analyzer.py` 第 243-249、291-297 行
- `backend/services/learning_engine.py`（类似模式）

## 具体描述

多个 service 方法采用 "如果没有传入 db 就自己创建" 的模式：

```python
async def update_relationship_stage(self, session_id, emotion, db=None):
    from backend.db.database import SessionLocal
    from backend.models.models import ChatMessage

    own_db = False
    if not db:
        db = SessionLocal()
        own_db = True

    try:
        # ... 查询操作 ...
    finally:
        if own_db:
            db.close()

async def update_learner_profile(self, user_id, world_id, interaction, db=None):
    from backend.db.database import SessionLocal
    from backend.models.models import LearnerProfile

    own_db = False
    if not db:
        db = SessionLocal()
        own_db = True

    try:
        # ... 查询和写入操作 ...
    finally:
        if own_db:
            db.commit()
            db.close()
```

## 影响分析

1. **绕过 FastAPI 的请求级 Session 管理**：FastAPI 通过 `Depends(get_db)` 管理 Session 生命周期（请求结束自动关闭/回滚），自管连接脱离了这个安全网
2. **`update_learner_profile` 在 finally 中 `commit()`**：如果调用方已经在一个事务中做了修改，自管连接的 commit 不会影响调用方的事务，但数据一致性难以保证
3. **异常处理不完整**：`update_relationship_stage` 的 finally 只做 `db.close()`，没有 commit 也没有 rollback；如果查询中途异常，连接状态不确定
4. **两个方法中的 `own_db` 模式完全重复**：可提取为装饰器或上下文管理器

## 调查结论（2026-04-14）

### 实际情况：自管连接的触发条件

| 方法 | 是否被调用 | 调用方是否传 db | SessionLocal 是否实际触发 |
|------|-----------|----------------|--------------------------|
| `update_relationship_stage` | ❌ 零调用（死代码） | — | 永远不触发 |
| `update_learner_profile` | ✅ learning_engine.py:274 | ✅ 已传 `db=db` | 永远不触发（正常流程） |

关键发现：**所有实际调用方都已经传入了 `db` 参数**，`SessionLocal()` 的 fallback 分支在正常流程中永远不会执行。

## ✅ 已确认修复方案

### 步骤 1：删除 `update_relationship_stage`（联动 #17）

该方法为死代码，已在 #17 中确认删除。删除后消除 1 处 `SessionLocal` 引用（第 243-249 行）。

### 步骤 2：简化 `update_learner_profile`，移除自管连接

```python
# 修改前：
async def update_learner_profile(self, user_id: int, world_id: int, interaction: dict, db=None):
    from backend.db.database import SessionLocal
    from backend.models.models import LearnerProfile

    own_db = False
    if not db:
        db = SessionLocal()
        own_db = True
    try:
        # ... 业务逻辑 ...
    finally:
        if own_db:
            db.commit()
            db.close()

# 修改后：
async def update_learner_profile(self, user_id: int, world_id: int, interaction: dict, db: Session):
    from backend.models.models import LearnerProfile

    # ... 业务逻辑（移除 try/finally 和 own_db）...
```

变更要点：
- `db` 参数从 `db=None` 改为 `db: Session`（必填）
- 删除 `SessionLocal` 导入和 `own_db` 模式
- 删除 `try/finally` 中的自管关闭逻辑
- 业务逻辑不变，commit 由调用方管理

### 步骤 3：验证调用方

确认 `learning_engine.py:274` 已传 `db=db`，无需修改调用方。

### 影响面

| 文件 | 变更 | 风险 |
|------|------|------|
| `dynamic_analyzer.py` | 删除 `update_relationship_stage` 整个方法 | 无（零调用） |
| `dynamic_analyzer.py` | 简化 `update_learner_profile` 签名 | 低（调用方已传 db） |
| `learning_engine.py` | 无需修改 | — |

### 总收益

- **彻底消除** `dynamic_analyzer.py` 中所有 `SessionLocal` 引用（4 处 → 0 处）
- **删除 ~80 行**自管连接代码
- `dynamic_analyzer.py` 只保留 `analyze_emotion` 和 `_llm_analyze`（纯 LLM 调用，无 DB 操作）
