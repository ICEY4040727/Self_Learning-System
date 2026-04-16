# 问题 05: `start_learning` 函数两条路径的返回字典几乎完全重复

## ✅ 已解决

**解决方案**: 提取 `_build_start_response` 辅助函数统一返回格式
**PR**: #212 → #219

## 问题类型
代码重复（同一函数内）

## 涉及文件
- `backend/api/routes/learning.py` 第 78-197 行（`start_learning` 函数）

## 重复内容

函数有两个主要分支：
1. **复用已有 session**（第 98-125 行）：查到 existing session → 构造返回字典
2. **创建新 session**（第 127-197 行）：创建新 session → 构造返回字典

两条路径的返回字典结构完全一致，包含相同字段：
```python
return {
    "session_id": ...,
    "teacher_persona": ...,
    "course": course.name,
    "relationship_stage": ...,
    "relationship": ...,
    "greeting": ...,
    "scenes": ...,
    "sage_sprites": ...,
    "traveler_sprites": ...,
    "character_sprites": ...,  # 同样的冗余字段（见问题 04）
}
```

## 影响分析

1. **维护负担**：新增或修改响应字段时，必须同步修改两处
2. **容易出现微妙不一致**：两条路径的字段已经存在细微差异（relationship_stage 的取值逻辑略有不同）
3. **函数过长**：`start_learning` 函数体约 120 行，远超合理长度

## 建议修复方向

1. 提取返回值构造为独立函数，如 `_build_start_response(session, course, teacher_persona, sage, traveler)`
2. 在两条路径末尾统一调用此函数
3. 这也会自然解决问题 04（`character_sprites` 冗余）