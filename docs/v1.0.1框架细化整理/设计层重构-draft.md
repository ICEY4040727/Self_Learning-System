# 设计层重构计划

> **状态**: APPROVED — 三方讨论已确认，可执行。已整合到 [联调重构执行指南](./37-联调重构执行指南.md)
> **提出者**: Creator
> **审阅者**: Reviewer（附条件 APPROVE D1）
> **日期**: 2026-04-14
> **关联文档**: [联调重构执行指南](./37-联调重构执行指南.md) | [前后端联调重构计划-draft](./前后端联调重构计划-draft.md) | [问题汇总索引](./00-问题汇总索引.md)

---

## 1. 背景

联调重构执行指南（#37）覆盖了 28 项代码层面的清理和重构，但在审查过程中发现**角色数据模型**和 **Prompt 组装器**存在更深层的设计问题，这些问题如果不先敲定，部分重构操作（尤其是 #31 角色模板合并、#15 key 统一）的方向会不确定。

### 1.1 当前角色数据流

```
前端创建流程 → Character 表 → TeacherPersona 表 → PromptBuilder 组装 system_prompt → LLM
```

但实际存在**两套并行的前端创建流程**和**两套常量定义**：

| 创建流程 | 文件 | 步骤数 | 数据源 |
|----------|------|--------|--------|
| SageCreateFlow | `SageCreateFlow.vue` | 5 步 | `characterPresets.ts` |
| CreatePersonaModal | `CreatePersonaModal.vue` | 3 步 | `personaTemplates.ts` |

### 1.2 PromptBuilder 组装现状

```python
# PromptBuilder.build_static_layer() 的拼装逻辑：
1. 从 TeacherPersona → 获取 character_id
2. 从 Character 表 → 读取 name, background, personality, speech_style, tags
3. 从 TeacherPersona → 读取 traits (strictness, pace, questioning, warmth, humor)
4. 硬编码 → 苏格拉底式提问规则 + Mermaid 规则
5. 可选 → Traveler 角色信息
```

**问题**：角色身份信息分散在两个模型中，模板仅影响前端 UI 预填值、不影响 Prompt 生成。

---

## 2. 设计问题（22 项，分为 8 个集群）

> D1-D7 为主线决策（§2 集群 A-D），D8-D13 为补充发现（§5.6），D14-D22 为子系统审查发现（§5.7）。

### 集群 A：数据模型职责（D1）

#### D1: Character vs TeacherPersona — 双模型的职责边界

**现状**：

| 模型 | 存储字段 | 定位 |
|------|---------|------|
| `Character` | name, type, personality, background, speech_style, tags, sprites, avatar, level, experience_points | 角色身份 |
| `TeacherPersona` | character_id(FK), traits(JSON), system_prompt_template, is_active | 人格配置 |

**问题**：
- `traits`（性格参数）存在 TeacherPersona 而不是 Character 中，但前端创建时 traits 是 Character 的一部分
- 一个 Character 理论上可以有多个 TeacherPersona（多套人格），但当前代码从未利用这个关系
- PromptBuilder 需要同时读取两个表，增加了复杂度

**选项**：

| 选项 | 描述 | 改动量 | 风险 |
|------|------|--------|------|
| **A** | 保持双模型，明确语义文档化 | 低 | 低 |
| **B** | traits 移到 Character，TeacherPersona 仅保留 system_prompt_template | 中 | 中 |
| **C** | 保持现状，在 PromptBuilder 中统一入口，减少分散读取 | 低 | 低 |

---

### 集群 B：前端创建流程（D2, D7）

#### D2: 两个 Sage 创建流程 — 哪个是正式的？

**现状对比**：

| 维度 | SageCreateFlow (5步) | CreatePersonaModal (3步) |
|------|---------------------|------------------------|
| 数据源 | `characterPresets.ts` | `personaTemplates.ts` |
| 模板 key | `socratic` ❌ | `socrates` ✅ |
| 灵感来源 | 模板 / AI生成 / 自定义 | 模板 + AI生成 |
| 外观定制 | 名称、称号、主题色 | 名称、称号、头像符号、颜色 |
| 性格设定 | 5滑块 + 说话风格标签 | 5滑块 + 描述文本 |
| 背景故事 | ✅ 独立步骤 | ❌ |
| 预览 | 含初见台词 | 含性格条形图 |
| 使用场景 | WorldDetail 页面内嵌 | 弹窗 Modal |

两个流程产出不同结构的 payload，都声称创建 sage 角色。

**选项**：

| 选项 | 描述 | 改动量 | 风险 |
|------|------|--------|------|
| **A** | 统一到 SageCreateFlow（功能更丰富） | 中 | 低 |
| **B** | 统一到 CreatePersonaModal（更简洁） | 中 | 低 |
| **C** | 保留两个但明确分工：SageCreateFlow=深度创建，CreatePersonaModal=快速创建 | 低 | 中（维护两套常量） |

#### D7: 重复的 TRAIT_SLIDERS 定义

**现状**：

| 文件 | 接口 | 特点 | 默认值 |
|------|------|------|--------|
| `characterPresets.ts` | `TraitSlider {key, label, leftLabel, leftExample, rightLabel, rightExample, defaultValue}` | 详细（含示例文本） | strictness=3, pace=5, questioning=7, warmth=6, humor=4 |
| `personaTemplates.ts` | `TraitSlider {key, name, min, max, default, minLabel, maxLabel}` | 简化 | strictness=5, pace=5, questioning=5, warmth=6, humor=4 |

5 个 slider key 相同，但接口定义不同、部分默认值不同。

**选项**：

| 选项 | 描述 |
|------|------|
| **A** | 统一到 `characterPresets.ts`（保留详细版本） |
| **B** | 抽取到独立文件 `constants/traitSliders.ts` |
| **C** | 随创建流程统一而自然解决（如果只保留一个创建流程） |

---

### 集群 C：Prompt 生成策略（D4, D5）

#### D4: 苏格拉底规则硬编码 — 是否应该按模板差异化？

**现状**：`PromptBuilder.build_static_layer()` 中，"苏格拉底式提问"规则是**硬编码**的：

```python
parts.append("""【教学方法——苏格拉底式提问】
1. 绝不直接给出答案。通过一连串由浅入深的问题引导学习者自己发现答案。
...
""")
```

无论用户选择了什么模板（爱因斯坦型、孙子型、尤达型……），所有老师都使用**完全相同**的教学规则。模板仅影响前端的 greeting 和预填值，**不影响 Prompt**。

**选项**：

| 选项 | 描述 | 效果 |
|------|------|------|
| **A** | 保持硬编码（所有老师用苏格拉底方法） | 产品一致性最高 |
| **B** | 按模板差异化（每个模板有独立教学规则） | 体验多样性，但维护成本高 |
| **C** | 基础规则 + 模板扩展（苏格拉底规则为底，每个模板追加风格指令） | 平衡一致性和多样性 |

#### D5: `template_name` 是否应持久化并影响 Prompt？

**现状**：
- 前端创建 Character 时传了 `template_name` 字段（如 `'socrates'`、`'einstein'`）
- 但后端 `Character` 模型**没有** `template_name` 列
- `PromptBuilder` **不读取**任何模板信息
- 模板仅用于前端 UI 默认值（greeting、icon、预填 traits）

**选项**：

| 选项 | 描述 | 改动量 |
|------|------|--------|
| **A** | 不持久化（现状） | 无 |
| **B** | 持久化到 Character（加 `template_name` 列），PromptBuilder 据此调整策略 | 中 |
| **C** | 持久化但不影响 Prompt（仅 UI 展示和统计） | 低 |

---

### 集群 D：数据存储细节（D3, D6）

#### D3: 模板 Key 命名 — `socratic` vs `socrates`

> 与联调重构计划 D3 关联，该决策已确认统一为 `socrates`，但此处补充设计层讨论。

**分析**：

| 维度 | `socrates` | `socratic` |
|------|-----------|-----------|
| 含义 | 人名（哲学家苏格拉底） | 方法论名（苏格拉底式教学法） |
| 语义 | "以苏格拉底为原型的角色" | "采用苏格拉底方法的教学风格" |
| 后端 | ✅ 已支持作为主 key | ❌ 无此 key |
| personaTemplates.ts | ✅ 使用 | ❌ |
| characterPresets.ts | ❌ | ✅ 使用 |

**选项**：
- **统一为 `socrates`**（与联调计划 D3 一致）：修改 `characterPresets.ts`
- **统一为 `socratic`**：修改 `personaTemplates.ts` + 后端

#### D6: `speech_style` 存储方式

**现状**：
- SageCreateFlow 中用户选择多个"说话风格"标签（如 `['文白夹杂', '爱讲故事', '偶尔吐槽']`）
- 提交时作为 `speechStyles` 数组
- 但 Character 模型中 `speech_style` 是 `Column(Text)`（单字符串）
- PromptBuilder 读取后直接拼接 `"说话风格: {speech_style}"`

**选项**：

| 选项 | 描述 | 改动量 |
|------|------|--------|
| **A** | `speech_style` 改为 `Column(JSON)` 存标签数组，PromptBuilder join 后拼接 | 中（需迁移脚本） |
| **B** | 保持 Text，前端 join 后提交（存 `"文白夹杂、爱讲故事、偶尔吐槽"`） | 低 |
| **C** | 合并到 tags 字段（speech_style 标签和特质标签统一） | 中 |

---

## 3. 重构方案（3 个 Phase）

### Phase 0 — 数据模型确认
> **前置条件**: 无 | **预估工作量**: 0.5 天 | **风险**: 低

**任务**:
- [ ] D1 确认 Character / TeacherPersona 职责边界
- [ ] D5 决定 `template_name` 是否持久化
- [ ] D6 决定 `speech_style` 存储方式
- [ ] 如需改表结构：编写 Alembic migration 脚本

**验收**: 模型变更后 `pytest` 通过 + `alembic upgrade head` 成功

---

### Phase 1 — 前端创建流程统一
> **前置条件**: Phase 0 完成 | **预估工作量**: 1-2 天 | **风险**: 中

**任务**:
- [ ] D2 确定保留哪个创建流程
- [ ] D3 统一模板 key 为 `socrates`（或 `socratic`）
- [ ] D7 合并 TRAIT_SLIDERS 为一份定义
- [ ] 更新所有引用：SageCreateFlow / CreatePersonaModal / WorldDetail / Character 页面

**验收**:
- `npm run build` 通过，无 TS 错误
- `grep -r "socratic" frontend/src/` 零结果（如果统一为 socrates）
- 角色创建端到端测试通过

---

### Phase 2 — Prompt 生成策略优化
> **前置条件**: Phase 0 + Phase 1 完成 | **预估工作量**: 1-2 天 | **风险**: 中

**任务**:
- [ ] D4 确认苏格拉底规则策略（硬编码 / 差异化 / 基础+扩展）
- [ ] 如选差异化或基础+扩展：
  - [ ] 在后端定义模板→教学规则的映射
  - [ ] PromptBuilder 根据模板 key（或 Character 属性）选择规则
- [ ] 如 `template_name` 持久化（D5-B）：PromptBuilder 增加模板感知逻辑

**验收**:
- `pytest backend/tests/test_prompt_builder.py` 通过
- 不同模板角色的 system_prompt 有可观测的差异（如果选择了差异化）

---

## 4. 执行依赖图

```
Phase 0 (数据模型确认) ──→ Phase 1 (前端创建流程统一) ──→ Phase 2 (Prompt 策略优化)
```

Phase 0 是纯设计决策（可能含表结构变更），Phase 1 依赖数据模型确定，Phase 2 依赖模板系统确定。

与联调重构计划的关系：
- 本计划的 Phase 0 应在联调 Phase 3（前后端联调）之前完成
- 本计划的 Phase 1 与联调 Phase 3 §3.7（角色模板合并）合并执行
- 本计划的 Phase 2 可在联调 Phase 4 之后独立执行

---

## 5. 需要三方讨论的决策点

### ⚖️ 决策 1 (D1): Character vs TeacherPersona 职责边界

- **选项 A**: 保持双模型，文档化语义（Character=身份，TeacherPersona=人格配置）
- **选项 B**: traits 移到 Character，TeacherPersona 仅保留 system_prompt_template
- **选项 C**: 保持现状，PromptBuilder 统一入口

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 A（保持双模型，文档化） | B 的收益（traits 移到 Character）不足以抵消数据迁移风险；当前 PromptBuilder 从两个表读取的模式已经稳定工作；建议在代码注释中明确 Character=角色身份、TeacherPersona=人格配置的语义边界 |
| **Reviewer** | ✅ APPROVE（附条件） | 同意合并方向，但要求：1) `is_active` 语义需文档化（是"可用于教学"还是"哪个配置活跃"）；2) Alembic 迁移必须独立 PR + 回滚脚本，且在联调 Phase 0 之前执行；3) 验收加 `grep -r "TeacherPersona" backend/ --include="*.py"` 零结果 |
| **Owner** | ✅ **选 D（完全删除 TeacherPersona，合并到 Character）** | 将 traits、system_prompt_template 全部移入 Character 表；减少模型复杂度和跨表查询；需 Alembic 迁移 + 回滚脚本 |

**⚠️ D1 变更影响评估**（Owner 选择的完全合并方案）：

| 影响项 | 说明 |
|--------|------|
| Character 表新增列 | `traits`(JSON), `system_prompt_template`(Text), `is_active`(Boolean) |
| TeacherPersona 相关代码 | `learning.py` 中 `_get_session_characters()`、`_build_start_response()` 需重写 |
| Session 模型 | `teacher_persona_id` FK 改为直接引用 `character_id` |
| PromptBuilder | 简化为仅从 Character 读取，删除跨表逻辑 |
| 需要迁移脚本 | Alembic: 将 TeacherPersona 数据迁入 Character，然后 DROP TABLE teacher_personas |
| 风险 | **中高** — 涉及核心模型变更，需充分测试 |

</details>

---

### ⚖️ 决策 2 (D2): Sage 创建流程统一

- **选项 A**: 统一到 SageCreateFlow（5步，功能更丰富）
- **选项 B**: 统一到 CreatePersonaModal（3步，更简洁）
- **选项 C**: 保留两个，明确分工

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 A（统一到 SageCreateFlow） | 1) 功能更丰富：有 background 步骤、greeting 初见台词、speechStyles 多选——这些字段后端 Character 表已有对应列；2) CreatePersonaModal 缺少 background 和 speech_style 数据，统一到它会导致数据丢失；3) 删除 CreatePersonaModal 后 WorldDetail 页面可用 SageCreateFlow 替代 |
| **Reviewer** | ✅ APPROVE | SageCreateFlow 功能更完整，背景故事和说话风格是差异化数据，删除 CreatePersonaModal 可消除双常量维护负担 |
| **Owner** | A | |

</details>

---

### ⚖️ 决策 3 (D3): 模板 Key 命名

- **选项**: 统一为 `socrates`（与联调计划 D3 一致）或 `socratic`

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ `socrates`（与联调计划一致） | 后端已支持，改动最小 |
| **Reviewer** | ✅ APPROVE | 三方一致，无异议 |
| **Owner** | socrates | |

</details>

---

### ⚖️ 决策 4 (D4): 苏格拉底规则策略

- **选项 A**: 硬编码（所有老师统一苏格拉底方法）
- **选项 B**: 按模板差异化
- **选项 C**: 基础苏格拉底规则 + 模板扩展风格指令

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 C（基础规则 + 模板扩展） | 当前所有模板的 Prompt 完全相同 = 零差异化，用户选了"爱因斯坦型"但 LLM 仍按苏格拉底方法教学，这是产品层面的浪费；C 方案：苏格拉底提问法作为通用基础规则，每个模板追加 2-3 条风格指令（如爱因斯坦型追加"多用类比和思想实验"），改动量可控 |
| **Reviewer** | ✅ APPROVE | D4=C 与 D5=B 联动关系正确：基础规则+扩展必须知道模板 key，template_name 持久化是前置条件 |
| **Owner** | C | |

</details>

---

### ⚖️ 决策 5 (D5): template_name 持久化

- **选项 A**: 不持久化（现状）
- **选项 B**: 持久化到 Character，影响 Prompt
- **选项 C**: 持久化但不影响 Prompt

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 C（持久化但不影响 Prompt） | 为 D4 的模板差异化打基础——如果选了 C（基础+扩展），PromptBuilder 需要知道角色的模板来源；当前不影响 Prompt 行为，风险最低；设为 nullable 列，已有角色为 null 不影响 |
| **Reviewer** | ✅ APPROVE（同意 Owner 的 B 方案） | D4=C 需要 PromptBuilder 感知模板，所以 B（持久化且影响 Prompt）逻辑更自洽 |
| **Owner** | ✅ **选 B（持久化到 Character，影响 Prompt）** | D4 选了 C（基础规则+模板扩展），PromptBuilder 需要知道模板 key 才能追加风格指令；template_name 持久化为 Character 新列 |

</details>

---

### ⚖️ 决策 6 (D6): speech_style 存储方式

- **选项 A**: 改为 JSON 数组
- **选项 B**: 保持 Text，前端 join
- **选项 C**: 合并到 tags

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 B（保持 Text，前端 join） | 避免数据库迁移（JSON 列需 Alembic migration + 回滚脚本）；已有数据兼容性最好（可能为空或单字符串）；前端在提交时 `speechStyles.join('、')` 即可，改动量最小 |
| **Reviewer** | ✅ APPROVE | 三方一致，无异议 |
| **Owner** | B | |

</details>

---

### ⚖️ 决策 7 (D7): TRAIT_SLIDERS 统一

- **选项 A**: 统一到 characterPresets.ts
- **选项 B**: 抽取到 constants/traitSliders.ts
- **选项 C**: 随创建流程统一自然解决

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 B（抽取到 constants/traitSliders.ts） | 干净分离，不依赖 D2 创建流程统一的结论；即使保留两个创建流程，它们也可以共用同一份 TRAIT_SLIDERS 定义；合并接口时保留详细版本（含 leftExample/rightExample），默认值统一为 strictness=5, pace=5, questioning=5, warmth=6, humor=4 |
| **Reviewer** | ✅ APPROVE | 三方一致，无异议 |
| **Owner** | ✅ **选 B（抽取到 constants/traitSliders.ts）** | 确认独立文件方案 |

</details>

---

## 5.5 技术调查

### 📋 D1: Character 与 TeacherPersona 字段分布

| 数据 | Character | TeacherPersona | PromptBuilder 使用 |
|------|:---------:|:--------------:|:------------------:|
| name | ✅ | ✅(冗余) | ✅ `"你是 {name}"` |
| personality | ✅ | ❌ | ✅ `"性格特点: {personality}"` |
| background | ✅ | ❌ | ✅ 直接注入 |
| speech_style | ✅ | ❌ | ✅ `"说话风格: {speech_style}"` |
| tags | ✅ | ❌ | ✅ `"角色特质: {tags}"` |
| traits (5维) | ❌ | ✅ | ✅ `"性格参数 0-10 ..."` |
| system_prompt_template | ❌ | ✅ | ✅ 降级方案使用 |
| avatar | ✅ | ❌ | ❌ 不注入 Prompt |
| sprites | ✅ | ❌ | ❌ 不注入 Prompt |
| is_active | ❌ | ✅ | ❌ 仅查询条件 |

**关键发现**：
- PromptBuilder 从 Character 读取 5 个字段，从 TeacherPersona 读取 1 个字段（traits）
- traits 是 TeacherPersona 唯一对 Prompt 有贡献的字段
- 如果 traits 移到 Character，PromptBuilder 可完全从 Character 读取

### 📋 D2: 两个创建流程的 Payload 对比

**SageCreateFlow 提交的 payload**:
```javascript
{
  type: 'sage',
  name: form.name,
  title: form.title,
  background: form.background,
  personality: form.personality,
  colorKey: form.colorKey,       // ← 仅此流程有
  traits: { ...form.traits },
  speechStyles: [...],           // ← 数组，需处理
  template_name: selectedTemplate,
  greeting: getGreeting(),       // ← 仅此流程有
}
```

**CreatePersonaModal 提交的 payload**（经 `buildCharacterPayload` 转换）:
```javascript
{
  name: form.name,
  type: 'sage',
  avatar: form.avatar,           // ← 符号头像
  title: form.title,
  tags: template?.traits || [],  // ← 来自模板预设
  template_name: form.templateKey,
  traits: form.traits,
  personality: form.description,
}
```

**差异字段**:

| 字段 | SageCreateFlow | CreatePersonaModal | 后端是否接收 |
|------|---------------|-------------------|------------|
| background | ✅ | ❌ | ✅ Character 有此列 |
| colorKey | ✅ | ❌ | ❌ Character 无此列 |
| speechStyles | ✅ (数组) | ❌ | ❌ 需映射到 speech_style |
| greeting | ✅ | ❌ | ❌ Character 无此列 |
| tags | ❌ | ✅ (从模板) | ✅ Character 有此列 |
| avatar | ❌ | ✅ (符号) | ✅ Character 有此列 |

### 📋 D4: 当前模板对 Prompt 的实际影响（= 零）

| 模板 | greeting | traits 默认值 | Prompt 教学规则 | Prompt 风格 |
|------|---------|-------------|---------------|------------|
| 苏格拉底型 | "我知道我一无所知..." | strictness=3, questioning=7 | 苏格拉底式提问 | 不变 |
| 爱因斯坦型 | "想象力比知识更重要..." | (未定义默认) | 苏格拉底式提问 | 不变 |
| 孙子型 | "知己知彼..." | (未定义默认) | 苏格拉底式提问 | 不变 |
| 尤达型 | "尝试，不尝试..." | (未定义默认) | 苏格拉底式提问 | 不变 |

**结论**：模板 key 仅影响前端 UI 展示，对 LLM 行为**零影响**。用户选了"爱因斯坦型"但 LLM 仍按苏格拉底方法教学。

---

## 5.6 补充发现（Creator 审查）

### 📋 额外设计问题（D8-D13）

在深入审查 PromptBuilder、前端常量和数据模型后，发现以下额外问题：

#### D8: `greeting` 字段未持久化

**现状**：
- `characterPresets.ts` 每个模板定义了 `greeting`（初见台词），如 "我知道我一无所知。让我们一起来探索真理吧。"
- `SageCreateFlow` 提交时包含 `greeting` 字段
- 但 `Character` 和 `TeacherPersona` 表均无 `greeting` 列
- `learning.py` 的 `_get_greeting()` 使用的是**硬编码的 stage-based greeting**，与模板无关
- **用户自定义的 greeting 在创建后丢失**

**选项**：
- **A**: 在 Character 表加 `greeting` 列，PromptBuilder 在首次对话时注入
- **B**: 不持久化，但 `_get_greeting()` 从 Character.personality 等字段动态生成
- **C**: 不持久化（现状），greeting 仅在前端 UI 预览时使用

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 A（持久化 greeting） | 用户花时间自定义了初见台词，创建后丢失是数据浪费；加一个 nullable Text 列即可，改动量低；PromptBuilder 在首次对话时注入 greeting 可显著提升首次体验 |
| **Reviewer** | ✅ 同意 Owner（删除 greeting） | greeting 作为独立字段的价值不大，可与 D1 合并处理减少迁移复杂度；如果需要"初见台词"功能，可以从 personality/background 动态生成 |
| **Owner** | 直接删除greeting | |

</details>

---

#### D9: `tags` vs `traits` 命名混淆

**现状**：
- `personaTemplates.ts` 每个模板有 `traits` 字段，值是**字符串标签数组**：`['耐心', '追问型', '启发型']`
- `buildCharacterPayload()` 将模板的 `traits` 映射到 payload 的 `tags` 字段
- `TRAIT_SLIDERS` 也叫 "traits"，但值是**数值参数**（0-10）
- Character 表有 `tags` 列（字符串数组）和 TeacherPersona 表有 `traits` 列（数值对象）
- **同一个词 "traits" 在不同上下文中指代完全不同的数据**

**影响**：开发时极易混淆，需要每次都澄清是"标签型 traits"还是"数值型 traits"。

**建议**：在合并时统一术语，如：
- 模板的字符串标签 → `tags`（与 DB 一致）
- 数值参数 → `trait_params` 或 `personality_params`

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 统一术语 | 建议模板字符串标签 → `tags`，数值参数 → `trait_params`；这个改动是纯粹的变量重命名，零风险，但能显著减少后续开发时的认知负担 |
| **Reviewer** | ✅ APPROVE | 术语统一是零风险高收益改动，三方一致 |
| **Owner** | 尽快改 | |

</details>

---

#### D10: 两套颜色系统不兼容

**现状**：
| 文件 | 变量 | 格式 | 示例 |
|------|------|------|------|
| `characterPresets.ts` | `CHARACTER_COLORS` | `{key, color(rgba), name}` | `{key:'gold', color:'rgba(245,158,11,0.6)', name:'金色'}` |
| `personaTemplates.ts` | `COLOR_OPTIONS` | hex 字符串 | `'#ffd700'` |

- `SageCreateFlow` 用 `form.colorKey`（键名：`gold`/`purple`/...）
- `CreatePersonaModal` 用 `form.color`（hex 值：`#ffd700`/`#f59e0b`/...）
- Character 表**无 color 列**——两套颜色都无法持久化

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 建议统一为 hex + 加 color 列 | hex 更通用、CSS 原生支持；如果 D2 统一到 SageCreateFlow，可在 Character 表加 `theme_color` nullable 列；当前优先级低，可在 Phase 4 处理 |
| **Reviewer** | ✅ APPROVE | 低优先级，同意 Creator 方案 |
| **Owner** | 可以按照creator | |

</details>

---

#### D11: 模板列表不一致

**现状**：
| 模板 | `characterPresets.ts` | `personaTemplates.ts` |
|------|:--------------------:|:--------------------:|
| 苏格拉底型 | ✅ (key=`socratic`) | ✅ (key=`socrates`) |
| 爱因斯坦型 | ✅ | ✅ |
| 亚里士多德型 | ✅ | ✅ |
| 孙子型 | ✅ | ✅ |
| 尤达型 | ✅ | ❌ |
| 自由奔放型 | ✅ | ❌ |
| 自定义 | ❌ | ✅ |

两个文件的模板列表有差异。如果合并创建流程，需要决定最终包含哪些模板。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 建议合并为 5 个模板 | 保留：苏格拉底型、爱因斯坦型、亚里士多德型、孙子型、尤达型；删除"自由奔放型"（与自定义重复）和"自定义"（统一走 SageCreateFlow 的自定义模式即可）；如果 D2 统一到 SageCreateFlow 则以 `characterPresets.ts` 为基准 |
| **Reviewer** | ✅ 同意 Creator 的 5 模板方案 | 但要求每个模板必须有完整的 `style_extensions`（D4=C 的风格指令），不能只有名称和 greeting |
| **Owner** | reviewer有更好的方案吗 | |

</details>

---

#### D12: PromptBuilder 的 `knowledge_svc` 参数误用

**现状**（`builder.py` 第 80-111 行）：
```python
def __init__(self, knowledge_svc=None, relationship_svc=None):
    self.knowledge = knowledge_svc
    ...

def _get_character_from_persona(self, teacher_persona, db=None):
    ...
    # 否则通过 self.knowledge 获取（如果它是 db session）
    if hasattr(self.knowledge, 'query'):
        return self.knowledge.query(Character)...
```

`knowledge_svc` 参数名为"知识服务"，但实际被当作 DB session 使用。这是历史遗留代码，应在重构中修正。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 重命名为 `db` | 纯参数重命名，零功能变更；在 PromptBuilder 重构时一并清理，与 D1 联动 |
| **Reviewer** | ✅ APPROVE | 零风险改动，三方一致 |
| **Owner** | 尽快修复 | |

</details>

---

#### D13: `prev_emotion` 始终为 None

**现状**（`learning_engine.py` 第 157 行）：
```python
context = {
    ...
    "prev_emotion": None,  # ← 硬编码为 None
    ...
}
```

虽然紧接着（第 170-177 行）查询了上一条用户消息的 emotion_analysis，但结果**从未使用**（`if last_user_msg and last_user_msg.emotion_analysis: pass`）。这意味着 `ScaffoldContext` 的 `prev_emotion` 永远是空值，脚手架等级计算基于默认值而非真实情感。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🔴 高优先级修复 | 这是一个功能缺陷而非设计问题；代码已经查询了 emotion_analysis，只是 `pass` 不使用；修复只需将 `prev_emotion: None` 改为 `prev_emotion: last_user_msg.emotion_analysis`，改动量 1 行；建议在联调 Phase 0（死代码清除）中一并修复 |
| **Reviewer** | ✅ APPROVE（🔴 同意高优先级） | 明确的 bug，代码查了数据但不用，1 行修复 |
| **Owner** | 尽快修复 | |

</details>

---

### 📋 问题优先级排序

| 问题 | 影响 | 优先级 | 建议 |
|------|------|--------|------|
| D13 prev_emotion 始终 None | **高** — 脚手架自适应功能失效 | 🔴 高 | 在联调 Phase 0 或 Phase 3 修复 |
| D9 tags/traits 命名混淆 | **中** — 开发混淆，可能导致 bug | 🟡 中 | 在合并模板时统一术语 |
| D8 greeting 未持久化 | **中** — 用户自定义台词丢失 | 🟡 中 | 与 D2 创建流程合并考虑 |
| D10 颜色系统不兼容 | **低** — 当前无法持久化颜色 | 🟢 低 | 与 D2 创建流程合并考虑 |
| D11 模板列表不一致 | **低** — 需决定最终列表 | 🟢 低 | 与 D3 key 统一合并处理 |
| D12 knowledge_svc 误用 | **低** — 代码可读性 | 🟢 低 | PromptBuilder 重构时清理 |

---

## 5.7 系统性子系统审查发现（D14-D22）

> Creator 对 7 个子系统进行深度审查后发现的额外设计问题。

### 集群 E：记忆系统设计

#### D14: Seed Memory 重复创建

**现状**：`learning_engine.py` 每次 `start_learning()` 创建新 session 时调用 `create_seed_memories()`。同一个 sage character 被多次用于新 session 时，seed memories 重复写入，无去重检查。

**影响**：sage 的记忆中会有多条 "学生名叫 XXX" 的重复事实。

**建议**：在 `create_seed_memories()` 中增加去重检查 — 按 `(sage_character_id, fact_type, content)` 查询是否已存在。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🟡 中优先级 | seed memory 应该是"首次创建，后续跳过"的语义；加一个 SELECT 1 去重检查即可，改动量约 10 行 |
| **Reviewer** | ⚠️ 同意 Owner（不去重），但需文档化语义 | 如果不去重，应明确 seed memory 是 "per-session seeding" 语义；建议加 `source_session_id` 标记来源，方便后续按需清理重复事实 |
| **Owner** | 每个新session都可能有不同的seedmemory,不需要去重 | |

</details>

---

#### D15: 记忆召回计数从未更新

**现状**：`memory_facts_service.update_recall_count()` 方法存在但从未被调用。`MemoryFact.recall_count` 始终为 0，`last_recalled_at` 始终等于 `created_at`。

**影响**：无法实现"遗忘曲线"（遗忘曲线依赖召回次数和时间间隔）。

**建议**：在 `MemoryFactsModule.format()` 检索记忆后，调用 `update_recall_count()` 更新召回计数和最后召回时间。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🟡 中优先级 | 是记忆系统完整性的关键环节；改动量约 5 行 |
| **Reviewer** | ✅ APPROVE | 改动量小，对遗忘曲线实现必要 |
| **Owner** | 可以 | |

</details>

---

#### D16: fact_type 枚举双重维护

**现状**：`memory_facts.py` 定义 `FACT_TYPE_*` 类属性；`memory_extractor.py` L132 硬编码 `valid_types = {...}` 集合。两个来源需手动同步。

**建议**：统一为 Python Enum 或从 `memory_facts.py` 导入常量。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🟢 低优先级 | 纯代码卫生问题，不影响功能 |
| **Reviewer** | ✅ APPROVE | 三方一致，统一为枚举 |
| **Owner** | 尽快统一 | |

</details>

---

### 集群 F：LLM 适配层设计

#### D17: 4 个 Adapter 类大量重复代码

**现状**：`adapter.py` 1043 行，4 个 Adapter 中消息格式转换、SSE 流解析、错误处理高度重复。

**建议**：提取 `BaseOpenAIStyleAdapter` 基类，预估减少 ~300 行。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🟡 中优先级 | 维护成本高但当前功能正常；建议在 LLM 层独立 PR 中处理 |
| **Reviewer** | ✅ APPROVE | 建议 Creator 先完成 D1 迁移再处理此项目，避免并行大改 |
| **Owner** | 提取重复 | |

</details>

---

#### D18: chat_stream 硬编码 max_tokens=1024

**现状**：`ClaudeAdapter.chat_stream()` 硬编码 `"max_tokens": 1024`，而 `chat()` 使用动态值。流式和非流式不一致，长回复可能在流式模式下截断。

**建议**：`chat_stream()` 也使用 `self.get_model_info().max_tokens`。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🟡 中优先级 | 1 行修复，但影响流式体验 |
| **Reviewer** | ⚠️ 需澄清 Owner 意图 | 将 max_tokens 改为动态值**不会降低**体验，反而会**改善**长回复被截断的问题；Owner 说的"不想影响"可能是不想引入风险？建议 Creator 确认后按最小改动修复 |
| **Owner** | 不想影响流式体验 | |

</details>

---

### 集群 G：学习引擎编排设计

#### D19: ChatMessage 持久化职责分散

**现状**：`learning_engine.process_message()` 处理业务逻辑但不负责 ChatMessage 持久化；路由层负责保存。非路由层调用方（测试、CLI）不会持久化消息。

**建议**：将 ChatMessage 持久化统一到 `learning_engine.process_message()` 内部。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🟡 中优先级 | 架构清晰度问题，当前功能正常 |
| **Reviewer** | ✅ APPROVE | 三方一致 |
| **Owner** | 可以 | |

</details>

---

#### D20: 掌握度(mastery)固定增量占位符 — FSRS 未接入

**现状**：
- 后端 `learning_engine.py`: `"mastery_level": 50` 硬编码
- 前端 `learning.ts`: `masteryPercent.value += 3` 每条消息固定 +3%
- `spaced_repetition.py` 和 FSRS 算法已存在但**从未被学习引擎调用**

**影响**：掌握度完全是无意义的占位数据。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🔴 高优先级 | FSRS 已开发未接入是功能浪费；建议联调后独立 Phase 接入 |
| **Reviewer** | ✅ 同意高优先级，但建议独立立项 | FSRS 接入是大任务，不应与联调重构混合；联调完成后再单独立项处理 |
| **Owner** | _待定_ | |

</details>

---

### 集群 H：API 路由设计

#### D21: User Profile 端点错放 learning.py

**现状**：`GET /user/profile` 和 `POST /user/profile/refresh` 放在 `learning.py`，但属于用户管理端点。

**建议**：迁移到独立的 `user.py` 路由。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🟢 低优先级 | RESTful 组织问题，不影响功能 |
| **Reviewer** | ✅ APPROVE | 低优先级，路由重组时一并处理 |
| **Owner** | _待定_ | |

</details>

---

#### D22: Chat 端点隐含自动 start_learning 副作用

**现状**：`send_message()` 无活跃 session 时自动调用 `start_learning()`。一个 `POST /chat` 可能触发创建 session → seed memories → 大量查询。

**建议**：文档化此行为，或改为返回 404 让前端显式调用 start。

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | 🟢 低优先级 | 当前已正常工作，但隐含副作用可能导致调试困难 |
| **Reviewer** | ✅ APPROVE | 低优先级，建议至少加代码注释文档化此行为 |
| **Owner** | _待定_ | |

</details>

---

### 📋 D14-D22 优先级排序

| 问题 | 影响 | 优先级 | 建议 |
|------|------|--------|------|
| D20 掌握度占位符/FSRS 未接入 | 🔴 高 — 核心功能未生效 | 🔴 高 | 联调后独立 Phase |
| D14 Seed Memory 重复 | 🟡 中 — 数据膨胀 | 🟡 中 | seed 创建前加去重 |
| D15 召回计数未更新 | 🟡 中 — 遗忘曲线无法实现 | 🟡 中 | MemoryFactsModule 检索后调用 update |
| D19 ChatMessage 职责分散 | 🟡 中 — 架构清晰度 | 🟡 中 | 统一到 LearningEngine |
| D17 Adapter 代码重复 | 🟡 中 — 维护成本 | 🟡 中 | 提取公共基类 |
| D18 max_tokens 不一致 | 🟡 中 — 流式截断风险 | 🟡 中 | 1 行修复 |
| D16 fact_type 双重维护 | 🟢 低 — 容易遗漏 | 🟢 低 | 统一为枚举 |
| D21 端点错放 | 🟢 低 — RESTful 组织 | 🟢 低 | 路由重组时迁移 |
| D22 隐含副作用 | 🟢 低 — 已正常工作 | 🟢 低 | 文档化 |

---

## 6. 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 双模型职责调整需要数据迁移 | 中 | 中 | 编写 Alembic migration + 回滚脚本 |
| 创建流程统一导致 UI 回归 | 中 | 中 | 保留旧组件直到新流程通过 e2e 测试 |
| 模板差异化增加 Prompt 维护成本 | 低 | 低 | 从基础+扩展模式开始，逐步增加 |
| speech_style 格式变更影响已有数据 | 低 | 低 | 已有数据可能为空或单字符串，需兼容 |
| template_name 持久化后已有角色无此字段 | 低 | 低 | 设为 nullable，已有角色为 null |

---

## 7. 讨论记录

| 日期 | 参与者 | 讨论内容 | 结论 |
|------|--------|---------|------|
| 2026-04-14 | Creator | 提出设计层重构草案，识别 D1-D7 设计问题 | 待 Reviewer 确认 |
| 2026-04-14 | Creator | 补充发现 D8-D13（审查 PromptBuilder/前端常量/数据模型） | 待 Reviewer 确认 |
| 2026-04-14 | Creator | 系统性子系统审查，发现 D14-D22（记忆/LLM/引擎/API） | 待 Reviewer 确认 |
| 2026-04-14 | Owner | 确认 D1-D7 决策：D1=合并到Character、D2=A、D3=socrates、D4=C、D5=B、D6=B、D7=B | ✅ 已确认 |
| 2026-04-14 | Reviewer | 审阅 D1-D22 全部决策：D1 附条件 APPROVE（3 点）；D14 建议文档化 per-session 语义；D18 需澄清 Owner 意图；其余全部 APPROVE | ✅ 审阅完成 |

---

## 附录：与联调重构计划的交叉引用

| 本计划决策 | 联调计划关联 | 建议 |
|-----------|------------|------|
| D1 (双模型) | — | 在联调 Phase 3 之前确认 |
| D2 (创建流程) | Phase 3 §3.7 (角色模板合并) | 合并执行 |
| D3 (模板 key) | 联调 D3 (已确认 `socrates`) | 保持一致 |
| D4 (Prompt 策略) | — | 可独立于联调计划执行 |
| D5 (template_name) | — | 与 D4 联动 |
| D6 (speech_style) | — | 在联调 Phase 1 之前确认 |
| D7 (TRAIT_SLIDERS) | Phase 3 §3.7 (角色模板合并) | 随 D2 自然解决 |