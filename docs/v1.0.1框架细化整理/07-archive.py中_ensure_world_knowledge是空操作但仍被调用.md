# 问题 07: `archive.py` 中 `_ensure_world_knowledge` 是空操作但仍被多处调用

## 问题类型
死代码 / 逻辑不清

## 涉及文件
- `backend/api/routes/archive.py` 第 508-510 行（函数定义）
- `backend/api/routes/archive.py` 第 627、744、840 行（调用点）

## 具体描述

```python
def _ensure_world_knowledge(db: Session, world_id: int) -> None:
    """Knowledge graph is deprecated in P1 #183. This function is a no-op."""
    pass
```

这个函数已被标记为废弃（P1 #183），实现为 `pass`，但仍在三处被调用：
1. `create_world`（第 627 行）
2. `create_world_character`（第 744 行）
3. `set_world_character_primary`（第 840 行）

## 影响分析

1. **混淆读者**：新开发者会疑惑为什么一个什么都不做的函数被反复调用
2. **函数调用开销**：虽然极小，但属于无意义开销
3. **与注释矛盾**：注释说 deprecated，但代码仍主动调用它

## 建议修复方向

1. 直接删除函数定义和所有调用点
2. 如果未来可能重新引入 knowledge graph，在 git history 中保留记录即可