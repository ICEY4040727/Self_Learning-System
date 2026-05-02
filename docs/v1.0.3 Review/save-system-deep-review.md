# 存档子系统深度 Review — 工作清单

> Branch: `feat/v1.0.3`
> Scope: 存档保存 / 加载 / 导入导出 / 分支
> Files in scope:
> - `backend/services/save_file_manager.py` (162)
> - `backend/api/routes/save.py` (700)
> - `backend/tests/test_save_file_manager.py` (93)
> - 数据模型：`Checkpoint` (models.py:489+)
> Last updated: 2026-04-29

同前几片 review，本文档是工作记录。**Claude 上下文窗口有限，本文档是唯一可信的进度来源**。

---

## 1. 已修复（已 commit）

| ID | 问题 | 修复 | 验证 |
|---|---|---|---|
| **S1** | `read/delete/get_file_size` 不校验路径 → 路径穿越 | `_resolve_and_validate` 方法 + 3 个测试 | pytest |
| **S2** | `read_save_file` 不知道 user_id → 跨用户读取 | `user_id` 参数 + path 首段校验 + 2 个测试 | pytest |
| **S3** | `_build_full_save_data` MemoryFact 缺 world_id filter | 加 `(world_id == ...) | (world_id.is_(None))` | code review |
| **S4** | 存档不含 ConceptMastery 数据 | 查 `ConceptMastery` + `progress_snapshot` 改 `{"concepts": [], "lessons": []}` | code review |
| **S5** | `write_save_file` 非原子写入 | tmp + rename 模式 + 1 个测试 | pytest |
| **S6** | `delete_checkpoint` 文件先删 DB 后删 | 调换顺序：DB delete+commit 先，文件后删 | code review |
| **S7** | `MAX_FILE_SIZE_BYTES` 死代码 | 删除常量（用户决定不设上限） | code review |
| **S9** | `_get_checkpoint_state` 文件缺失沉默 fallback | 加 `logger.warning` | code review |
| **S12** | `delete_checkpoint` 缺 status_code=204 | 加 `status_code=204`，删 body | code review |

---

## 2. 待修复 — 初轮扫描发现

### 严重等级图例
- 🔴 P0：安全漏洞 / 数据泄漏 / 必炸
- 🟠 P1：高风险 / 部分写入 / stale code
- 🟡 P2：bug 但有兜底 / 性能 / 设计冲突
- 🟢 P3：代码质量 / 测试缺失

---

### TODO-S1 ✅ — `read/delete/get_file_size` 不校验路径在 SAVE_DIR 内 → 路径穿越 🔴 **P0**

- **位置**：`save_file_manager.py:73, 92, 110`
- **问题**：三个静态方法接受 `relative_path: str` 直接拼接 `SAVE_DIR / relative_path`。Python 的 `/` 算子接受绝对路径就会丢弃 base：
  ```python
  Path("/a") / "/etc/passwd" == Path("/etc/passwd")  # ← 直接逃出 SAVE_DIR
  Path("/a") / "../../etc/passwd"  # ← 通过 .. 逃出
  ```
- **触发路径**：理论上 `Checkpoint.file_path` 来自 DB（由 `write_save_file` 写入正常 relative path），但任何向 DB 写 file_path 的新代码、SQL race、未来的 import 路径都可能污染。**没有写时纠正、读时校验**就等于把 base 拉满到无防御。
- **修复**：每个方法 entry 处 normalize + 验证 resolve 后仍在 SAVE_DIR 内：
  ```python
  full = (SAVE_DIR / relative_path).resolve()
  base = SAVE_DIR.resolve()
  if base not in full.parents and full != base:
      raise ValueError("path escape")
  ```
- **测试**：注入 `../../etc/passwd` 和绝对路径，断言 raise。

---

### TODO-S2 ✅ — `read_save_file` 不知道 user_id → cross-user 读取 🔴 **P0**

- **位置**：`save_file_manager.py:73`，调用方 `save.py:191` `_get_checkpoint_state`
- **问题**：`SaveFileManager.read_save_file(relative_path)` 不带 user 信息。文件按 `{user_id}/...` 组织，但读取时不校验 path 的第一段 == 当前 user。如果 SQL race / bug 让 user A 的 `checkpoint.file_path` 变成 `2/foo.json`（另一个用户的目录），他读到 user B 的存档。
- **修复**：API 层（`get_checkpoint` / `export_checkpoint` / `_get_checkpoint_state`）传 `user_id` 给 `read_save_file`，方法内校验 path 起始段 == user_id；或者直接由 SaveFileManager 接收 `(user_id, filename)` 而非自由 relative_path。
- **测试**：构造 user A 的 checkpoint 但 file_path 指向 user B 目录的文件，断言 read 返回 None / 抛异常。

---

### TODO-S3 ✅ — `_build_full_save_data` MemoryFact 缺 world_id filter → 跨世界数据泄漏 🟠 **P1**

- **位置**：`save.py:147-159`
- **问题**：
  ```python
  facts = db.query(MemoryFact).filter(
      MemoryFact.character_id == db_session.sage_character_id
  ).order_by(MemoryFact.salience.desc()).limit(50).all()
  ```
  没有 world_id filter。同一 sage character 在 world A 和 world B 都教学时，world A 的 checkpoint 会把 world B 的 MemoryFact 也存进去。前几片 review (R1-01) 已为 `observe_recent` 加过 world_id filter，但 save 这条路径漏了。
- **修复**：加 `(MemoryFact.world_id == checkpoint.world_id) | (MemoryFact.world_id.is_(None))`（与 R1-01 语义一致）。
- **测试**：两个 world 同 sage 各写 fact，存档 world A 的 checkpoint 后断言只含 world A + nullable 的 fact id。

---

### TODO-S4 ✅ — `_build_full_save_data` 仍查 ProgressTracking → concept 掌握度永远丢失 🟠 **P1**

- **位置**：`save.py:163-175`
- **问题**：concept 掌握度已经在 redesign 中迁移到 `concept_mastery` 表（TR-A1+A2），ProgressTracking 现在只剩 lesson 行。本函数还在查 ProgressTracking 拿 `topic + mastery_level`，意味着：
  - 存档里 progress_snapshot.topics 全是 lesson 进度（"L1: 20" 之类的初始 mastery）
  - 跨世界共享的 concept 掌握度（"递归: 75"）**完全没存进去**
  - 如果用户 restore 旧存档到一个空的 concept_mastery 状态，会丢失所有学习进度
- **修复**：改为查 `ConceptMastery` 表（user_id == ..., concept_id IN <user's all concepts>），同时**保留 ProgressTracking lesson 行的查询**（写到 progress_snapshot 的另一字段），区分两类。
- **同步改 schema**：`progress_snapshot` 改为 `{"concepts": [...], "lessons": [...]}` 而非旧的 `{"topics": [...]}`。需要一个 schema bump（v2.0 → v2.1）和 restore 时识别两个版本。
- **测试**：concept_mastery + progress_trackings 各写一条，存档读回后断言两类都在。

---

### TODO-S5 ✅ — `create_checkpoint` 写盘非原子 → 半文件风险 🟠 **P1**

- **位置**：`save_file_manager.py:62` `filepath.write_text(content)`
- **问题**：`Path.write_text` 不是原子写入 — 它是 open(w) → write → close。中途 OOM / SIGTERM / 磁盘满会留半个 JSON 文件。下次 `read_save_file` 拿到这个半文件 → `json.loads` 抛 → 返回 None → 用户存档"消失"。
- **修复**：tmp + rename 模式：
  ```python
  tmp = filepath.with_suffix(".json.tmp")
  tmp.write_text(content)
  tmp.replace(filepath)  # POSIX rename 是原子的
  ```
- **测试**：mock write_text 抛异常，断言不留临时文件 / 主文件未污染。

---

### TODO-S6 ✅ — `delete_checkpoint` 文件先删 DB 后删 → DB 失败时 ghost row 🟠 **P1**

- **位置**：`save.py:418-423`
- **问题**：跟教材 X5 一模一样的反模式 — `SaveFileManager.delete_save_file()` 先删文件，`db.delete + db.commit` 后做。commit 失败留 ghost row 指向不存在文件。
- **修复**：调换顺序 — `db.delete + db.commit` 先做，文件后 unlink；commit 失败抛异常，文件保留（孤儿 vs ghost row 选孤儿）。
- **测试**：mock db.commit 抛异常，断言文件仍在。

---

### TODO-S7 ✅ — `MAX_FILE_SIZE_BYTES = 10 MB` 是死代码 🟡 **P2** — 决定：删掉常量，不设上限

- **位置**：`save_file_manager.py:29`
- **问题**：常量定义了但 `write_save_file` 不用。理论上长 chat（几千轮 + 完整 emotion_analysis）+ 50 个 fact + chat history 累加可能超过 10MB。没人挡。
- **修复**：在 `write_save_file` 写盘前 `len(content) > MAX_FILE_SIZE_BYTES` → raise / 截断 chat_history。具体策略需要决定（见 UNCERTAIN-1）。

---

### TODO-S8 🔵 — `import_checkpoint` 不限 payload 大小 🟡 **P2** — deferred: S7 删上限后此项不再关联

- **位置**：`save.py:642-700`
- **问题**：FastAPI 默认 body 大小是 mostly 由前置 reverse proxy 限。Pydantic 接收任意大 JSON 进内存。session_snapshot.messages 长度无限。
- **修复**：在 path 上加 `Body(..., max_length=...)` 或 endpoint 内手动校验 `len(json.dumps(payload.session_snapshot))` < limit。配合 S7 一起做。

---

### TODO-S9 ✅ — `_get_checkpoint_state` file 缺失时沉默 fallback 到 DB state 🟡 **P2**

- **位置**：`save.py:188-194`
- **问题**：file_path 不为空但文件不存在（被外部清理 / 数据库与文件不同步）→ 沉默 fallback 到 `checkpoint.state`。state 在 v2.0 流程下只是部分字段（create 时写的少量），用户拿到不完整存档却不知道。
- **修复**：file_path 不为空但 file 缺失 → 至少 logger.warning 标错状态，UI 可考虑加"存档损坏"提示。短期：raise 404 + 明确文案让前端处理。
- **关联**：S2 修好后这条会更清晰（read_save_file 失败有更明确语义）。

---

### TODO-S10 🔵 — checkpoint.state JSON 字段双写问题 🟡 **P2** — 决定：UNCERTAIN-2 → A（保留做缓存索引）

- **位置**：`save.py:322-336` (create) + `save.py:191` (read fallback)
- **问题**：v2.0 流程下 file 是 source of truth，但 create 时还往 `checkpoint.state` 写一个简化版（只含 relationship/course_id/sage_character_id/traveler_character_id）。这导致：
  - state 和 file 可能不同步（file 含完整 chat_history，state 只有 4 个字段）
  - `_build_checkpoint_response` (line 197) 列表视图直接读 state，不走 file（性能考虑）→ 列表显示和详情不同步风险
  - 数据库占空间但不一定准
- **修复方向**（UNCERTAIN-2）：
  - **A**：保留 state 仅用作 list 视图轻量索引（明确文档化），create 时只写必要字段，restore 永远走 file
  - **B**：彻底删 state 字段（迁移），所有读都走 file
  - **C**：state 改成 cached 视图，写文件后回填 state 关键字段，加 ETag/version 标识
- **测试**：取决于决策。

---

### TODO-S11 ✅ — concept/lesson topic_type 在 progress_snapshot 不区分 🟢 **P3** — 随 S4 一起修好

- **位置**：`save.py:172-175` （已被 S4 包含）
- **状态**：S4 修好后顺手解决；单列出来防遗忘。

---

### TODO-S12 ✅ — `delete_checkpoint` 缺 status_code=204 🟢 **P3**

- **位置**：`save.py:405`
- **问题**：跟教材 X14 一样 — 返回 `{"message": ...}` 但没 response_model，OpenAPI 不准。
- **修复**：`@router.delete(..., status_code=204)` 无 body。

---

### TODO-S13 ⏳ — 测试用 `patch.object(SaveFileManager, "__module__")` 怪 patching 🟢 **P3**

- **位置**：`tests/test_save_file_manager.py:17-23`
- **问题**：patch `__module__` 是反模式（Python 类的 `__module__` 是字符串，patch 它跟 SAVE_DIR 没关系；唯一作用是让 `with patch.object(...)` 提供 `enter/exit` 让后面的赋值生效）。可改为直接 `monkeypatch.setattr(sfm, "SAVE_DIR", tmp_path / "saves")`。
- **影响**：测试本身能跑过，但模式不该被复制到新测试。

---

### TODO-S14 ⏳ — `_build_full_save_data` LearnerProfile 用 `first()` 而非 `one_or_none()` 🟢 **P3**

- **位置**：`save.py:138-141`
- **问题**：`(user_id, world_id)` 应该 unique（schema 没标 unique，但语义上唯一）。`order_by(id.desc()).first()` 隐藏了"如果有多条会拿最新一条"的语义模糊。
- **修复**：改 `one_or_none()`，并在 LearnerProfile 模型上加 UNIQUE(user_id, world_id) constraint（需迁移）。
- **影响**：低 — 但暴露了 schema 与代码假设不一致。

---

### TODO-S15 ✅ — 测试覆盖 🟡 **P2** — 已补 6 个新测试覆盖 S1/S2/S5

---

## 3. 新发现（执行过程中追加）

（暂无）

---

## 4. UNCERTAIN — 已全部敲定 ✅

### UNCERTAIN-1 ✅ — 删掉 MAX_FILE_SIZE_BYTES，不设上限

**决定**：常量已删除，不设任何文件大小上限。实际场景下不会超过 10MB（每个会话最多几百条消息）。

### UNCERTAIN-2 ✅ — 方案 A：保留 state 做缓存索引，file 是真相

**决定**：`checkpoint.state` 保留作为 list 视图的轻量缓存索引（只含 relationship/course_id/sage_character_id 等 4 个字段），file 是 source of truth。

### UNCERTAIN-3 ✅ — 直接改结构，不管旧格式

**决定**：`progress_snapshot` 直接改为 `{"concepts": [...], "lessons": [...]}` 新结构，不做版本兼容。restore 流程尚未实现，无需担心旧存档。

---

## 5. 已知 Acceptable / 不修

| ID | 问题 | 为什么不修 |
|---|---|---|
| `branch_from_checkpoint` 中无 partial-commit 风险 | SQLAlchemy commit 是 atomic | OK |
| `Checkpoint.thumbnail_path` 不在 SAVE_DIR 体系中（生产是 character avatar 路径）| 设计如此 | 不动 |

---

## 6. 工作流约定

1. UNCERTAIN-1~3 全部敲定后才进入实施
2. 每项执行 → TaskUpdate 标 in_progress → 改完跑相关测试 → 文档标 ✅ + commit hash
3. P0 + P1 必须有真 DB / 真 fastapi TestClient 测试
4. S4 涉及存档 schema bump，需要兼容性思考

## 7. 离开本片的判定

- §2 全部 P0 + P1 ✅ 或显式 deferred
- §4 UNCERTAIN 全部敲定 + 实施
- §3 全部消化
- 全套测试 pass（`cd backend && pytest`）
- 确认存档子系统不再有阻塞性安全/数据问题
