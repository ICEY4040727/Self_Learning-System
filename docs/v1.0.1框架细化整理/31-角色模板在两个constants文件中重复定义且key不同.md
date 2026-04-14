# 问题 31: 角色模板在 `characterPresets.ts` 和 `personaTemplates.ts` 中重复定义且 key 不同

## 问题类型
重复定义 + key 不一致

## 涉及文件
- `frontend/src/constants/characterPresets.ts` — `SAGE_TEMPLATES`（6 个模板，key: `socratic`/`einstein`/...）
- `frontend/src/constants/personaTemplates.ts` — `PERSONA_TEMPLATES`（5 个模板，key: `socrates`/`einstein`/...）

## 重复内容

**characterPresets.ts 的 SAGE_TEMPLATES：**
| key | name | icon |
|-----|------|------|
| `socratic` | 苏格拉底型 | 🤔 |
| `einstein` | 爱因斯坦型 | 💡 |
| `aristotle` | 亚里士多德型 | 📚 |
| `sunzi` | 孙子型 | ⚔️ |
| `yoda` | 尤达型 | 🌙 |
| `free` | 自由奔放型 | 🦋 |

**personaTemplates.ts 的 PERSONA_TEMPLATES：**
| key | name | icon |
|-----|------|------|
| `socrates` | 苏格拉底型 | 🧘 |
| `einstein` | 爱因斯坦型 | 💡 |
| `aristotle` | 亚里士多德型 | 📚 |
| `sunzi` | 孙子型 | ⚔️ |
| `custom` | 自定义 | ✨ |

## 问题细节

1. **苏格拉底 key 不同**：`socratic` vs `socrates`
2. **图标不同**：苏格拉底 🤔 vs 🧘；自由奔放 🦋 vs 自定义 ✨
3. **模板数量不同**：6 vs 5（yoda/free 对应 custom）
4. **额外重复**：两个文件都定义了 `TraitSlider` 接口和 `TRAIT_SLIDERS` 常量（字段名还不同：`label`/`leftLabel` vs `name`/`minLabel`/`maxLabel`）

## 影响分析

1. **后端模板查找可能失败**：两个不同的 key（`socratic` vs `socrates`）发给后端，一个可能匹配不到
2. **维护成本翻倍**：新增模板需同步修改两处，且保持 key 一致
3. **TraitSlider 接口重复**：TypeScript 可能产生类型兼容问题

## 建议修复方向

1. 统一到一个文件（如 `characterPresets.ts`），`personaTemplates.ts` 引用或删除
2. 统一 key 命名规范（与后端 `persona_generate` 的模板 key 保持一致）
3. 合并 `TraitSlider` 接口，消除重复定义