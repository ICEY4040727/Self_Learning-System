# Archive 子系统深度 Review — 工作清单

> Branch: `feat/v1.0.3`
> Scope: 世界/角色/课程/档案 CRUD + persona 生成
> Files: `backend/api/routes/archive.py` (1720)
> Last updated: 2026-05-02

---

## 1. 已修复

（暂无）

## 2. 发现清单

### TODO-A1 🔴 P0 — `generate_persona` world 查询缺少 user_id filter → IDOR

- **位置**: L1646-1648
- **问题**: `world = db.query(World).filter(World.id == req.world_id).first()` 没有 `World.user_id == current_user.id`。攻击者可探测其他用户的 world 是否存在（通过观察返回 vs 空）。
- **修复**: 加 user_id filter，找不到直接 skip world_context（不报错，因为 world_id 是 optional）。

### TODO-A2 🟠 P1 — `get_worlds` 不传 user_id → 课程进度永远 null

- **位置**: L588 `[_build_world_response(w, db) for w in worlds]`
- **问题**: `_build_world_response` 接受可选 `current_user_id`，`get_worlds` 调用时没传。导致 world 列表视图中每个课程的 `progress` 永远是 `None`。
- **修复**: 改为 `[_build_world_response(w, db, current_user.id) for w in worlds]`。

### TODO-A3 🟡 P2 — delete endpoints 返回 body 而非 204

- **位置**: L357-372 (character), L628-642 (world), L798-821 (world_character), L1134-1142 (course)
- **问题**: 和 save.py S12 一样的反模式 — 返回 `{"message": "X deleted"}` 但没 response_model。
- **修复**: 加 `status_code=204`，去掉 body。

### TODO-A4 🟡 P2 — `_get_world_characters_by_role` N+1 查询

- **位置**: L470-493
- **问题**: 循环里每个 link 单独 `db.query(Character).filter(Character.id == link.character_id).first()`。如果 world 有 5 个 character，就是 5 次 DB round-trip。
- **修复**: 先收集所有 character_id，一次 `IN` 查询拿到 dict，再循环构建 SageInfo。

### TODO-A5 🟡 P2 — `get_world_characters` 也是 N+1

- **位置**: L713-729
- **问题**: 同 A4 模式。
- **修复**: 同 A4。

### TODO-A6 🟢 P3 — `get_course_sessions` 内部 import

- **位置**: L1206 `from sqlalchemy import func as sa_func`
- **问题**: 应该在文件顶部 import。
- **修复**: 移到文件顶部。

### TODO-A7 🟢 P3 — 1720 行单文件过大

- **问题**: archive.py 包含 character/world/course/learner_profile/progress/diary/sprites/persona 所有路由。应拆分。
- **修复**: 下个迭代拆分。当前不阻塞。

---

## 3. 决定

| 项 | 决定 |
|---|---|
| A1 | **修** — IDOR 安全问题 |
| A2 | **修** — 一行改动 |
| A3 | **修** — 与 save.py 保持一致 |
| A4/A5 | **不修** — P2 性能优化，下个迭代 |
| A6 | **修** — trivial |
| A7 | **不修** — 拆分是独立 PR |