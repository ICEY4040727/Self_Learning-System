# Learning 子系统深度 Review — 工作清单

> Branch: `feat/v1.0.3`
> Files: `backend/api/routes/learning.py` (502)
> Last updated: 2026-05-02

## 结论：无 P0/P1 问题，全部 deferred

### TODO-L1 🟡 P2 — `start_learning` 查 Character 两次
- **位置**: L198 + L222-223
- **问题**: sage_character 查了两次（第一次拿 system_prompt，第二次 "for sprites"）
- **修复**: 复用第一次查询结果
- **决定**: 下个迭代

### TODO-L2 🟢 P3 — `_get_session_characters` fallback 逻辑可疑
- **位置**: L109-116
- **问题**: teacher_persona_id fallback 查 `WorldCharacter.id == teacher_persona_id`，但 teacher_persona_id 原来是 TeacherPersona 表的 ID，不是 WorldCharacter ID
- **影响**: 旧数据走这个路径会找不到（返回 None），但不会崩溃。新数据不走此路径
- **决定**: 不修 — TeacherPersona 已删除，旧 Session 也不多

### TODO-L3 🟢 P3 — 多处函数内 import
- LearnerProfile, user_profile 等
- **决定**: 不修 — 下个迭代统一整理

### 安全审查
- ✅ 所有 endpoint 正确校验 `user_id == current_user.id`
- ✅ 无路径穿越 / IDOR 风险
- ✅ ChatMessage 写入使用 session 的 user_id 过滤