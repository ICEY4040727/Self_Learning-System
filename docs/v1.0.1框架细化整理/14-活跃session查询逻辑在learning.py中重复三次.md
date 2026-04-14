# 问题 14: 活跃 session 查询逻辑在 `learning.py` 中重复三次

## 问题类型
重复查询逻辑

## 涉及文件
- `backend/api/routes/learning.py` 第 95、212、222 行

## 重复内容

活跃 session 的查询模式出现 3 次：

```python
db.query(SessionModel).filter(
    SessionModel.course_id == course_id,
    SessionModel.user_id == current_user.id,
    SessionModel.ended_at == None
).first()
```

## ✅ 已确认修复方案

### 方案：提取 `_get_active_session()` 辅助函数

```python
def _get_active_session(db: Session, course_id: int, user_id: int) -> SessionModel | None:
    """获取指定课程和用户的活跃会话（未结束）。"""
    return db.query(SessionModel).filter(
        SessionModel.course_id == course_id,
        SessionModel.user_id == user_id,
        SessionModel.ended_at == None,
    ).first()
```

### 步骤

1. 在 `learning.py` 顶部定义 `_get_active_session()` 辅助函数
2. 第 95 行：替换为 `existing = _get_active_session(db, course_id, current_user.id)`
3. 第 212 行：替换为 `existing = _get_active_session(db, course_id, current_user.id)`
4. 第 222 行：替换为 `existing = _get_active_session(db, course_id, current_user.id)`
5. 使用 SQLAlchemy 的 `is_(None)` 替代 `== None`（PEP 8 兼容）

### 放在哪里

- 放在 `learning.py` 文件内作为模块级私有函数
- 不提取到 models，因为这是路由层的查询逻辑

### 影响面

| 文件 | 变更 | 风险 |
|------|------|------|
| `learning.py` | 提取 1 个辅助函数 + 替换 3 处 | 低（纯重构） |

### 联动

- #20（save.py ChatMessage 查询重复 6 次）：类似的模式，各文件各自提取辅助函数
- 两者不共享辅助函数（查询不同模型、不同文件），但遵循相同的设计模式