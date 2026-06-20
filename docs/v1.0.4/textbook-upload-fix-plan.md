# 教材上传功能

> 创建日期: 2026-05-11
> 状态: 待实施
> 目标: 统一教材上传、书架复用、课程关联、解析状态和删除生命周期
> 相关文档:
> - `docs/v1.0.3 Review/textbook-system-deep-review.md`
> - `docs/milestones/textbook-chunked-llm-pipeline.md`

## 1. 背景

教材上传功能两条入口:

1. 课程页直接上传教材到课程，上传时同步回填上传到书架。
2. 书架页先上传, 创建课程时再关联到课程。

这两个入口的目标是合理的: 教材应该可以先独立存在, 也应该可以被多门课程复用。但是当前实现里, “教材文件资产”和“课程-教材关联”没有被清晰建模, 导致上传成功、解析失败、课程关联、删除文件之间的语义不一致。

这份文档不是重新 review 旧的教材安全问题。旧文档已经覆盖过路径穿越、静态目录暴露、命名冲突、提取错误、LLM 截断等问题。本文只记录当前代码中影响后续修复的链路问题。

## 2. 当前关键文件

后端:

| 文件 | 当前职责 |
|---|---|
| `backend/api/routes/textbook.py` | 课程内教材上传、列表、删除、下载、基于教材生成课程 |
| `backend/api/routes/bookshelf.py` | 用户级书架上传、列表、删除、关联课程 |
| `backend/models/models.py` | `Textbook` 和 `TextbookLibrary` 两套表模型 |
| `backend/core/config.py` | `upload_dir` 配置, 默认 `./uploads` |

前端:

| 文件 | 当前职责 |
|---|---|
| `frontend/src/api/course.ts` | 课程教材上传、列表、删除、生成课程 |
| `frontend/src/api/bookshelf.ts` | 书架上传、列表、删除、关联课程 |
| `frontend/src/views/CoursePage.vue` | 课程页教材上传和生成课程入口 |
| `frontend/src/views/Bookshelf.vue` | 书架页教材上传和状态展示 |
| `frontend/src/components/CreateCourseModal.vue` | 创建课程时选择/上传教材并批量关联 |

## 3. 当前问题

### P0/P1: 书架教材和课程教材没有真实关联键

`TextbookLibrary` 表表示用户级教材库, `Textbook` 表表示课程内教材。但二者之间没有 `library_id` 或任何外键。书架列表、重复关联检查、批量关联都靠 `file_path` 匹配:

- `bookshelf.py` 列表用 `Textbook.file_path == item.file_path` 反查 `linked_course_ids`
- `link_textbook_to_course` 创建 `Textbook` 时复制 `lib_item.file_path`
- `batch_link_textbooks` 也复制 `lib_item.file_path`

代码注释里已经写到“在 Textbook 表上加 library_id 字段来追踪关联”, 但模型实际上没有这个字段。这说明设计意图和实现已经脱节。

风险:

1. `file_path` 成为隐式外键, 没有数据库约束。
2. 后续路径迁移、文件重命名、去重、备份恢复都会破坏关联。
3. 很难判断一份文件是否仍被课程引用。
4. 删除时无法正确区分“删除课程关联”和“删除真实文件”。

### P0/P1: 删除课程教材会误删书架共享文件

当书架教材关联到课程时, `Textbook.file_path` 指向 `TextbookLibrary.file_path` 同一份文件。

但是:

- `delete_textbook` 删除课程教材后会 `unlink(file_path)`
- `delete_from_bookshelf` 删除书架教材后也会 `unlink(file_path)`

这会造成两个方向的破坏:

1. 用户只想从某门课程移除教材, 结果把书架里的原始文件也删了。
2. 用户删除书架教材, 已关联课程里的 `Textbook` 行还可能保留, 但文件已经不存在。

目标语义应该是:

- 删除课程教材 = 删除“课程和教材的关联”, 不应默认删除共享文件。
- 删除书架教材 = 删除“用户级教材资产”, 必须处理已有课程引用, 不能留下悬空课程记录。

### P1: 解析失败被包装成上传成功

后端上传接口在解析失败时仍返回 200, 只是把记录写成:

```python
status = "error"
error_message = str(e)
extracted_text = None
```

这不是一定错误。保留上传文件和错误状态是可以接受的。但是前端没有统一表达这个状态:

- `CoursePage.vue` 上传后无条件显示“教材上传成功”。
- `CoursePage.vue` 教材列表只展示文件名和大小, 不展示 `status` / `error_message`。
- `Bookshelf.vue` 会展示 `status === 'error'`, 但上传 toast 仍先显示成功。
- `CreateCourseModal.vue` 上传后直接把返回 item 加入 `bookshelfItems` 和 `selectedBookIds`, 不检查 `status`。

结果是用户看到“上传成功”, 但后续生成课程时没有可用教材文本, 或创建课程流程进入 AI 生成后才失败。

### P1: 创建课程流程吞掉教材关联失败

`CreateCourseModal.vue` 中:

```ts
try {
  await bookshelfApi.batchLinkToCourse(course.id, selectedBookIds.value)
} catch (err) {
  console.error('Failed to link textbooks:', err)
  // Non-fatal, continue
}
genStatus.value = 2
```

这里把教材关联失败视为非致命, 继续调用 `generateCourse`是不对的。如果用户明确选择了教材, 关联失败应该阻断后续 AI 生成,。

### P1/P2: 上传进度和解析耗时语义不一致

前端 axios 全局 timeout 是 15 秒。教材上传接口在一个请求里做了三件事:

1. 接收文件。
2. 写入磁盘。
3. 执行 PDF/EPUB/TXT/OCR 解析。

`onUploadProgress` 只能表示网络上传进度, 不能表示服务端解析进度。对扫描 PDF/OCR 或较大 EPUB, 用户可能看到 100%, 然后长时间等待, 最后得到一个通用超时/失败。

应该拆成“上传文件”和“后台解析任务”两个阶段。

### P2: 三个前端入口支持的文件类型不一致

后端 `ALLOWED_EXTENSIONS` 支持:

```text
.pdf, .txt, .md, .markdown, .epub,
.png, .jpg, .jpeg, .webp, .gif, .tif, .tiff, .bmp
```

前端当前不一致:

| 入口 | 当前 accept |
|---|---|
| CoursePage | 支持 PDF/TXT/MD/EPUB/图片 |
| Bookshelf | 支持 PDF/TXT/MD/MARKDOWN/EPUB, 不支持图片 |
| CreateCourseModal | 支持 PDF/EPUB/TXT/MD, 不支持 MARKDOWN/图片 |

用户会遇到“这个页面可以传, 换个入口就不能传”的不一致体验。

### P2: 课程页重复选择同一文件可能不触发上传

`CoursePage.vue` 选择文件后没有清空 input value。浏览器通常不会对同一个文件重复触发 `change`。书架页和创建课程弹窗已经做了 reset, 课程页也应补齐。

### P2: 批量关联接口返回值不完整

`batch_link_textbooks` 创建新 `Textbook` 后, 在 `db.commit()` 前往 `results` 里写:

```python
{"textbook_id": None, "library_id": lib_id, "skipped": False}
```

当前前端没有使用返回的 `textbook_id`, 所以还没有暴露为用户问题。但接口契约不完整, 后续如果需要展示“已关联教材”或定位错误, 会缺少 ID。

## 4. 根因

当前代码把三个概念混在了一起:

1. 文件资产: 磁盘上的真实文件, 包括文件路径、大小、content type。
2. 解析结果: extracted_text、page_count、status、error_message。
3. 课程引用: 某门课程是否使用这份教材。

`TextbookLibrary` 像是文件资产和解析结果, `Textbook` 又同时像课程引用、文件资产和解析结果。二者没有真实外键, 删除时只能从 `file_path` 推断所有权, 于是生命周期必然混乱。

## 5. 建议目标模型

### 最小修复方案

保留现有表名, 增量修复:

1. 给 `Textbook` 增加 `library_id: int | None` 外键, 指向 `textbook_library.id`。
2. 给 `Textbook` 增加 `owns_file: bool` 或 `source_type` 字段, 区分:
   - `library` 关联: 文件归 `TextbookLibrary` 管。
   - `direct_upload` 直传: 文件归这条 `Textbook` 管。
3. 书架关联课程时必须写入 `library_id`。
4. `list_bookshelf` 用 `Textbook.library_id == item.id` 查关联课程, 不再用 `file_path`。
5. 删除课程教材时:
   - 如果 `library_id is not None`: 只删 `Textbook` 行, 不删文件。
   - 如果 `library_id is None and owns_file`: 可以删文件。
6. 删除书架教材时:
   - 如果仍有 `Textbook.library_id == item.id`, 默认返回 409, 要求先从课程移除。
   - 或显式提供“同时从所有课程解除关联”的端点, 不要静默删文件。

这是推荐的第一阶段, 变动小, 风险可控。

### 更干净的长期方案

重新命名概念:

- `TextbookLibrary` 或新表 `MaterialAsset`: 用户级教材资产, 包含文件和解析结果。
- `CourseTextbook` 或 `CourseMaterial`: 课程和教材资产的关联表。

课程内不再复制 `extracted_text`、`file_path`、`page_count`; 课程生成时通过关联读取教材资产的解析结果。这个方案更干净, 但迁移面更大, 不建议作为第一刀。

## 6. 修复顺序

### Step 1: 先止住文件生命周期风险

后端:

1. 新增 migration:
   - `textbooks.library_id` nullable FK -> `textbook_library.id`
   - `textbooks.owns_file` boolean, default true
2. 更新模型 `Textbook`。
3. 更新 `link_textbook_to_course` 和 `batch_link_textbooks`:
   - 设置 `library_id=lib_item.id`
   - 设置 `owns_file=False`
4. 更新 `list_bookshelf`:
   - 用 `Textbook.library_id == item.id`
5. 更新 `delete_textbook`:
   - 关联书架教材时只删课程关联, 不 unlink 文件。
6. 更新 `delete_from_bookshelf`:
   - 有课程引用时返回 409, detail 给出 linked_course_ids。

测试:

1. 书架上传 txt -> 关联课程 -> 删除课程教材 -> 书架文件仍存在。
2. 书架上传 txt -> 关联课程 -> 删除书架教材 -> 返回 409。
3. `list_bookshelf` 返回正确 `linked_course_ids`。
4. 同一书架教材可以关联多门课程。
5. 课程直传教材删除后仍会删除自己的文件。

### Step 2: 修正上传成功和解析失败的前端语义

前端:

1. `CoursePage.vue` 教材列表展示:
   - `status`
   - `error_message`
   - `page_count`
2. `CoursePage.vue` 上传后判断返回 item:
   - `status === 'extracted'`: 显示上传并解析成功。
   - `status === 'error'`: 显示上传成功但解析失败, 并展示原因。
3. `CoursePage.vue` 生成按钮只在存在可用教材时启用:
   - 至少一条 `status === 'extracted' && extracted_text != null`。
4. `Bookshelf.vue` 上传成功 toast 同样区分解析成功/失败。
5. `CreateCourseModal.vue`:
   - 只允许选择 `status === 'extracted'` 的教材。
   - 上传返回 `status === 'error'` 时不要加入 `selectedBookIds`。
   - 关联失败时阻断生成, 给出错误。
6. `CoursePage.vue` 文件选择后清空 input value。

测试:

1. mock 上传返回 `status=error`, 课程页显示失败状态。
2. mock 上传返回 `status=error`, 创建课程弹窗不自动选中该教材。
3. mock batch link 失败, 创建课程流程停在错误状态, 不调用 generate。
4. 同一个文件可连续选择两次。

### Step 3: 统一文件类型配置

建议新增一个前端常量, 例如:

```ts
export const TEXTBOOK_ACCEPT = '.pdf,.txt,.md,.markdown,.epub,.png,.jpg,.jpeg,.webp,.gif,.tif,.tiff,.bmp'
export const TEXTBOOK_FORMAT_HINT = '支持 PDF / TXT / MD / EPUB / 图片 OCR, 最大 50MB'
```

所有入口统一使用:

- `CoursePage.vue`
- `Bookshelf.vue`
- `CreateCourseModal.vue`

后端 `ALLOWED_EXTENSIONS` 仍是最终裁决。

### Step 4: 处理上传超时和解析进度

短期:

1. 给 `courseApi.uploadTextbook` 和 `bookshelfApi.upload` 单独配置更长 timeout, 例如 120 秒。
2. 文案从“上传中”改成“上传/解析中”, 避免 100% 后停住的误导。

长期:

1. 上传接口只负责接收文件并创建记录, 返回 `status='extracting'`。
2. 后台任务执行解析。
3. 前端轮询教材列表或新增 `GET /textbooks/{id}/status`。
4. 失败状态展示 `error_message`。

不要只靠无限加 timeout 解决。OCR 和大文件解析天然应该是任务状态, 不是普通上传请求。

### Step 5: 修复批量关联返回值

后端在创建每个 `Textbook` 后 `flush()` 拿到 ID:

```python
db.add(textbook)
db.flush()
results.append({
    "textbook_id": textbook.id,
    "library_id": lib_id,
    "skipped": False,
})
```

这样前端后续可以精确展示关联结果, 也便于调试。

## 7. 推荐验收标准

修复完成后应满足:

1. 从课程移除书架教材不会删除书架文件。
2. 删除仍被课程引用的书架教材不会留下悬空课程记录。
3. 书架列表的 `linked_course_ids` 来自真实外键, 不依赖 `file_path`。
4. 解析失败的教材不会被显示为普通成功。
5. 解析失败的教材不能被选中用于课程生成。
6. 课程生成按钮只在至少存在一份可用教材文本时启用。
7. 三个上传入口支持的文件格式一致。
8. 扫描 PDF/OCR 耗时较长时, UI 不再只显示网络上传进度并最终报通用 timeout。
9. 后端测试覆盖书架-课程共享文件生命周期。
10. 前端测试覆盖上传失败、解析失败、关联失败和重复选择同一文件。

## 8. 暂不建议做的事

1. 不建议只改 toast 文案, 这不能解决文件生命周期问题。
2. 不建议继续用 `file_path` 作为隐式关联键。
3. 不建议在删除书架教材时静默级联删除所有课程关联, 除非 UI 明确二次确认。
4. 不建议先大规模重命名表和模型; 当前更需要小步修复数据一致性。
5. 不建议把 OCR/EPUB 大文件解析继续长期绑在单个上传请求里。

## 9. 待拍板问题

1. 课程页“上传教材”是否也应该先进入书架, 然后自动关联当前课程?
   - 推荐: 是。这样教材只有一个资产来源, 后续复用和删除更清晰。
2. 删除书架教材时, 如果已经关联课程, 产品行为应该是什么?
   - 推荐第一版: 返回 409, 提示先从课程解除关联。
   - 后续可加“同时解除所有课程关联并删除”的显式危险操作。
3. 解析失败的教材是否保留文件?
   - 推荐: 保留, 允许用户查看错误、删除或未来重试解析。
4. 异步解析是否进入本轮修复?
   - 推荐: 第一轮只加 timeout 和状态展示; 第二轮再做后台任务。

