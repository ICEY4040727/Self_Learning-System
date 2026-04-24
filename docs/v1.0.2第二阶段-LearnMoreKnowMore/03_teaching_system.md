# 系统三：教学系统（PromptBuilder + RecallService）— 详细设计

> **版本**：v1.0.2 | **日期**：2026-04-24 | **状态**：设计中
> **理论**：Vygotsky 最近发展区（ZPD）——教学内容应在学生"能独立完成"和"在指导下能完成"之间。StrategyModule 的本质就是 ZPD 调整：低维度多引导，高维度少引导。

---

## 一、问题

| 编号 | 问题 | 阻碍 | 说明 |
|------|------|------|------|
| T1 | 无教学策略层 | **高** | PromptBuilder 不区分"这个学生擅长抽象思维"和"这个学生需要具体例子" |
| T2 | 无记忆召回上下文 | **高** | MemoryFactsModule 注入原始事实列表，但没有上下文化的教学关联提示 |
| T3 | context 结构无文档 | 中 | PromptBuilder 的 context dict 缺乏类型定义 |
| T4 | 无概念图谱 | **高** | RecallService 需要"学树遍历时关联递归"，但没有结构化的概念关系数据。concept_tags 全靠 LLM 在 `<memory>` 中输出，自引用循环 |

---

## 二、方案

### 2.1 新增 StrategyModule（priority=25）

根据画像维度值匹配策略规则，注入"怎么教"的指令。

**新增表：strategy_rules**

| 字段 | 说明 |
|------|------|
| dimension_key | 关联 profile_dimension_defs.key |
| low_instruction | 维度值 < 0.4 |
| mid_instruction | 0.4-0.7（null = 不干预） |
| high_instruction | > 0.7 |
| priority | 多规则排序 |
| scene | "learning"/"review"/"all" |
| enabled | 是否启用 |

**种子数据**：

| dimension_key | low | high |
|---------------|-----|------|
| abstract_thinking | 用具体实例和类比辅助理解 | 可以直接讨论抽象模式 |
| problem_solving | 分步骤引导，每步确认理解 | 鼓励自主探索 |
| self_monitoring | 主动询问是否理解 | 引导学生自评 |
| learning_resilience | 额外鼓励，降低难度 | 挑战更难问题 |

**新增策略 = 新增一行数据。**

### 2.2 新增 RecallContextModule（priority=75）

从 RecallService 获取上下文化的记忆召回提示。

与 MemoryFactsModule 互补：
- MemoryFactsModule 注入原始事实列表（"学生对递归有困难"）
- RecallContextModule 注入上下文化的教学提示（"之前学递归遇到困难，教树遍历时注意关联"）

### 2.3 概念图谱（Course.concept_map）

RecallService 需要"学树遍历时关联递归"——前提是系统知道"树遍历"和"递归"有关联。

**方案：在 Course 上增加 concept_map 字段**

```json
// Course.metadata.concept_map
{
  "nodes": [
    {"id": "recursion", "label": "递归", "category": "algorithm"},
    {"id": "tree_traversal", "label": "树遍历", "category": "data_structure"},
    {"id": "binary_tree", "label": "二叉树", "category": "data_structure"}
  ],
  "edges": [
    {"source": "tree_traversal", "target": "recursion", "type": "requires"},
    {"source": "binary_tree", "target": "tree_traversal", "type": "applies"}
  ]
}
```

**概念图谱的来源**：

| 来源 | 何时 | 质量 | 成本 |
|------|------|------|------|
| **教材上传时提取**（首选） | 上传教材 → LLM 分析目录和章节引用关系 | 高 | 1 次 LLM 调用 |
| **首次学习时构建**（兜底） | 第一次教某概念时，LLM 从教材内容中提取关联 | 中 | 每概念 1 次 |
| **手动配置** | 教师在后台编辑 | 最高 | 人工 |

**教材上传提取流程**（在 Course 创建 API 中增加一步）：

```
上传 PDF → 解析目录结构 → LLM 提取概念和关系 → 存入 concept_map
                                    ↓
                        {chapter_title, section_titles, key_terms}
                        → "递归" 出现在第3章
                        → 第5章"树遍历"引用了"递归"
                        → edge: tree_traversal requires recursion
```

**关键设计决策**：concept_map 在 Course 级别（非 World 级别），因为概念关系是教材的固有属性。一个 World 对应一个 Course，自然有一个 concept_map。

### 2.4 RecallService

```
输入：
  - 当前 topic（从 concept_map 中当前正在学的概念 ID）
  - concept_map（Course.metadata.concept_map）
  - MemoryManager.observe_recent()

关联逻辑：
  1. 从 concept_map.edges 找到当前 topic 的前置概念（type=requires 的 source）
  2. 从 MemoryManager 检索前置概念的 struggle/mastered 记忆
  3. 如果有前置概念未 mastered → 注入提示"建议先复习 X"
  4. 如果有前置概念曾经 struggle → 注入提示"学生之前学 X 时遇到困难"

降级策略：
  - 无 concept_map → 不注入 RecallContext（不是降级为模糊匹配，而是跳过）
  - 有 concept_map 但 topic 不在 nodes 中 → 跳过
  - 有 concept_map + topic → 执行完整关联逻辑
```

**为什么不做模糊匹配降级**：模糊匹配（"递归"和"树递归"共享"递归"子串）的准确率不可控，可能产生错误关联（"树"和"二叉树"关联，但"树"在讲植物）。不如在有 ground truth 时才关联。

### 2.5 context 扩展

新增 `course_progress` 字段（current_step, completed_steps, mastery_per_step）。

---

## 三、改造清单

| 文件 | 改动 | 说明 |
|------|------|------|
| `prompt_builder/modules/strategy.py` | **新建** ~60 行 | StrategyModule |
| `prompt_builder/modules/recall_context.py` | **新建** ~30 行 | RecallContextModule |
| `recall_service.py` | **新建** ~120 行 | 记忆召回服务 |
| `models.py` | **改** | 新增 StrategyRule |
| `course API` | **改** | 上传时增加概念图谱提取 |
| `prompt_builder/builder.py` | **改** ~3 行 | Module 注册 |

---

## 四、测试

| 测试 | 验证什么 |
|------|---------|
| test_strategy_low | 低维度命中 low_instruction |
| test_strategy_null_mid | mid 为 null 时不注入 |
| test_recall_no_topic | 无 concept_map 时跳过（不是模糊匹配） |
| test_recall_related | concept_map 中的前置关联正确检索 |
| test_recall_prerequisite_struggle | 前置概念 struggle 时注入复习提示 |
| test_concept_map_extract | 教材上传时概念图谱提取 |
