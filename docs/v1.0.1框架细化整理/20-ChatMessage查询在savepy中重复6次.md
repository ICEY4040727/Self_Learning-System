# 问题 20: `ChatMessage` 查询逻辑在 `save.py` 中重复 6 次

## ✅ 已解决

**解决方案**: 提取 `_get_recent_messages` 和 `_get_message_count` 辅助函数
**PR**: #210 → #217

## 问题类型

## 问题类型
重复查询逻辑（问题 #14 的加剧）

## 涉及文件
- `backend/api/routes/save.py` 第 132、248、325、527、643、850 行

## 具体描述

`db.query(ChatMessage)` 在 `save.py` 中出现了 **6 次**，其中多处查询模式高度相似：

| 行号 | 函数 | 查询目的 |
|------|------|----------|
| 132 | `_build_checkpoint_response` | 获取最近 20 条消息构建预览 |
| 248 | `create_checkpoint` | 获取聊天历史写入存档文件 |
| 325 | `create_checkpoint` | 统计消息总数 |
| 527 | `get_checkpoint` | 从 DB 读取聊天历史 |
| 643 | `export_checkpoint` | 导出时读取聊天历史 |
| 850 | `get_save_detail` (Legacy) | 遗留接口读取消息 |

其中行 132、248、527、643 的查询模式几乎一致：
```python
db.query(ChatMessage).filter(
    ChatMessage.session_id == session_id
).order_by(ChatMessage.created_at.asc()).all()
```

## 根因分析

Issue #207 Phase 1 在已有 3 次重复（#14 已记录）的基础上，新增了 3 处查询（export、import、file-read fallback），使重复从 3 次增加到 6 次。

## ✅ 已确认修复方案

### 方案：提取 `_get_session_messages()` 辅助函数

```python
def _get_session_messages(
    db: Session,
    session_id: int,
    *,
    limit: int | None = None,
    order: str = "asc",
) -> list[ChatMessage]:
    """获取指定会话的消息列表。"""
    q = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
    q = q.order_by(
        ChatMessage.created_at.asc() if order == "asc" else ChatMessage.created_at.desc()
    )
    if limit is not None:
        q = q.limit(limit)
    return q.all()
```

### 步骤

1. 在 `save.py` 顶部（导入后）定义 `_get_session_messages()` 辅助函数
2. 6 处调用统一替换：
   - 行 132：`_get_session_messages(db, session_id, limit=20)`
   - 行 248：`_get_session_messages(db, db_session.id)`
   - 行 325：`db.query(ChatMessage).filter(...).count()` → 保留为 `_count_session_messages()` 或直接用 `len(_get_session_messages(...))`（注：count 查询更高效，可单独提取 `_count_session_messages()`）
   - 行 527：`_get_session_messages(db, db_session.id)`
   - 行 643：`_get_session_messages(db, db_session.id)`
   - 行 850：删除（联动 #06，遗留接口整体删除）
3. 删除遗留接口（#06）可消除行 850 的查询 → 实际只需替换 4 处 + 1 处 count

### 额外提取：`_count_session_messages()`

```python
def _count_session_messages(db: Session, session_id: int) -> int:
    """统计指定会话的消息数量。"""
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
```

### 放在哪里

- 放在 `save.py` 文件内作为模块级私有函数
- 与 #14 的 `_get_active_session()` 遵循相同设计模式：各文件各自提取

### 影响面

| 文件 | 变更 | 风险 |
|------|------|------|
| `save.py` | 提取 2 个辅助函数 + 替换 5 处调用 | 低（纯重构） |
| 行 850（Legacy） | 随 #06 一并删除 | 无 |

### 联动

- #06（遗留代码）：删除遗留接口后，行 850 的查询自动消失
- #14（learning.py 查询重复）：相同模式，各文件各自提取辅助函数
- #12（重复导入）：重构时一并清理 ChatMessage 的重复导入
