# 问题 15: 角色模板（Persona Templates）前后端重复定义且 key 不匹配

## 问题类型
重复定义 + 潜在 Bug

## 涉及文件
- `backend/api/routes/archive.py` 第 44-50 行（`PERSONA_TEMPLATES` 字典）
- `frontend/src/constants/personaTemplates.ts` 第 15-51 行（`PERSONA_TEMPLATES` 数组）

## 重复内容

**后端（archive.py）：**
```python
PERSONA_TEMPLATES = {
    "苏格拉底型": ["耐心", "追问型", "启发型"],
    "爱因斯坦型": ["鼓励型", "探索型", "启发型"],
    "亚里士多德型": ["严谨", "体系化", "百科全书"],
    "孙子型": ["策略性", "举一反三", "引导型"],
    "默认": ["耐心", "启发型"],
}
```

**前端（personaTemplates.ts）：**
```typescript
export const PERSONA_TEMPLATES: PersonaTemplate[] = [
  { key: 'socrates',    name: '苏格拉底型',   traits: ['耐心', '追问型', '启发型'] },
  { key: 'einstein',    name: '爱因斯坦型',   traits: ['鼓励型', '探索型', '启发型'] },
  { key: 'aristotle',   name: '亚里士多德型', traits: ['严谨', '体系化', '百科全书'] },
  { key: 'sunzi',       name: '孙子型',       traits: ['策略性', '举一反三', '引导型'] },
  { key: 'custom',      name: '自定义',       traits: [] },
]
```

## 潜在 Bug

前端 `buildCharacterPayload` 发送 `template_name: form.templateKey`（值为 `'socrates'`），但后端使用中文 key 做 lookup：

```python
template_traits = PERSONA_TEMPLATES.get(template_name, PERSONA_TEMPLATES["默认"])
```

`PERSONA_TEMPLATES.get("socrates")` 找不到匹配，**始终 fallback 到 `"默认"`**。

当前因为前端同时发送了 `traits`（滑块值），会走 `if traits is not None` 分支而跳过模板查找，所以 bug 未触发。但如果前端不发送 traits（例如使用预设模板而非自定义滑块），后端将无法正确匹配模板。

## 影响分析

1. **数据不同步风险**：新增模板时前后端需分别修改，traits 容易出现不一致
2. **key 不匹配的潜在 bug**：前端用英文 key，后端用中文 key，模板查找永远失败
3. **`"custom"` 前端有但后端没有**：前端有 `custom` 模板，后端没有对应处理

## 建议修复方向

1. **短期修复**：统一 key 格式。建议后端改为英文 key（`"socrates"` 而非 `"苏格拉底型"`），与前端保持一致
2. **中期优化**：将模板数据提取为独立的 JSON/YAML 配置文件，前后端共享（或由后端提供 `/api/persona-templates` 接口）
3. **验证**：测试不发送 traits 时，后端是否能正确根据 template_name 选择模板