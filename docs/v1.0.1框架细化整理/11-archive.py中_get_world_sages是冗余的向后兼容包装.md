# 问题 11: `archive.py` 中 `_get_world_sages` 是冗余的向后兼容包装

## ✅ 已解决

**解决方案**: 函数已删除
**验证**: `grep "_get_world_sages" backend/api/routes/archive.py` 无结果

## 问题类型
冗余包装函数

## 涉及文件
- `backend/api/routes/archive.py` 第 539-541 行

## 具体描述

```python
def _get_world_sages(db: Session, world_id: int) -> list[SageInfo]:
    """Backward-compat wrapper."""
    return _get_world_characters_by_role(db, world_id, "sage")
```

这个函数是 `_get_world_characters_by_role(db, world_id, "sage")` 的单行包装，注释标注 "Backward-compat wrapper"。

但全局搜索显示，**没有任何地方调用 `_get_world_sages`**。所有使用处都已迁移为直接调用 `_get_world_characters_by_role`。

## 影响分析

1. **死代码**：未被调用的函数占用代码空间并增加理解负担
2. **误导性**：注释暗示存在需要向后兼容的调用方，但实际上已经没有

## 建议修复方向

直接删除 `_get_world_sages` 函数定义（第 539-541 行）。