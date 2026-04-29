# 教材子系统深度 Review — 工作清单

> Branch: `feat/v1.0.3`
> Scope: Phase 3 commit `cefd4da` 的教材上传 + AI 课程生成
> Files in scope:
> - `backend/api/routes/textbook.py` (449 lines — cefd4da 里最大的单文件)
> - `backend/services/course_generator.py` (231 lines — 已在 teaching review 触及 T4，本片接着挖)
> - `backend/alembic/versions/2026_04_25_add_textbooks_table.py` (40)
> - `backend/main.py:88-91` (static 挂载点 — 关键)
> - `backend/tests/test_textbook_course_gen.py` (273)
> - 数据模型：`Textbook` (models.py:463+)
> Last updated: 2026-04-29

---

## ☑️ UNCERTAIN 拍板汇总（2026-04-29）

| ID | 决议 | 实施方向 |
|---|---|---|
| UNCERTAIN-1 (X2 鉴权) | **A** | 教材移出 `/static` → `backend/uploads/textbooks/`；新增 `GET /api/textbooks/{id}/file` + ownership 校验；前端同步改 URL |
| UNCERTAIN-2 (X11 重生成) | **拒绝** | 已有 `generated_lessons` 时 `POST /generate` 返回 409 / 明确错误；前端要走"清空 + 重生成"流程 |
| UNCERTAIN-3 (X8 EPUB) | **A2** | 移除 zipfile + regex；改用 `ebooklib` + `BeautifulSoup`；新依赖加入 requirements |
| UNCERTAIN-4 (X12 截断) | **B 本片 + C 立项** | 本片：章节边界截断（中文/英文/markdown 模式）；C 单独立项 `docs/milestones/textbook-chunked-llm-pipeline.md` |
| UNCERTAIN-5 (X9 错误) | **B** | 新增 `TextExtractionError`；调用方 try/except 设 status="error" + error_message |

同前几片 review，本文档是工作记录。**Claude 上下文窗口有限，本文档是唯一可信的进度来源**。每完成一项就更新状态；发现新问题就 append 到 §3。

---

## 1. 已修复（已 commit）

| ID | 修复 | 备注 |
|---|---|---|
| **X1** | `_safe_upload_filename` 用 `Path.name` 剥路径 + 替换 `\` `\0`；写文件后 resolve 校验 still in upload_root | 双重防御：name 剥分隔符 + resolve 校验 |
| **X2** | 教材搬出 `static`（→ `settings.upload_dir/textbooks`），新增 `GET /api/textbooks/{id}/file` + ownership 校验 | 前端 course.ts 无 download URL，无需改 |
| **X3** | `secrets.token_hex(8)` 替代 `int(time.time())` 前缀 | 同名同秒上传不再覆盖 |
| **X4** | INSERT/commit 失败 `unlink(missing_ok=True)` 兜底 | 不留孤儿文件 |
| **X5** | `delete_textbook` 改为 DELETE → commit → unlink；commit 失败不会留 ghost row | 顺手 X14 一并改 204 |
| **X6** | 新 `_read_with_limit` 1 MiB chunked 读取，超阈值立即抛 413 | 不再先 OOM 再校验 |
| **X7** | 提取走 `anyio.to_thread.run_sync` | event loop 不被 PDF / EPUB 解析阻塞 |
| **X8** | EPUB 改用 `ebooklib + BeautifulSoup`（UNCERTAIN-3 A2），按 spine 顺序遍历 ITEM_DOCUMENT | zipfile + regex 整段删除 |
| **X9** | 新 `class TextExtractionError`；`_extract_text` raise；upload 端 try/except 设 status='error' + error_message | 不再把 sentinel 当文本入库 |
| **X10** | textbook status 与 course.meta 单次 commit | 不再有 partial-write 不一致 |
| **X11** | `course.meta.generated_lessons` 已存在时 `POST /generate` 返回 409（UNCERTAIN-2 拒绝） | 前端要走"清空+重生成" |
| **X12** | `_truncate_at_chapter_boundary`：≥2 章节标题时按最后边界截断；正则覆盖中/英/markdown | C 方案立项 `docs/milestones/textbook-chunked-llm-pipeline.md` |
| **X13** | 新迁移 `2026_04_29_textbooks_indexes.py`：加 `ix_textbooks_course_id` + `ix_textbooks_user_id` | down_revision = 2026_04_27_fsrs_per_user |
| **X14** | `delete_textbook` `status_code=204` 无 body | OpenAPI 与实际一致 |
| **X15** | `_extract_pdf` 一次 fitz.open 返回 `(text, page_count)` | 不再开两次 |
| **X16** | `settings.upload_dir`（默认 `./uploads`），路径计算从 settings 读 | 与 X2 同 PR |
| **X17** | 新增测试覆盖：path 穿越、token_hex 不冲突、PDF/EPUB 错误、章节截断、TestClient 上传/下载/owner 隔离/regenerate 拒绝 | 305 passed (+17) |
| **顺手** | `TextbookResponse.created_at` 类型从 `str` 改 `datetime`（pydantic ResponseValidationError 修） | 旧类型生产即崩 |

**Commits**：见底部 §7。

---

## 2. 待修复 — 初轮扫描发现

### 严重等级图例
- 🔴 P0：安全漏洞 / 数据丢失 / 必炸
- 🟠 P1：高风险 / 部分写入 / DoS
- 🟡 P2：bug 但有兜底 / 性能问题
- 🟢 P3：代码质量 / 测试缺失

---

### TODO-X1 ⏳ — `safe_name` 不去除 filename 路径成分 → 路径穿越 🔴 **P0**

- **位置**：`textbook.py:178-182`
  ```python
  safe_name = f"{int(time.time())}_{filename}"
  file_path = static_dir / safe_name
  file_path.write_bytes(content)
  ```
- **问题**：`filename` 来自 `file.filename` (line 161)。Path 穿越触发条件：上传一个 filename 为 `../../../tmp/pwn.pdf` 的请求，扩展名是 `.pdf` 通过 ALLOWED_EXTENSIONS 检查。`safe_name = "1714234567_../../../tmp/pwn.pdf"`。
- **`/` 在 filename 中**：`Path(static_dir / safe_name)` 会解释成路径分隔。攻击者可写到 backend/static/textbooks/{course_id} 之外。
- **修复**：`filename = Path(filename).name` 在写文件前剥离所有路径成分；同时验证 normalized 后的 filename 不含 `\\` / `\0` 等。
- **测试**：注入 `filename="../../etc/passwd.pdf"`，断言写入路径在 static_dir 之内。

---

### TODO-X2 ⏳ — Static 挂载使所有教材文件无鉴权可下 🔴 **P0**

- **位置**：`main.py:91` + `textbook.py:175`
- **问题**：
  - `app.mount("/static", StaticFiles(...))` 把整个 static 目录公开为 URL，无任何 auth
  - 教材写到 `static/textbooks/{course_id}/{timestamp}_{filename}`
  - URL 可预测（timestamp = upload time，filename 用户已知；course_id 可枚举）
  - 任意用户或匿名访问者能拿到他人上传的教材内容（PDF/EPUB 通常含个人作业、付费教材等敏感内容）
- **修复方向**（需用户拍板，见 §UNCERTAIN-1）：
  - **方案 A**：教材落到 static 目录之外（如 `backend/uploads/textbooks/{course_id}/...`），新增 `GET /api/textbooks/{id}/file` 端点，校验 ownership 后 `FileResponse` 流式返回。
  - **方案 B**：保持目录布局，在挂载层加 auth middleware，但 StaticFiles 不易拦截。
  - 倾向 A：彻底脱离 public 目录是更彻底的修复。
- **测试**：直接访问 `/static/textbooks/{course_id}/{file}` 应该 404 / 401，授权 endpoint 才能下。

---

### TODO-X3 ⏳ — `time.time()` 命名冲突（同秒上传相同 filename） 🟠 **P1**

- **位置**：`textbook.py:179-181`
- **问题**：`int(time.time())` 是秒级精度。同一课程下同一秒上传两份同名文件 → 后者覆盖前者，第一份的 DB 行 file_path 指向被覆盖的内容。
- **修复**：用 `secrets.token_hex(8)` 或 `uuid.uuid4().hex[:16]` 代替 timestamp 前缀；或加上随机后缀 `f"{int(time.time())}_{secrets.token_hex(4)}_{filename}"`。
- **影响**：单用户低，多用户必中。

---

### TODO-X4 ⏳ — 文件写盘后 DB INSERT 失败 → 孤儿文件 🟠 **P1**

- **位置**：`textbook.py:182, 198-211`
- **问题**：顺序 = 写文件 → INSERT → commit。commit 失败（FK 错、磁盘满、连接断）后文件留在磁盘，DB 没记录，下次再上传同名文件命名冲突 / 占空间无人管。
- **修复**：try/except 包住 INSERT+commit，失败时 `file_path.unlink(missing_ok=True)` 兜底。
- **测试**：mock db.commit 抛异常，断言写盘文件被清理。

---

### TODO-X5 ⏳ — `delete_textbook` 文件先删、DB 后删 → DB 失败时 file_path 指向幽灵 🟠 **P1**

- **位置**：`textbook.py:255-263`
- **问题**：顺序 = unlink → DELETE → commit。如果 commit 失败（rare 但可能），文件已删但 DB 行还在，前端列出后下载 404。
- **修复**：调换顺序 — DELETE → commit → unlink。commit 后即便 unlink 失败也只是文件残留（X4 反向），不至于不一致。
- **测试**：mock db.commit 抛异常前 unlink 是否被推迟。

---

### TODO-X6 ⏳ — 文件全量读入内存后才校验大小 🟡 **P1 (DoS)**

- **位置**：`textbook.py:170-172`
  ```python
  content = await file.read()
  if len(content) > MAX_FILE_SIZE:
      raise HTTPException(...)
  ```
- **问题**：用户上传 1GB 文件，服务器先把 1GB 读进 RAM，再说"超过 50MB"。多个并发上传 = OOM。
- **修复**：用 chunked read + 累计长度，超 MAX_FILE_SIZE 立即中断；或先读 `file.headers.get("content-length")` 拒绝（可被欺骗，仍需 chunked guard）。
- **影响**：单用户、本地部署影响小；公网部署立即上 P0。

---

### TODO-X7 ⏳ — `_extract_text_from_bytes` 在 async handler 里同步执行 CPU-bound 抽取 🟡 **P1**

- **位置**：`textbook.py:185, 191`
- **问题**：PyMuPDF (`fitz.open` + 逐页 `get_text()`) 和 EPUB zip+regex 提取都是 CPU-bound、数十 MB 教材轻松数秒。`async def upload_textbook` 里直接调，会阻塞整个 event loop。其它请求挂等。
- **修复**：`from anyio import to_thread; text = await to_thread.run_sync(_extract_text_from_bytes, content, filename)`。
- **测试**：可以做个 sleep mock 验证不阻塞，但比较折腾，先做修复。

---

### TODO-X8 ⏳ — EPUB 提取无解压大小上限 → zip bomb 🟠 **P1**

- **位置**：`textbook.py:121-138`
- **问题**：`zipfile.ZipFile(io.BytesIO(content))` 不限制解压后总大小。一个 50MB 的 zip bomb 可解出 GB 级文本，全 decode + regex 一遍。RAM/CPU 双爆。
- **修复**：累计 `info.file_size`（解压后）超阈值（如 200MB）即中断；同时单文件 file_size 超阈值跳过。
- **影响**：依赖 EPUB 接受度。如果项目实际用 EPUB 频率不高，可考虑暂时关掉支持（见 UNCERTAIN-3）。

---

### TODO-X9 ⏳ — `extracted_text` 含错误 sentinel 仍标 status="extracted" 🟠 **P1**

- **位置**：`textbook.py:184-208` + `_extract_text_from_bytes` 的 PDF/EPUB 错误分支
- **问题**：`_extract_text_from_bytes` 在解析失败时返回字符串如 `"[PDF 文本提取失败: ...]"`、`"[PDF 文件需要安装 PyMuPDF 库才能提取文本]"`、`"[不支持的文件类型: .docx]"`。**当作正常文本入库**，status="extracted"。后续 `generate_course_from_textbooks` 会把这串错误信息当教材内容喂给 LLM。
- **修复**：`_extract_text_from_bytes` 改返回 `(ok: bool, text: str)` 或 raise；upload 端根据结果决定 status="extracted" / status="error" + error_message。
- **测试**：上传一个无效 PDF，断言 status="error"。

---

### TODO-X10 ⏳ — 课程生成 partial-write：textbook 标 processed 后 course.meta 写入失败时不一致 🟠 **P1**

- **位置**：`textbook.py:336-349`
  ```python
  for t in textbooks:
      t.status = "processed"
  db.commit()              # ← commit 1
  course.meta = ...
  db.commit()              # ← commit 2
  ```
- **问题**：commit 1 成功、commit 2 失败 → 教材被永久标 processed（list_textbooks 只返回 status="extracted"），但课程没生成。用户必须删教材重传。
- **修复**：合并成一次 commit；`flag_modified` 后再统一 commit。
- **测试**：mock 第二次 commit 抛异常，断言教材 status 回滚到 extracted。

---

### TODO-X11 ⏳ — `course.meta` 重新生成时无声覆盖 🟠 **P1**

- **位置**：`textbook.py:342-348`
- **问题**：第二次调用 `generate_course_from_textbooks` 直接覆盖 `generated_overview` / `generated_lessons` / `concept_map`。如果用户已基于旧 lessons 学习了一段（`current_lesson_index`、`completed_lessons` 在 meta 里！），重生成会扰乱进度状态。
- **不确定的修复策略**（见 UNCERTAIN-2）：
  - 拒绝覆盖（前端必须传 `force=true`）
  - 备份旧 meta 到 `course.meta["history"]`
  - 保留 `current_lesson_index` / `completed_lessons`，只覆盖 lessons / overview / concept_map
- **测试**：取决于决策。

---

### TODO-X12 ⏳ — 教材合并 → LLM 上下文超限的截断策略偏差 🟡 **P2**

- **位置**：`textbook.py:298-306`
- **问题**：80000 字符上限，超出时取头 + 尾，中间省略。教材通常按"基础→进阶"线性组织，砍中间相当于把进阶内容直接接到基础后面，LLM 看到的内容缺一段，生成的章节图错位。
- **修复方向**（UNCERTAIN-4）：
  - 简单：改成只取头部
  - 适当：按章节标题切分，跳过靠后章节而非中间
  - 复杂：map-reduce 多次 LLM 调用合并
- **影响**：超 80000 字符的教材实际占比未知。

---

### TODO-X13 ⏳ — `textbooks.course_id` / `textbooks.user_id` 缺索引 🟡 **P2**

- **位置**：`alembic/versions/2026_04_25_add_textbooks_table.py:35`
- **问题**：迁移只建了 `ix_textbooks_id`。所有 list / generate / delete 查询都按 `course_id` + `user_id` 过滤，Postgres 不会自动给 FK 建索引。教材表小时影响不大；多用户 + 累积上传后会全表扫。
- **修复**：新迁移 `ALTER TABLE` 加 `ix_textbooks_course_id`、`ix_textbooks_user_id`。
- **影响**：性能问题，prod 体感后才会暴露。

---

### TODO-X14 ⏳ — `delete_textbook` 没有 response_model 🟢 **P3**

- **位置**：`textbook.py:236-264`
- **问题**：返回 `{"message": "..."}` 但路由没声明 response_model，OpenAPI 文档不准。
- **修复**：声明 `response_model=` 或改为 `status_code=204` + 无返回。

---

### TODO-X15 ⏳ — PDF 打开两次（提取文本 + 计算页数） 🟢 **P3**

- **位置**：`textbook.py:185 + 191`
- **问题**：`fitz.open` 被调两次，第二次只为了 `len(doc)`。第一次完全可以顺手记 page_count。
- **修复**：`_extract_text_from_bytes` 改返回 `(text, page_count)` 或单独函数 `_extract_pdf(content) -> (text, page_count)`。

---

### TODO-X16 ⏳ — 静态目录路径硬编码（`Path(__file__).resolve().parents[2]`） 🟢 **P3**

- **位置**：`textbook.py:175`
- **问题**：依赖文件位置层级，移动或重组目录结构后会指向错地方。和 `main.py` 用的 `os.path.dirname(__file__)` 也不一致。
- **修复**：从 `core/config.py` 读 `settings.upload_dir`（如果不存在则加入）。配合 X2 一起做。

---

### TODO-X17 ⏳ — 测试缺关键安全/恢复路径覆盖 🟡 **P2**

需要补的测试（按 fix 项打散到对应 TODO 里，统一记在这）：
- 路径穿越 (X1)：filename 含 `..` 仍写入 static_dir 内
- 鉴权 (X2)：未登录访问教材文件
- 命名冲突 (X3)：并发上传同名同 course
- DB INSERT 失败回滚（X4）
- 错误 sentinel 不入库（X9）
- generate course 部分失败回滚（X10）
- 跨用户 IDOR：用户 A 调 `/courses/{B's course_id}/textbooks` → 已被 `_get_course_with_auth` 覆盖，但应有正向测试
- delete_textbook 跨用户：textbook_id 属于他人时返回 404（已有 user_id filter 保护，需测试覆盖确认）

---

## 3. 新发现（执行过程中追加）

> 实施时把发现写到这里，避免改了 §2 项时丢线索。

（暂无）

---

## 4. UNCERTAIN — 需要拍板再做

### UNCERTAIN-1 ⏳ — X2 鉴权方案 A vs B

**背景**：教材文件经 `/static` 挂载无鉴权暴露。

| 方案 | 描述 | 取舍 |
|---|---|---|
| **A** | 文件改存 `backend/uploads/textbooks/{course_id}/...`（脱离 static），新增 `GET /api/textbooks/{id}/file` 走 FileResponse + ownership 检查 | 完全脱 public；多一个 endpoint；前端改 URL |
| **B** | 保持当前路径，加 mount 拦截器（自定义 StaticFiles 子类做 auth） | 改动小；逻辑混在静态层不直观；StaticFiles 拦截不优雅 |

**倾向 A**。需要确认 1) 前端能改 URL；2) 是否同时迁移现存教材文件。
**owner**：A,顺手把前端改了，如果改前端的过程中出现问题在此处说明。目前没有上传任何教材文件。
---

### UNCERTAIN-2 ⏳ — X11 重新生成课程的 meta 处理策略

**背景**：course.meta 既存"生成数据"（lessons/overview/concept_map）也存"教学进度"（current_lesson_index / completed_lessons）。重新生成时如何对待？

| 策略 | 描述 |
|---|---|
| **拒绝** | 已有 generated_lessons → 拒绝再生成，前端要走"清空+重生成" |
| **备份** | 把旧 meta 存到 `course.meta["history"]`，便于撤销 |
| **保留进度** | 仅覆盖生成相关字段，进度字段不动（可能与新 lessons 不匹配） |

**倾向"保留进度 + 警告"**：不强制阻断，但若 `current_lesson_index >= len(new_lessons)` 自动 clamp 到 0 并日志警告。
**owner**：我想知道这个重新生成课程是什么场景？

**Claude 回答 — 重生成场景**（来自代码现状 + 合理推断）：
当前同一个端点 `POST /api/courses/{course_id}/generate` 既负责"首次生成"也负责"重生成"，**前端没有任何拦截**。可能的触发场景：
1. **无前置内容**（首次）：course.meta 还没有 generated_lessons → 没风险
**owner**：删除该场景
2. **新加教材后**：用户上传新文件 → 重新生成想合并新内容
**owner**：删除该场景
3. **不满意 LLM 输出**：lessons 划分不合理、太少/太多、概念粒度不对，想换 prompt 或换 LLM provider 重试
4. **修改 course 字段**：course.description / target_level / target_days / custom_instructions 改了想重新生成
5. **教材更新版本**：用户用新版教材替换旧的（先 delete + upload，再 generate）
**owner**：删除改场景


**风险点**：场景 3-5 时，如果用户已经基于旧 lessons 学了几节，meta 里的 `current_lesson_index=3, completed_lessons=[0,1,2]` 会被以下三种策略影响：
- 拒绝 → 用户被阻塞，必须先清空进度（但"清空进度"无对应端点，需另开发）
- 备份 → meta["history"] 保留旧 lessons，但 current_lesson_index 仍按新 lessons 解释；体感等同"保留进度+警告"加可恢复
- 保留进度 → current_lesson_index 在新 lessons 上的语义飘移；clamp 兜底安全但用户可能困惑

**等你拍板**：选拒绝 / 备份 / 保留进度 / 其它（如带 force 参数 + 明确警告）
**owner**：只进行由于不满意llm输出和不满意导致的重生成，即：产生数据后该课程无法重新生成。
---

### UNCERTAIN-3 ⏳ — X8 EPUB 是否值得保留

**背景**：EPUB 解析靠 `zipfile + 正则去标签`，比 PyMuPDF 等成熟方案脆弱（zip bomb 是真实威胁）。

- 如果 prod 实际 EPUB 占比 < 5%，**移除 .epub 支持** + 在 ALLOWED_EXTENSIONS 里删掉是最干净的修复
- 如果占比可观，按 X8 加解压上限

需要用户判断。
**owner**：我认为应当采用成熟方案。

**Claude 追问**："采用成熟方案" 的具体方向：

| 选项 | 描述 | 取舍 |
|---|---|---|
| **A1** | 用 PyMuPDF (fitz) 解 EPUB（fitz 原生支持 .epub / .mobi / .fb2 / .xps / .cbz） | 同一库一套代码；现有 PyMuPDF 依赖已在；最干净 |
| **A2** | 用 ebooklib + BeautifulSoup 专门解 EPUB | 更"教科书"做法；需新依赖；HTML 解析更准 |
| **B** | 直接移除 .epub 支持 | 最干净但损失功能 |

**Claude 倾向 A1**：fitz 已经在依赖里了，能复用。如果你说的"成熟方案"是指 A1 我直接做；如果是 A2 也可以。请确认是 A1 / A2。
**owner**：A2
---

### UNCERTAIN-4 ⏳ — X12 教材截断策略

**背景**：教材超 80000 字符的截断策略目前是"头 + 尾"，但教材通常线性递进。

- 用户预期主要是哪类教材（PDF 教科书 / md 笔记 / 学术论文）？
- 多大占比会超 80000 字符？

如果主要是中等长度笔记 → 不需要复杂方案，可直接简化为"取头部"。

**owner**：预期是pdf教科书，也有可能是学术论文，但是我认为如果将一切输入都按照章节切分后再进行格式转换会更好

**Claude 追问** — "按章节切分后再格式转换" 我理解可能是这两种之一：

| 选项 | 描述 | 实现复杂度 |
|---|---|---|
| **A** | **提取阶段就分章节**：`_extract_text_from_bytes` 改为返回 `list[Chapter]`（每个含 title + body）。Textbook 表新加 `chapters JSON` 列存结构化结果。生成阶段 LLM 看到的是结构化 chapter list，不再是大 string。后续可按 chapter 选择性送（如"前 N 章"或"用户指定章节"） | 高 — 改 schema、迁移、_extract_*、generate 整链路 |
| **B** | **生成阶段截断时按章节边界**：保留 `extracted_text` 现状（一个大 string），但截断逻辑改成"找到 80000 字符前的最后一个章节标题（如 `第N章` / `Chapter N` / `## ` 等模式），从那里截断"。LLM 看到的是完整的前 N 章，丢弃后部 | 中 — 仅改 truncate 逻辑，加章节模式正则 |

**辅助问题**：
- 如果选 A，是否同步把 chapter 信息暴露给前端，让用户选择"生成第 X 章 - 第 Y 章"？还是后台自动拼装？
- 如果选 B，章节标题正则要中文 + 英文 + markdown 三套。你预期的教材主要语言是什么？

**Claude 倾向 B**：A 改动面太大，对一份 cefd4da review 来说超出 scope；B 收益足够（避免砍中间）+ 改动局限。**如果你确定是 A，建议把 A 拆成单独 milestone（`chapter-aware-textbook-pipeline.md`），不在本片做完。**
**owner**：我没看懂B的意思

**Claude 重新解释 B（用具体例子）**：

假设教材 200000 字符，限额 80000 字符。

**当前代码**（textbook.py:302-306）：
```python
half = MAX_CHARS // 2  # = 40000
all_text = all_text[:40000] + "[省略]" + all_text[-40000:]
```
即：取 0~40000 + 160000~200000，**砍掉 40000~160000 中间一大段**。如果第 5 章在 50000 字符位置、第 10 章在 100000 字符位置，LLM 会看到"第 1-4 章 + 第 11+ 章"，第 5-10 章丢失，章节顺序断裂。

**B 方案**（按章节边界截断）：
```python
# 在 0~80000 范围内找最后一个章节标题位置（用正则）
# 比如 "第六章 微积分" 出现在第 75000 字符处
# → 取 all_text[:75000]，丢弃 75000 之后所有内容
# LLM 看到完整的前 5 章，第 6 章及以后被丢弃
```

正则匹配的章节标题模式：
- 中文：`第一章` / `第1章` / `第 1 节`
- 英文：`Chapter 1` / `Chapter One`
- markdown：行首 `# ` 或 `## `

**B 的本质**：与"只取头部"差别在 — 不会切到一句话或一段话的中间，最后一个完整的章节是边界。**LLM 看到的是教材的完整前若干章**。

**取舍对比**：
| 方案 | 当前（头+尾） | 只取头部 | B（章节边界） | A（提取就分章节） |
|---|---|---|---|---|
| LLM 内容连续性 | 中间断 ❌ | 末尾断 ⚠️（句中） | 末尾自然断 ✅ | 完整结构 ✅✅ |
| 实现成本 | — | 极低 | 低（加正则 + 边界查找） | 高（改 schema） |
| 是否本片做 | 是当前现状 | 可 | **可** | 建议另立 milestone |

**问题**：你看完后倾向 B 还是 A？或者其它（如改成"只取头部"）？
**owner**：能不能建立一个流水线，先按照限额字符对原pdf切分，再将切分好的多份pdf进行转换，然后再将转换好的各部分组装起来？

**Claude 回应**：你提的是 **chunked pipeline / map-reduce**。技术上可行，但需要先澄清一点：

**先澄清**：原 PDF 二进制 **不能** 按字节切（PDF 有 cross-ref 表、字体表，切完全坏）。所以可行流程是：
1. 先用 fitz 提取出**整本**纯文本
2. 把纯文本按字符限额切成 N 段（这一步不是切 PDF 二进制）
3. 每段单独调 LLM 生成局部 outline（lessons + concept_map 片段）
4. 最后合并所有局部 outline

**实现路径与成本评估**：

| 维度 | 现状（头+尾） | B（章节边界截断）| **C：你提的 map-reduce 流水线** |
|---|---|---|---|
| LLM 看到的内容 | 缺中间 | 缺末尾（章节边界） | **全部** |
| LLM 调用次数 | 1 | 1 | N+1（N 段 + 1 次合并；或 N 段直接 concat 不合并）|
| API 费用 | 1× | 1× | **~3-5×**（200000 字符 → 3-4 段 + 1 合并） |
| 延迟 | ~5-10s | ~5-10s | ~30-60s（串行）/ ~10-15s（并行）|
| 实现复杂度 | — | 低（加正则） | **高** — 段切分 + 局部 prompt + 合并算法（dedupe lessons by title/concept、deep-merge concept_map nodes/edges）+ 错误处理（其中一段 LLM 失败怎么办）+ 测试覆盖 |
| 范围 | 修 review bug | 修 review bug | **新 feature** |

**Claude 强烈建议拆成两件事**：

1. **本片（cefd4da review）只修 bug**：用 **B（章节边界截断）** — 正则找章节边界，从最后完整章节处截断。改动局限、避免砍中间，把 X12 P2 关闭。

2. **新立项 milestone**：`docs/v1.0.x/textbook-chunked-llm-pipeline.md`，专门设计 map-reduce 流水线。包括：
   - 切分策略（按字符 vs 按章节 vs 按页）
   - 局部 prompt（要不要让每段都生成 overview？还是只生成 lessons？）
   - 合并算法（如何 dedup lessons / concept nodes）
   - 失败处理（某段失败 = 整体失败 vs 跳过）
   - 测试 + 成本评估
   - 是否同步 UI 上加 "正在处理 5 段教材..." 进度条（涉及前端）
   - 是否新建一个 `pipeline_strategy: 'simple' | 'chunked'` 配置开关，让用户选

**我倾向**：本片选 B 收尾；C 单独立项 v1.0.4 或 v1.1 做。

你拍板：
- **(a)** 本片选 B + 立项 C（推荐）

---

### UNCERTAIN-5 ⏳ — X9 错误 sentinel 检测要不要直接 raise

**背景**：`_extract_text_from_bytes` 当前永远返回 str。修复方向：

- **A** 改返回 `(ok, text)` tuple，调用方分支
- **B** 失败时 raise `ExtractionError`，调用方 try/except 设 status="error"

**倾向 B**：异常更显式。但 `_extract_text_from_bytes` 没现成的异常类，要新建一个 `class TextExtractionError(Exception)`。
**owner**：选B
---

## 5. 已知 Acceptable / 不修

| ID | 问题 | 为什么不修 |
|---|---|---|
| `Textbook.user_id` 与 course→world→user_id 链路冗余 | denormalization 加速查询，符合现有 schema 风格（Achievement 同样模式） | 设计选择 |
| `_parse_response` markdown 块去除粗糙（只看开头/结尾的 ``` ） | LLM JSON 输出场景下足够 | 对抗 LLM 输出畸形不是本系统职责 |
| course_generator T4（empty lessons raise）| 已在教学 review 修过 | 无需重做 |

---

## 6. 工作流约定

1. UNCERTAIN-1~5 全部敲定后才进入实施
2. 每项执行 → TaskUpdate 标 in_progress → 改完跑相关测试 → 文档标 ✅ + commit hash
3. P0 必须有真 DB / 真 fastapi TestClient 的回归测试，不靠 mock
4. 改 status sentinel / 路径相关的修复要记 migration 影响（生产数据迁移可能需 backfill）

## 7. 离开本片的判定

- §2 全部 P0 + P1 ✅ ✓
- §4 UNCERTAIN 全部敲定 + 实施 ✓（C 立项延后）
- §3 全部消化 ✓（暂无新发现）
- 全套测试 pass：**305 passed, 13 skipped**（基线 288 → +17 textbook 测试）
- 确认 cefd4da 的教材子系统不再有阻塞性安全/数据问题 ✓

---

## 完成态（2026-04-29）

| Section | 状态 |
|---|---|
| §1 已修复 | 17 项（X1-X17 全 ✅）+ 1 顺手（TextbookResponse.created_at 类型） |
| §2 待修复 | 0（全部 ✅） |
| §3 新发现 | 0 |
| §4 UNCERTAIN | 5 项全部敲定（C 立项 → `docs/milestones/textbook-chunked-llm-pipeline.md`） |
| §5 acceptable | 3 项 |

**教材子系统 review 关闭。**
