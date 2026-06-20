# 世界 / 课程 / 角色生成能力缺口分析

本文不是在讲“愿景”，而是对照当前代码，逐层说明：

1. 现在到底已经实现了什么。
2. 哪些地方只是存了字段，但没有形成语义闭环。
3. 哪些地方是明显的 schema 错位或数据丢失。
4. 为什么这些功能还没有真的完成。
5. 应该按什么顺序补。


---

## 1. 目标到底是什么

你要的不是一个普通的“世界描述生成器”，而是一个学习世界编译系统。它要满足下面这三个职责层。

### 1.1 World 负责长期容器和氛围

World 不是教材本身，也不是角色本身。它的职责是长期容器，应该承载：

- `World.name`
- `World.description`
- `World.background_picture`

World 的正确定位是：提供一个长期可复用的世界壳，给后续课程和角色提供舞台，但不承载课程叙事结构本身。

### 1.2 Course 负责契约、节奏、目标和教材锚定

Course 是教学编译的主线，至少要稳定承载：

- `Course.name`
- `Course.description`
- `Course.target_level`
- `Course.meta`
- `LessonPlan`
- `CourseProgress`

但课程真正应该保证的是下面这些结构：

- 章节结构
- 原子知识点
- 先修关系
- 例题与练习点
- 可能误解
- 课程目标与检查点
- 每个节点的教材来源位置

Course 的边界就是：剧情只能围着这些结构服务，不能凭空跑偏。

### 1.3 Character 负责关系和教学声音

Character 不是单纯的人设卡，它至少要承载：

- `Character.traits`
- `Character.system`
- `Character.greeting`
- `WorldCharacter.world_title`
- `WorldCharacter.world_background`
- `WorldCharacter.relationship_seed`
- `WorldCharacter.world_greeting`

这里最关键的拆分是：

- `Character` 负责“全局人格”。
- `WorldCharacter` 负责“在某个世界里的身份、关系起点和开场方式”。

同一个导师进入不同世界，声音可以一致，但身份和关系不该一样。

---

## 2. 当前已经落地了什么



## 5. 课程层到底还缺什么



## 6. 角色层到底还缺什么

### 6.1 `Character` 已经能当人格卡，但还没进教材优先流

`Character.traits` 和 `system_prompt_template` 已经会进入 prompt builder，见 `backend/services/prompt_builder/builder.py:166` 到 `backend/services/prompt_builder/builder.py:221`。

但是在教材优先 commit 流程里：

- `character_plan` 只进了 `Course.meta`
- 没有创建 `Character`
- 没有创建 `WorldCharacter`
- 没有写 `world_title`
- 没有写 `world_background`
- 没有写 `relationship_seed`
- 没有写 `world_greeting`

见 `backend/api/routes/learning_plans.py:239`。

所以角色层现在是“已有模型、已有模板、已有绑定接口”，但还没有被教材优先流程真正驱动。

### 6.2 角色上下文生成存在，但它只是补上下文，不是生成角色体系



它没有做这些事：

- 根据课程目标自动决定角色分工
- 根据章节调整角色语气
- 根据世界主线调整角色职责
- 根据事件池生成角色行为规则
- 根据关系阶段生成角色语气变化

### 6.3 `learning_engine` 里真正消费到的角色信息也有限

会话启动时，`system_prompt` 主要来自 `sage_character.system_prompt_template`，见 `backend/api/routes/learning.py:503`、`backend/api/routes/learning.py:504`。

开场白优先级是：

1. `world_greeting`
2. `custom_greeting`
3. `dynamic_greeting`
4. fallback

见 `backend/api/routes/learning.py:323` 到 `backend/api/routes/learning.py:350`。

这意味着角色层目前确实参与了对话，但它还没有从“对话层人格”变成“教材驱动角色系统”。

---

## 7. 为什么没有实现到你说的那个形态

### 7.1 现有实现是分阶段堆上来的

代码里很明显能看到几个阶段并存：

- 早期是世界 / 角色 / 课程 CRUD。
- 后来加 AI 世界生成。
- 后来加教材上传和课程生成。
- 再后来加 `LessonPlan`、`CourseProgress`、`LearningPlanDraft`。
- 再后来加 prompt builder 和叙事 / 成就观察器。

由于是这样逐层叠上来的，所以很多功能被做成了“兼容旧结构 + 新结构并存”。

最直接的证据是：

- `CourseContentModule` 还会回退到 `course.meta.generated_lessons`，见 `backend/services/prompt_builder/modules/course_content.py:68` 到 `backend/services/prompt_builder/modules/course_content.py:70`。
- `NarrativeTriggerRule` 和 `AchievementDef` 还留着对未知 condition_type 的 warning，而不是强类型 DSL，见 `backend/models/models.py:472` 到 `backend/models/models.py:508`。
- `commit_learning_plan_draft()` 里 `commit_world` 参数存在，但当前没有用，见 `backend/api/routes/learning_plans.py:41` 到 `backend/api/routes/learning_plans.py:47`、`backend/api/routes/learning_plans.py:180` 到 `backend/api/routes/learning_plans.py:216`。

### 7.2 结构不统一，导致运行时只能消费一部分

世界层最明显的例子就是三套 `World.scenes` 结构。

课程层最明显的例子就是：

- 新结构：`LessonPlan` + `CourseProgress`
- 旧结构：`course.meta.generated_lessons` + `current_lesson_index`

角色层最明显的例子就是：

- 全局人格：`Character`
- 世界内身份：`WorldCharacter`
- 会话内 prompt：`Session.system_prompt`

这些结构都存在，但它们没有被统一成一套“编译后 schema”。

### 7.3 缺少校验器，所以很多约束只是写在注释里

比如：

- 剧情不能替代教材
- 每个事件都要回指章节或知识点
- 角色开场白不能偏离课程目标
- 先修关系不能断裂

这些要求现在大多只在：

- prompt 文案
- docs
- 注释
- draft 生成逻辑

里出现。

但没有一个正式 validator 去拦截违反规则的数据。

### 7.4 缺少前端审阅面，导致蓝图无法稳定修正

`Bookshelf.vue` 目前只能展示 draft 概要，见 `frontend/src/views/Bookshelf.vue:35` 到 `frontend/src/views/Bookshelf.vue:47`。

它没有提供：

- 章节树编辑
- knowledge blueprint 审阅
- route bible 审阅
- event pool 审阅
- role plan 审阅
- source span 审核

所以即使后端生成了蓝图，用户也没法把它修到“能执行”的程度。

---

## 8. 哪些地方是具体 bug 或明显断点



## 9. 改进应该怎么落

### 9.1 第一优先级：先修数据丢失

先把最明显的断点修掉：

- 普通创建世界把 `scenes` 传到后端。
- 世界编辑不要默认清空 `scenes`。
- `worldApi.create`、`worldApi.update` 类型允许 scenes。

这是基础稳定性问题，不先修，后面任何世界底座都会被覆盖掉。

### 9.2 第二优先级：先把世界壳收缩成顶层字段

在当前产品边界下，世界壳不应该承担课程叙事结构。它应该只保留最小字段：

```json
{
  "background_picture": "..."
}
```

世界舞台说明应直接落在 `World.description`，不再保留 `world_detail` 这条平行语义路径。这一步的目标不是统一所有生成结构，而是先把世界壳和课程叙事拆开。

### 9.3 第三优先级：把 `world_plan` 从文档语义上改名

当前代码里的 `world_plan` 其实不是“世界计划”，而是课程叙事编排草图。

文档层建议使用：

- 当前代码名：`world_plan`
- 目标语义名：`course_narrative_plan`

它的生成顺序应该固定为：

1. 根据教材知识结构生成课程教学结构。
2. 引入角色。
3. 根据世界壳和角色生成课程叙事结构。

没有其他生成方式。
### 9.4 第四优先级：把教材蓝图变成可校验结构

至少要把这些结构从“粗提取”升级成“可验证”：

- `chapters`
- `atomic concepts`
- `prerequisites`
- `examples`
- `exercises`
- `misconceptions`
- `checkpoints`

并且每个节点都要有：

- `source_textbook_id`
- `source_span`
- `confidence`

这样你才能真的判断“剧情有没有偏离教材”。

### 9.5 第五优先级：删除教材优先 draft commit 旁路

如果产品主流程已经固定为：

1. 先创建世界壳。
2. 进入世界壳后，根据教材生成课程教学结构。
3. 引入角色。
4. 根据世界壳和角色生成课程叙事结构。

那 `LearningPlanDraft -> commit_learning_plan_draft()` 这条“教材优先直接 commit 世界和课程”的旁路就不应该再是主流程。

它当前带来的损害很具体：

- 绕过世界壳入口。
- 把课程叙事草图写进 `World.scenes`。
- 让 `world_plan` 继续伪装成世界结构。
- 把课程创建变成一条与正式世界入口平行的历史分支。



### 9.6 第六优先级：让课程创建流程真正落实角色

至少要补：

- `character_plan` -> 创建或绑定 `Character`
- 生成 `WorldCharacter`
- 写入 `world_title`
- 写入 `world_background`
- 写入 `relationship_seed`
- 写入 `world_greeting`
- 必要时写入 `Course.meta.sage_ids`

这样教材优先流程才真正形成世界 + 课程 + 角色的一体化结果。

### 9.7 第七优先级：把 event_pool 接到 runtime

`event_pool` 不能继续只是 JSON。

最小接法是把它接到：

- `NarrativeEngine`
- `PromptBuilder`
- 前端事件展示

并至少区分：

- teaching event
- review event
- relationship event
- affect event

每类事件都要能回指到 lesson / concept / checkpoint。

---

## 10. 推荐的实施顺序

### Phase 1: 修数据不丢

修：

- world create scenes 丢失
- world update scenes 覆盖
- API 类型不匹配
- 创建和编辑链路的数据保持

### Phase 2: 稳定世界壳

修：

- `background_picture`
- `world_detail`
- 创建和编辑链路的字段保持

### Phase 3: 课程教学结构先成形

修：

- 章节树
- 原子知识点
- 先修关系
- 例题
- 练习
- 误解
- 检查点

### Phase 4: 引入角色后生成课程叙事结构

修：

- `course_narrative_plan`（当前代码名 `world_plan`）
- 世界壳 + 角色 -> 课程叙事
- `NarrativeModule`
- `event_pool`

### Phase 5: 删除教材优先 draft commit 旁路

修：

- `LearningPlanDraft`
- `commit_learning_plan_draft()`
- `world_plan` 写入 `World.scenes`
- 平行课程创建入口

### Phase 6: 让角色真正落位

修：

- `character_plan`
- `WorldCharacter`
- `sage_ids`
- `world_greeting`

### Phase 7: 让事件池可执行

修：

- `event_pool`
- `NarrativeEngine`
- 复习事件
- 情绪事件
- 关系事件

---

## 11. 最后一句话

当前系统离你的目标，不是差一个“世界描述文案生成器”，而是差一个真正的教材编译与世界编排层。

最具体的缺口已经很明确：

1. 不同入口写了三种不兼容的 `World.scenes`。
2. 普通创建世界丢 scenes。
3. 编辑世界会清空 scenes。
4. draft commit 的 `world_plan` 实际是课程叙事草图，但却被塞进了世界壳字段。
5. `character_plan` 只存不落。
6. `event_pool` 只是 JSON，没有执行器。
7. 教材解析还停留在启发式提取，没有原子知识点、source span、检查点和可校验约束。

所以后续不是继续加几个 prompt 字段，而是先把“世界壳 -> 教材教学结构 -> 角色 -> 课程叙事结构 -> runtime 消费”这条链打通。

---

## 12. 函数级追踪：现在到底是怎么“粗提”的
这一段再往下拆一层，直接说明为什么当前产物看起来很完整，但其实还只是启发式拼装，不是教材编译器。

### 12.1 教材解析不是编译器，而是几层启发式规则

| 函数 | 当前输入 | 当前输出 | 缺的语义 | 直接后果 |
| --- | --- | --- | --- | --- |
| `_extract_chunks()` | 合并后的教材全文，外加标题正则 | `chapter_tree` / `chunks` | `source_span`、段落边界、置信度、章节内部结构 | 只能按标题切块，正文、例题、注释、附录会被混在一起 |
| `_top_keywords()` | 合并后的教材全文 | `extracted_topics`、`knowledge_blueprint.concepts` 的候选词 | 概念消歧、同义合并、概念边界、可测验性 | 把高频词当概念，容易得到“词袋”而不是原子知识点 |
| `_extract_exercise_lines()` | 包含练习提示词的行 | `exercises` | 题型、难度、答案、目标概念、评分标准 | 只能拿到题目壳，不能形成真正的练习模型 |
| `_extract_misconceptions()` | 包含误区提示词的行 | `common_misconceptions` | 错误模式、严重度、纠错策略、对应概念 | 误解只是字符串，不足以驱动修复事件 |
| `build_learning_plan_blueprint()` | `library_items + goal + course_form` | `material_analysis / knowledge_blueprint / course_blueprint / world_plan / character_plan` | 版本化 schema、validator、稳定字段契约 | 产物结构很多，但 `world_plan` 实际上承载的是课程叙事草图，不是世界壳 |
| `_route_type_from_goal()` | `goal + course_form` | `route_type` | 真正的教学策略选择器 | 路由类型只是关键词分类，不是课程编排决策 |

这就是为什么现在能“看起来像蓝图”，但还不能“证明它是对的”。

### 12.2 入口级字段损失表

| 入口 | 实际保留 | 丢失 / 覆盖 | 运行时后果 |
| --- | --- | --- | --- |
| `CreateWorldModal.vue` -> `Worlds.vue` -> `worldApi.create()` -> `create_world()` | `name`、`description` | `scenes` 在前端提交链路里被丢掉；`worldApi.create()` 类型也没收这个字段 | 用户以为世界已带场景，数据库里却只有名字和描述 |
| `WorldDetail.vue` -> `worldApi.update()` -> `update_world()` | `name`、`description` | `db_world.scenes = world.scenes or {}`，未提交 `scenes` 时会直接覆盖成空字典 | 一个普通编辑就可能把世界底座、氛围、角色辅助字段清空 |
| `Bookshelf.vue` -> `createDraft()` -> `commitDraft()` -> `commit_learning_plan_draft()` | `material_analysis`、`knowledge_blueprint`、`course_blueprint`、`world_plan`、`character_plan` | `commit_world` 形参存在但没用；不创建 `Character` / `WorldCharacter`；`event_pool` 不进入任何执行器 | 能生成世界、课程、章节，但还没形成完整“教材驱动的世界-角色闭环” |
| `update_learning_plan_world()` | 顶层 `payload` | 只是浅合并：`draft.world_plan = {**old, **payload}` | 如果前端只改一部分，嵌套的 `world / route_bible / event_pool` 可能被整段覆盖 |
| `frontend/src/stores/learning.ts` | `data.scenes.background` | 只认 `background/menu_background`，也还没切到 `background_picture` | 运行时学习页只看见背景图，世界壳字段仍然没有被干净消费 |
| 角色绑定链路 | `world_title`、`world_background`、`relationship_seed`、`world_greeting` | `commit_learning_plan_draft()` 没有调用 `generate_world_character_context()` / `create_world_character()` | 教材优先流程里角色层仍然是未落地的草稿，而不是已绑定的世界内角色 |

### 12.3 运行时到底读什么

- `WorldSettingModule` 只读 `world.name / world.description / scenes.mood / scenes.theme_preset / scenes.bgm`，见 `backend/services/prompt_builder/modules/world_setting.py:36` 到 `backend/services/prompt_builder/modules/world_setting.py:57`。
- `NarrativeModule` 只读 `scenes.narrative` 或 `scenes.narrative_input`，并且期待里面有 `world_theme / learner_role / sage_role / knowledge_metaphor / progression_arc`，见 `backend/services/prompt_builder/modules/narrative.py:53` 到 `backend/services/prompt_builder/modules/narrative.py:90`。
- `CourseContentModule` 优先读 `LessonPlan` + `CourseProgress`，读不到才回退到 `course.meta.generated_lessons`，见 `backend/services/prompt_builder/modules/course_content.py:60` 到 `backend/services/prompt_builder/modules/course_content.py:139`。
- `TeachingPlanner` 也已经优先读 `LessonPlan`，但仍保留 `course.meta.current_lesson_index` / `completed_lessons` 的旧路径，见 `backend/services/teaching_planner.py:34` 到 `backend/services/teaching_planner.py:90`。
- `MasteryTracker` 仍然直接用 `course.meta.generated_lessons`、`current_lesson_index`、`completed_lessons` 计算掌握度与自动推进，见 `backend/services/mastery_tracker.py:121`、`backend/services/mastery_tracker.py:203`、`backend/services/mastery_tracker.py:315`。
- `event_pool` 目前没有任何明确消费者，既不在 `PromptBuilder` 里，也不在 `NarrativeEngine` 里，更不在前端里单独编辑。

换句话说，现在 runtime 真正稳定消费到的，还是少数几个字段：

- 世界：`name`、`description`、`background`
- 课程：`LessonPlan`、`CourseProgress`、少量 `course.meta` 回退字段
- 角色：`Character.system_prompt_template`、`Character.greeting`、`WorldCharacter.world_*`

而你希望的那套：

- 世界底座
- 长期主线
- 角色关系规则
- 教学事件池
- 复习事件池
- 情绪与关系事件池
- 触发条件

现在还没有变成统一 schema，也没有变成统一消费者。

## 13. 最小验收标准

如果要把这件事做成“真的完成了”，最小验收标准应该是：

1. 普通创建世界时，`scenes` 能完整落库并回读。
2. 编辑世界时，未提交 `scenes` 不会清空原数据。
3. `commit_learning_plan_draft()` 会真正创建或绑定 `Character` / `WorldCharacter`。
4. `World.background_picture` 成为唯一世界背景字段。
5. `LessonPlan`、`CourseProgress`、`MasteryTracker` 不再依赖旧的 `course.meta.generated_lessons` 作为主路径。
6. 每个章节 / 知识点至少有 `source_textbook_id`、`source_span`、`confidence` 三个校验字段。
7. `event_pool` 至少有一个运行时消费者，且能回指到 lesson / concept / checkpoint。
8. `LearningPlanDraft -> commit_learning_plan_draft()` 不再是产品主路径。

## 14. 修正后的产品边界

现在要把产品链重新定清楚，不要再把世界、课程、角色三件事放在同一个生成节点里。

| 阶段 | 主责任 | 输入 | 输出 | 现有基础设施 |
| --- | --- | --- | --- | --- |
| 世界创建 | 建壳 | 世界名、简介、背景图、世界说明 | `World`、基础 `scenes` | `POST /worlds`、`CreateWorldModal`、`WorldDetail` |
| 课程创建 | 编排 | 教材 | 课程教学结构 | `CourseGenerator`、`bookshelf` |
| 角色引入 | 绑定 | 已存在角色 + 世界壳 | `WorldCharacter` | `character` 接口、`world character` 接口 |
| 课程叙事生成 | 编排 | 课程教学结构 + 世界壳 + 角色 | `course_narrative_plan`（当前代码名 `world_plan`） | 角色上下文生成 |
| 课程提交 | 落库 | 上一步蓝图 | `Course`、`LessonPlan`、`CourseProgress`、`WorldCharacter`、课程叙事字段 | 正式课程创建接口 |
| 运行时 | 消费 | 已落库课程与世界 | prompt、对话、复习、叙事触发 | `PromptBuilder`、`TeachingPlanner`、`MasteryTracker`、`NarrativeEngine` |

这里最重要的改动不是“再做一个新系统”，而是把现有系统的职责顺序调正：

1. 世界创建不生成剧情。
2. 课程创建的第一步是根据教材生成课程教学结构。
3. 第二步是引入角色。
4. 第三步才是根据世界壳和角色生成课程叙事结构。
5. 没有其他生成方式。
6. 不再继续扩展教材优先 draft commit 旁路。

从技术组长视角看，当前真正的问题不是“功能太少”，而是：

- pipeline 没有按产品阶段分层。
- 数据契约没有按入口收口。
- 现有基础设施已经够用，但没有被按正确顺序串起来。
- 过度设计的风险在于先追求统一 schema，结果把本来可落地的流程拖成了新架构工程。

所以更合理的做法是：

- world 只负责世界壳。
- course 先负责教材教学结构，再负责课程叙事结构。
- 角色在课程叙事生成前引入。
- runtime 只负责消费。
- `LearningPlanDraft` 先当课程编排器，不要先发明一个新的总控引擎。
