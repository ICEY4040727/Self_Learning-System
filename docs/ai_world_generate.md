# AI 辅助生成世界 — 功能文档

## 1. 概述

在 `CreateWorldModal` 的第一步（命名世界）中，新增「AI 智能生成」入口。用户输入一段简短描述（如"一个充满魔法的维多利亚时代学院"），AI 自动生成世界名称、描述、主题风格、氛围标签等建议，用户可一键采用或手动调整后继续。

## 2. 用户流程

```
Step 1: 命名你的世界
┌─────────────────────────────────────┐
│ [原有] 世界名称输入框                  │
│ [原有] 主题风格网格                    │
│                                     │
│ ─── AI 智能生成 ───                  │
│ [新增] 描述输入框: "描述你想要的世界…"   │
│ [新增] [✨ 智能生成] 按钮              │
│                                     │
│ [新增] AI 建议卡片（生成后显示）         │
│   名称: xxx    描述: xxx              │
│   主题: xxx    氛围: xxx, xxx         │
│   [采用此方案]                        │
│                                     │
│ [原有] 下一步 按钮                     │
└─────────────────────────────────────┘
```

## 3. 后端接口

### `POST /world/generate`

**Request:**
```json
{
  "description": "一个充满魔法的维多利亚时代学院",
  "inspiration_type": "freeform"  // "freeform" | "style_reference"
}
```

- `description`: 用户自由描述，5-500 字
- `inspiration_type`: `freeform`=自由描述，`style_reference`=参考某个已有作品/风格

**Response:**
```json
{
  "name_suggestion": "星霜学院",
  "description": "维多利亚时代的魔法学院，古老钟楼与浮空书架并存...",
  "theme_preset": "academy",
  "mood_tags": ["mysterious", "academic", "elegant"],
  "bgm_suggestion": "classical",
  "scene_description": "黄昏时分，学院钟楼敲响，走廊中漂浮着微光..."
}
```

**字段说明：**
| 字段 | 类型 | 说明 |
|------|------|------|
| name_suggestion | string | AI 生成的世界名称（2-20字） |
| description | string | 世界描述（20-140字） |
| theme_preset | string | 推荐的主题 key（必须匹配 WORLD_THEMES 中的 key） |
| mood_tags | string[] | 推荐氛围标签 key 列表（匹配 MOOD_TAGS 中的 key） |
| bgm_suggestion | string | 推荐背景音乐 key |
| scene_description | string | 场景描写（用于未来扩展，暂不使用） |

**限制：**
- 30 秒冷却（同 persona/generate）
- 需要用户已配置 API Key
- 使用用户默认 LLM provider

## 4. LLM Prompt 设计

```
你是世界设计师。根据用户的描述，为 Galgame 风格学习系统生成一个"学习世界"。

用户描述：{description}
类型：{inspiration_type}

可选主题：
- academy: 学院（知识殿堂，智者云集）
- library: 图书馆（卷帙浩繁，静谧求知）
- lab: 实验室（探索未知，验证真理）
- mountain: 山林书院（隐世修行，问道自然）
- cyber: 赛博空间（数字世界，代码织梦）
- starship: 星际飞船（星辰大海，文明探索）
- ruins: 遗迹废墟（远古智慧，待发掘）
- dream: 梦境迷宫（意识深处，无限可能）

可选氛围标签：
- mysterious, academic, warm, tense, elegant, lively, quiet, dark, fantastical, realistic, futuristic, romantic

可选背景音乐：
- silent: 静默, piano: 钢琴曲, ambient: 环境音, classical: 古典乐, electronic: 电子乐, nature: 自然音

输出严格 JSON（不要 markdown 代码块）：
{
  "name_suggestion": "2-20字世界名称",
  "description": "20-140字世界描述",
  "theme_preset": "从可选主题中选一个 key",
  "mood_tags": ["从可选氛围标签中选 1-3 个"],
  "bgm_suggestion": "从可选背景音乐中选一个 key",
  "scene_description": "50-100字场景描写"
}

规则：
- 名称要简洁有诗意，避免太普通（如"我的世界"、"新世界"）
- 描述要有画面感，暗示学习探索的故事
- 主题必须从给定列表中选择
- 氛围标签不超过 3 个
- 必须输出合法 JSON，不要 markdown 代码块
```

## 5. 前端实现

### CreateWorldModal 修改

在 Step 1 的主题网格下方、下一步按钮上方，新增 AI 生成区域：

1. 描述输入框 + 「✨ 智能生成」按钮
2. 生成后显示建议卡片
3. 点击「采用此方案」自动填充表单

### API 调用

```typescript
// frontend/src/api/world.ts
export const worldApi = {
  // ... 现有方法
  async generate(description: string, inspirationType: string = 'freeform') {
    return await client.post('/world/generate', { description, inspiration_type: inspirationType })
  }
}
```

## 6. 文件修改清单

| 文件 | 变更 |
|------|------|
| `backend/api/routes/archive.py` | 新增 `WorldGenerateRequest`, `WorldGenerateResponse`, `WORLD_GENERATE_PROMPT`, `POST /world/generate` |
| `frontend/src/api/world.ts` | 新增 `worldApi.generate()` |
| `frontend/src/components/CreateWorldModal.vue` | Step 1 新增 AI 生成区域 |

## 7. 参考实现

- 后端模式：完全参照 `POST /persona/generate`（archive.py L1719）
- 前端模式：参照 `CreatePersonaModal.vue` 的 AI 生成区域