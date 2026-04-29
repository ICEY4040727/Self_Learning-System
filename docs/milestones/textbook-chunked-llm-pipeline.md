# Milestone: Chunked LLM Pipeline for Textbook Course Generation

> Status: **Proposed** — not started
> Triggered by: `docs/v1.0.3 Review/textbook-system-deep-review.md` UNCERTAIN-4
> Owner: TBD
> Target version: v1.0.4 or v1.1

---

## 目标

教材超过 LLM 上下文限额（当前 80000 字符）时，**完整覆盖整本教材** 而不是丢弃中间或末尾。

通过 map-reduce 流水线：
1. 提取整本纯文本
2. 按某种策略切分（字符 / 章节 / 页）
3. 每段单独调 LLM 生成局部 outline
4. 合并所有局部 outline → 最终 lessons / overview / concept_map

---

## 与本 milestone 之外的关联

- v1.0.3 review 已经选择"章节边界截断"（X12 方案 B）作为临时修复，把 P2 bug 关闭。本 milestone 是真正的解决方案，启用后 X12 的临时修复可以清掉。
- 入口仍然是 `POST /api/courses/{course_id}/generate`，但需要新增 `pipeline_strategy` 参数（或自动判断长度切换）。

---

## 待设计点（需另写 design doc 才动手）

### 1. 切分策略

| 策略 | 描述 | 取舍 |
|---|---|---|
| 按字符 | 每 N 字符切一段，段间按字符边界 | 实现最简；可能切到一句话中间 |
| 按章节 | 用正则识别章节标题，按章节切；多章合一段直到达字符上限 | 语义自然；正则需多语种支持 |
| 按页（仅 PDF） | 用 PyMuPDF 按 page 累计到字符上限 | PDF 友好；EPUB/MD 不通用 |
| 混合 | PDF 走章节优先 + 页 fallback；EPUB/MD 走章节 + 字符 fallback | 复杂但鲁棒 |

### 2. 局部 prompt

每段单独调 LLM 时：
- 让每段都生成 `{overview, lessons, concept_map}` 完整结构？还是只生成 `lessons` + `concept_map` 节点？
- 是否在 prompt 里注入"这是第 K 段，共 N 段"上下文，让 LLM 知道自己看的是局部？
- 是否在 prompt 里注入前一段的 outline 让 LLM 续写？（trade-off：上下文累加 vs 独立处理）

### 3. 合并算法

合并 N 段返回的局部 outline：

- **lessons**：去重（按 title 完全匹配？按 concepts 集合 Jaccard 相似度？按 order 重新排序？）
- **overview**：N 段都生成了 overview → 取最长？concat？再调一次 LLM 合成？
- **concept_map**：
  - nodes：按 id 去重；同 id 不同 label 时取哪个？
  - edges：按 (source, target, relation) 三元组去重

### 4. 错误处理

- 某段 LLM 调用失败：整体失败 / 跳过该段（标记 `partial=True`）
- LLM 返回 JSON 解析失败：retry N 次？fallback 到只取已成功段？
- 超时：单段 timeout 设多少？整体 timeout？

### 5. 成本与延迟

- 200000 字符教材 → 3 段 + 1 合并 = 4× LLM 调用
- 串行：~30-60s；并行：~10-15s（受 provider rate limit 约束）
- API 费用 ~3-5×
- 是否要加成本估算 + 用户确认（前端弹窗）？

### 6. UI 影响

- 前端 generate course 按钮变成长任务，需要进度反馈
- 选择性章节生成（"只生成第 1-5 章"）是否纳入？
- 失败时如何呈现 `partial=True` 状态？

### 7. 测试与回归

- 单段 vs 多段输出的语义等价性测试（不能强等价，但 lessons 总数、关键 concept 覆盖率不能差太多）
- 各步失败的回滚 / 部分成功测试
- 成本/延迟回归（CI 跑不动 LLM，需要 e2e 单独跑）

### 8. 配置开关

- 加 `pipeline_strategy: 'simple' | 'chunked'` 配置 / 请求参数
- 默认走 `simple`（兼容当前），用户/教材超阈值时自动或显式切到 `chunked`

---

## 进入 Doing 的前置条件

1. 上面 8 项每项有明确决策
2. 写出 prompt 设计稿 + 合并算法伪代码
3. 估算 API 费用（用 prod 实际教材 token 数）
4. 与前端协调进度条 / 选择性章节 UI

---

## 不在本 milestone 内的事

- streaming 渲染 lessons
- 教材内嵌图片识别 / 公式 OCR
- 多模态 LLM（直接喂 PDF 二进制）
- 教材版本管理 / diff
