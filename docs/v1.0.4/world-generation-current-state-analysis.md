# 世界生成代码现状分析

本文只分析当前代码现状，不提出代码改动。

先给结论：当前“世界生成”已经有可用的基础设施，但它现在应该被重新定义为“世界壳生成”。它不是剧情生成器，也不应该在世界创建阶段变成剧情生成器。真正的问题不是缺一个更大的生成系统，而是现有 pipeline 没打通、字段契约不一致、持久化链路断开。

## 1. 正确产品边界

世界创建阶段的职责应该是：

- 建立长期容器。
- 保存世界名、简介、默认背景图、基础世界说明。
- 不依赖课程。
- 不依赖人物。
- 不生成剧情主线。
- 不生成教学事件池。

课程叙事生成应该发生在课程创建阶段，因为那时才有完整输入：

- 教材内容。
- 根据教材推导出的课程教学结构。
- 已导入人物。
- 世界壳。

完整顺序应该是：

1. 先创建世界壳。
2. 进入世界壳后，根据教材生成课程教学结构。
3. 引入角色。
4. 根据世界壳和角色生成课程叙事结构。

没有其他生成方式。

## 2. 当前世界生成入口

当前后端入口是 `POST /world/generate`，在 `backend/api/routes/archive.py:846`。

它的请求模型是：

- `description`
- `inspiration_type`

见 `backend/api/routes/archive.py:77` 到 `backend/api/routes/archive.py:80`。

实际使用情况：

- `description` 被塞进 `WORLD_GENERATE_PROMPT`。
- `inspiration_type` 当前没有进入 prompt，也没有影响分支逻辑。
- 前端 `worldApi.generateWorld()` 也只发送 `{ description }`，见 `frontend/src/api/world.ts:124` 到 `frontend/src/api/world.ts:133`。

当前响应模型是：

- `name_suggestion`
- `description`
- `theme_preset`
- `mood_tags`
- `bgm_suggestion`
- `world_detail`

这说明当前代码仍然带着旧的主题化生成思路；但从 v1.0.4 的目标定义看，真正需要保留的核心字段只应该是：

- `name_suggestion`
- `description`
- `background_picture`

见 `backend/api/routes/archive.py:82` 到 `backend/api/routes/archive.py:88`。

这个接口的定位是“根据自然语言生成世界静态设定建议”。它没有直接写数据库，这是合理的，因为用户还要审阅、修改、再创建世界。

## 3. 当前前端链路

当前前端入口是 `CreateWorldModal.vue`。

它已经做了三件有价值的事：

- AI 生成后自动填充 `name / description / worldDetail` 这一类世界壳信息，见 `frontend/src/components/CreateWorldModal.vue:208` 到 `frontend/src/components/CreateWorldModal.vue:232`。
- 创建时已经会组装一个 `scenes` payload，见 `frontend/src/components/CreateWorldModal.vue:251` 到 `frontend/src/components/CreateWorldModal.vue:263`。
- 通过 `emit('create', { name, description, scenes })` 把这些字段交给父组件。
- 前端其实已经有 `buildScenesPayload()`，见 `frontend/src/constants/worldThemes.ts:112` 到 `frontend/src/constants/worldThemes.ts:122`，但当前创建链路没有复用它，仍然在 `CreateWorldModal` 里手工拼装 payload。

断点在父组件 `Worlds.vue`。

`handleCreateWorld()` 接收了 `data.scenes`，但实际调用 `worldApi.create()` 时只传了：

- `name`
- `description`

见 `frontend/src/views/Worlds.vue:122` 到 `frontend/src/views/Worlds.vue:128`。

也就是说，当前实际链路是：

```text
用户描述
-> POST /world/generate
-> CreateWorldModal 填表
-> CreateWorldModal 组装 scenes
-> Worlds.vue 丢弃 scenes
-> POST /worlds 只带 name/description
-> World.scenes = {}
```

这不是世界生成能力不足，而是生成后的静态世界壳没有被持久化。

## 4. 当前后端持久化能力

后端 `WorldCreate` 已经支持 `scenes`，见 `backend/api/routes/archive.py:182` 到 `backend/api/routes/archive.py:185`。

`create_world()` 也会把 `world.scenes` 写入 `World.scenes`，见 `backend/api/routes/archive.py:760` 到 `backend/api/routes/archive.py:769`。

所以后端不是不能存，而是前端没有传。

更严重的问题在编辑链路：

- `WorldDetail.vue` 编辑世界时只提交 `name / description`，见 `frontend/src/views/WorldDetail.vue:516` 到 `frontend/src/views/WorldDetail.vue:523`。
- 后端 `update_world()` 使用 `db_world.scenes = world.scenes or {}`，见 `backend/api/routes/archive.py:808` 到 `backend/api/routes/archive.py:823`。

这意味着用户只要编辑一次世界名称或描述，就可能把原有 `scenes` 清空。

## 5. 当前 schema 问题的本质

当前最表面的现象是 theme / mood / bgm 三套枚举不一致，但更本质的问题是：世界壳里放了太多不该存在的字段。

如果 v1.0.4 的世界壳只保留：

- `background_picture`

同时把世界舞台说明直接收回 `World.description`，那么下面这些不一致在产品层就不再应该是核心问题：

那么下面这些不一致在产品层就不再应该是核心问题：

- `theme_preset`
- `mood`
- `bgm`
- `theme_color`
- `world_detail`

### 5.1 当前代码为什么会显得混乱

因为当前代码仍然沿用旧的主题化方案：

`WORLD_GENERATE_PROMPT` 要求：

```text
academy|library|laboratory|forest|ruins|city|space|ocean
```

见 `backend/api/routes/archive.py:63`。

### 5.2 前端主题枚举

`WORLD_THEMES` 当前是：

```text
academy / library / lab / mountain / cyber / blank
```

见 `frontend/src/constants/worldThemes.ts:17` 到 `frontend/src/constants/worldThemes.ts:74`。

直接后果：

- 后端可能返回 `laboratory`，前端只认 `lab`。
- 后端可能返回 `forest / ruins / city / space / ocean`，前端主题网格都没有。
- 只有 `academy / library` 基本稳定匹配。

### 5.3 BGM 枚举也不一致

后端 prompt 要求：

```text
silent|classical|ambient|lofi|nature|epic|jazz
```

见 `backend/api/routes/archive.py:65`。

前端 `BGM_PRESETS` 当前是：

```text
whitenoise / rainy_piano / morning_guitar / silent
```

见 `frontend/src/constants/worldThemes.ts:100` 到 `frontend/src/constants/worldThemes.ts:105`。

直接后果：

- AI 返回的大多数 `bgm_suggestion` 不会被前端采用。
- 当前只有 `silent` 是稳定交集。

### 5.2 prompt builder 的枚举也有漂移

`WorldSettingModule` 里把 `theme_preset` 映射为：

```text
academy / library / laboratory / mountain_academy / cyberspace / blank
```

见 `backend/services/prompt_builder/modules/world_setting.py:55` 到 `backend/services/prompt_builder/modules/world_setting.py:64`。

这和前端的 `lab / mountain / cyber` 也不一致。

因此，即使 `scenes` 成功落库，运行时 prompt 也可能显示原始 key，而不是稳定的中文世界风格。

但从当前整理后的方向看，这一整组 theme / mood / bgm 字段都属于待收缩字段，而不是待增强字段。

## 6. 当前 runtime 消费情况

当前世界生成出来的字段，理论上会被以下地方消费。

### 6.1 学习 prompt 的世界氛围

`WorldSettingModule` 读取：

- `world.name`
- `world.description`
- `scenes.mood`
- `scenes.theme_preset`
- `scenes.bgm`

见 `backend/services/prompt_builder/modules/world_setting.py:36` 到 `backend/services/prompt_builder/modules/world_setting.py:77`。

它不读取 `background_picture` 这种更贴近世界壳语义的字段，也没有把 `world.description` 当成世界壳主说明来使用。

### 6.2 角色进入世界时的上下文生成

`_world_context_for_character_generation()` 读取：

- `world.name`
- `world.description`
- `scenes.mood`
- `scenes.theme_preset`
- `scenes.world_detail`
- `scenes.background`
- `scenes.narrative`
- `scenes.narrative_input`

见 `backend/api/routes/archive.py:277` 到 `backend/api/routes/archive.py:306`。

这说明当前代码把“世界舞台说明”错误地放进了 `scenes.world_detail`，而不是稳定地放在 `World.description`。

### 6.3 前端学习页背景

`frontend/src/stores/learning.ts` 只读取：

- `data.scenes?.background`

见 `frontend/src/stores/learning.ts:176`。

`frontend/src/types/learning.ts` 也只声明：

- `background`
- `menu_background`

见 `frontend/src/types/learning.ts:80`。

因此当前世界生成里的大部分字段对学习页 UI 基本不可见。真正和世界壳有关、且前端应该长期稳定消费的，其实只有默认背景图。

### 6.4 World 类型本身也缩得太窄

`frontend/src/types/world.ts` 里 `World.scenes` 只声明了：

- `background`
- `menu_background`

见 `frontend/src/types/world.ts:15` 到 `frontend/src/types/world.ts:23`。

这和真实的世界创建 payload 不一致。`CreateWorldModal` 生成的是更丰富的 `scenes`，但 `World` 类型没有表达这些字段，导致类型层也在压缩信息。

## 7. 当前文档与代码的漂移

旧文档 `docs/v1.0.4/ai_world_generate.md` 现在已经不能当作当前代码的准确说明。

主要漂移点：

- 旧文档 response 写的是 `scene_description`，当前代码返回 `world_detail`。
- 旧文档写 `worldApi.generate(description, inspirationType)`，当前代码是 `worldApi.generateWorld(description)`。
- 旧文档写 `inspiration_type` 会传给后端，当前前端没有传，后端也没有使用。
- 旧文档里的 theme / bgm 枚举和当前前后端常量都不完全一致。

这篇旧文档仍有历史价值，但不应该作为 v1.0.4 的实现依据。

## 8. 现有基础设施其实已经够用

当前不需要先做大重构。已有基础设施包括：

- 后端 `WorldCreate.scenes` 已经能接字段。
- 后端 `create_world()` 已经能存 `scenes`。
- 前端 `CreateWorldModal` 已经能组装 `scenes`。
- `PromptBuilder` 已经有 `WorldSettingModule`。
- 世界角色上下文生成已经能读取世界说明，但当前是从 `world_detail` 这条旧路径读取。

所以第一阶段应该做的是打通链路和收敛契约，而不是发明新的世界编译器。

## 9. 当前世界生成的真实问题清单

按优先级排序：

1. `CreateWorldModal` 已经生成 `scenes`，但 `Worlds.vue` 创建世界时丢掉了。
2. `worldApi.create()` 类型只允许 `name / description`，和后端 `WorldCreate.scenes` 不一致。
3. `WorldDetail.vue` 编辑世界不提交 `scenes`，后端 `update_world()` 会把 `scenes` 覆盖成 `{}`。
4. 后端 prompt、前端常量、`WorldSettingModule` 三套 theme / bgm 枚举不一致。
5. `inspiration_type` 是死字段：schema 有，前端不传，后端不用。
6. 世界舞台说明没有稳定地落在 `World.description`，而是绕进了 `scenes.world_detail` 旧路径。
7. 前端类型把 `World.scenes` 缩成了 `background/menu_background`，没有表达真实 payload。
8. 旧世界生成文档与当前代码不一致。
9. 当前课程编排草图字段叫 `world_plan`，语义上误导成“世界计划”，但它实际上是课程叙事结构。
10. `LearningPlanDraft -> commit_learning_plan_draft()` 是一条旁路，不再符合当前主产品流程。

## 10. 建议的完善方向

这部分仍然不是代码方案，只是下一步实现时的边界。

### 10.1 世界生成只做世界壳

世界生成阶段只生成并保存：

- `World.name`
- `World.description`
- `World.background_picture`

不生成：

- 课程剧情。
- 教学事件池。
- 复习事件池。
- 角色关系主线。
- 章节映射。

### 10.2 课程创建再生成叙事结构

课程创建 pipeline 的顺序应该固定为：

1. 根据教材知识结构生成课程教学结构。
2. 引入角色。
3. 根据世界壳和角色生成课程叙事结构。

这一步的输入是：

- 已有 `World`
- 根据教材推导出的课程教学结构
- 已导入人物

输出应该指向课程侧，而不是回写到世界壳：

- `Course.meta`
- `LessonPlan`
- `CourseProgress`
- `WorldCharacter`
- 或课程作用域下的叙事字段

文档层推荐名称：

- 当前代码名：`world_plan`
- 目标语义名：`course_narrative_plan`

但不应该在单独创建 `World` 时提前生成。

### 10.3 教材优先 draft 旁路应退出主流程

当前 `LearningPlanDraft` 和 `commit_learning_plan_draft()` 形成了一条“教材优先直接 commit 世界和课程”的旁路。

从当前产品定义看，这条路径应该退出主流程，原因很明确：

- 它绕过了“先建世界壳，再进世界创建课程”的交互顺序。
- 它把课程叙事草图错误写进 `World.scenes`。
- 它让世界创建和课程创建再次耦合。
- 它让 `world_plan` 这种误导性命名继续扩散。

### 10.4 先打通，不重构

第一阶段只需要验证这些验收条件：

1. AI 生成后，创建世界能把 `scenes` 完整写入数据库。
2. `GET /worlds/{id}` 能回读同样的 `scenes`。
3. 编辑世界名称/描述不会清空 `scenes`。
4. 世界壳字段收敛到 `World.description + World.background_picture`。
5. `inspiration_type` 要么真正使用，要么从世界生成入口移除。
6. 世界生成不会创建课程、人物、剧情。
7. 课程叙事结构只从“课程教学结构 + 世界壳 + 角色”派生。
8. `LearningPlanDraft -> commit_learning_plan_draft()` 不再作为产品主路径。

如果这 8 条完成，世界生成作为“世界壳生成”就算稳定了。后续再进入课程创建主导的课程叙事生成。
