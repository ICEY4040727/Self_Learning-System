# v1.0.4 文档索引

这一组文档只讨论“世界壳 -> 课程教学结构 -> 角色 -> 课程叙事”的收敛，不再把世界创建做成剧情生成器。

## 当前收束状态

- 世界壳第一阶段已进入发布收束：正式契约收敛为 `World.description + World.background_picture`。
- `scenes` 已退出世界壳前后端正式契约；数据库列是否删除不阻塞本轮发布。
- `world_plan` 对外语义已收敛为 `course_narrative_plan`；旧字段只作为历史/内部兼容存在。
- v1.0.4 不继续扩大课程叙事执行器范围，优先整理已完成改动、补齐验证并降低发布风险。
- 发布检查见 [release-checklist.md](./release-checklist.md)。

## 架构设计文档（四大系统闭环）

| 文档 | 说明 |
|------|------|
| [WholeDesign.md](./WholeDesign.md) | 闭环总览；**功能描述附源码行号锚点** |
| [01_memory_system.md](./01_memory_system.md) | 记忆系统详细设计 |
| [02_learner_profile.md](./02_learner_profile.md) | 学习画像 |
| [03_teaching_system.md](./03_teaching_system.md) | 教学系统 |
| [04_narrative_system.md](./04_narrative_system.md) | 叙事系统 |

锚点格式：`[file:line](../../backend/.../file.py#Lline)`，相对 `docs/v1.0.4/`。可重复运行 `scripts/annotate_v104_doc_anchors.py` 批量刷新链接。

## 阅读顺序

1. [ai_world_generate.md](./ai_world_generate.md)
   - 目标定义：世界壳应该长什么样。
2. [world-generation-current-state-analysis.md](./world-generation-current-state-analysis.md)
   - 现状分析：当前代码为什么还没对齐目标。
3. [world-course-character-gap-analysis.md](./world-course-character-gap-analysis.md)
   - 缺口分析：课程、角色、叙事还差哪些结构。
4. [world-course-refactor-implementation-plan.md](./world-course-refactor-implementation-plan.md)
   - 世界壳创建执行文档：只讲世界壳怎么落地。
5. [world-shell-guided-intake-design.md](./world-shell-guided-intake-design.md)
   - 世界壳引导式采集设计：只讲创建向导怎么问。
6. [world-shell-wizard-fields-and-page-outline.md](./world-shell-wizard-fields-and-page-outline.md)
   - 世界壳向导字段与页面草图：只讲具体字段和页面组织。
7. [world-shell-wizard-frontend-state-and-component-split.md](./world-shell-wizard-frontend-state-and-component-split.md)
   - 世界壳向导前端状态与组件拆分：直接服务 `CreateWorldModal.vue` 重构。
8. [create-world-modal-refactor-task-list.md](./create-world-modal-refactor-task-list.md)
   - `CreateWorldModal.vue` 重构任务清单：直接服务实施。
9. [release-checklist.md](./release-checklist.md)
   - v1.0.4 收束发布检查清单：记录冻结范围、验证命令和剩余风险。

## 当前共识

- `World.description` 承载世界舞台说明。
- `World.background_picture` 承载默认背景图。
- `world_plan` 的目标语义应理解为 `course_narrative_plan`。
- 世界创建不生成剧情。
- 课程创建时，先教材教学结构，再引入角色，最后生成课程叙事。
- `LearningPlanDraft -> commit_learning_plan_draft()` 不应继续作为主路径。

## 相关但独立

- [textbook-upload-fix-plan.md](./textbook-upload-fix-plan.md)
