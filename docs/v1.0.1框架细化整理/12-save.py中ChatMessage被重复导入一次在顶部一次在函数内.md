# 问题 12: `save.py` 中 `ChatMessage` 被重复导入 — 顶部和函数内各一次

## ✅ 已解决

**解决方案**: 
1. ChatMessage 仅在顶部导入，函数内不再重复导入
2. 提取 `_get_session_messages` 和 `_count_session_messages` 辅助函数减少重复查询
**验证**: 函数内无 ChatMessage 导入；辅助函数已定义并被多处使用


## 问题类型
冗余导入 / 逻辑不清

## 涉及文件
- `backend/api/routes/save.py` 第 13 行（顶部导入）
- `backend/api/routes/save.py` 第 192 行（`_build_checkpoint_response` 内部）

## 具体描述

**顶部导入（第 12-20 行）：**
```python
from backend.models.models import (
    Character,
    ChatMessage,      # ← 已在顶部导入
    Checkpoint,
    Course,
    LearnerProfile,
    TeacherPersona,
    User,
    World,
)
```

**函数内重复导入（第 192 行）：**
```python
def _build_checkpoint_response(cp: Checkpoint, db: Session, user_id: int) -> CheckpointResponse:
    ...
    if cp.session_id:
        from backend.models.models import ChatMessage  # ← 冗余，已在顶部导入
        last_msgs = db.query(ChatMessage).filter(...)
```

同样，`ProgressTracking`（第 181 行）也在函数内内联导入，但顶部未导入 — 这种不一致的导入策略令人困惑。

## 影响分析

1. **代码不一致**：同文件中有些模型在顶部导入，有些在函数内导入，没有统一策略
2. **增加阅读负担**：看到 `from backend.models.models import ChatMessage` 在函数内部时，需要确认顶部是否已导入
3. **性能影响（极小）**：虽然 Python 会缓存模块，但函数内导入仍是不必要的额外操作

## 建议修复方向

1. 统一策略：所有模型导入都放在文件顶部
2. 删除 `_build_checkpoint_response` 中的 `from backend.models.models import ChatMessage`（已在顶部导入）
3. 将 `from backend.models.models import ProgressTracking` 移动到文件顶部
4. 检查 `archive.py` 和 `learning.py` 中的类似内联导入，一并清理