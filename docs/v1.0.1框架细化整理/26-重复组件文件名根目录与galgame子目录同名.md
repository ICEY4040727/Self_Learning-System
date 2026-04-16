# 问题 26: 重复组件文件名（根目录与 galgame 子目录同名）

## ⚠️ 未解决

**说明**: 同名组件仍存在于两个目录

## 问题类型
文件结构混乱 / 命名冲突

## 涉及文件

| 根目录 `components/` | `components/galgame/` | 功能关系 |
|---|---|---|
| `BacklogPanel.vue` | `galgame/BacklogPanel.vue` | 可能功能重叠 |
| `DialogBox.vue` | `galgame/DialogBox.vue` | 可能功能重叠 |
| `HudBar.vue` | `galgame/HudBar.vue` | 可能功能重叠 |
| `SaveLoadPanel.vue` | `galgame/CheckpointPanel.vue` | 存档/检查点功能重叠 |

## 影响分析

1. **导入歧义**：开发者导入时容易混淆 `@/components/DialogBox` 和 `@/components/galgame/DialogBox`
2. **功能重叠风险**：根目录的组件可能是旧版，galgame 下的是新版（重构后遗留）
3. **维护浪费**：修改同一功能时可能改了错误的文件

## 建议修复方向

1. 确认根目录的 BacklogPanel、DialogBox、HudBar 是否仍被引用
2. 如果无引用 → 删除根目录版本
3. 如果仍有引用 → 迁移引用到 galgame 版本后删除根目录版本
4. 如果两版本功能不同 → 重命名以消除歧义（如 `LegacyDialogBox.vue`）