# 问题 26: 重复组件文件名（根目录与 galgame 子目录同名）

## ⚠️ 未解决

**说明**: 同名组件仍存在于两个目录

## 问题类型
文件结构混乱 / 命名冲突

## 涉及文件

| 根目录 `components/` | `components/galgame/` | 备注 |
|---|---|---|
| `BacklogPanel.vue` | `galgame/BacklogPanel.vue` | 时间戳相同，需进一步分析 |
| `DialogBox.vue` | `galgame/DialogBox.vue` | 时间戳相同，需进一步分析 |
| `HudBar.vue` (04-14 13:35) | `galgame/HudBar.vue` (04-14 13:23) | ✅ 根目录更新 |
| `SaveLoadPanel.vue` | `galgame/CheckpointPanel.vue` | 文件名不同，需进一步分析 |

## ⚠️ 惯性偏好提醒

**不要假设 galgame 子目录是新版**。应根据实际时间戳判断：
- `HudBar.vue`：根目录（04-14 13:35）比 galgame（04-14 13:23）**更新 12 分钟**
- 应保留根目录版本

## 影响分析

1. **导入歧义**：开发者导入时容易混淆 `@/components/DialogBox` 和 `@/components/galgame/DialogBox`
2. **惯性偏好风险**：错误地认为 galgame 目录是新版，导致保留旧代码
3. **维护浪费**：修改同一功能时可能改了错误的文件

## 建议修复方向

1. 检查各同名组件的时间戳，确认哪个是新版
2. 确认根目录的 BacklogPanel、DialogBox、HudBar 是否仍被引用
3. 如果无引用 → 删除旧版本
4. 如果仍有引用 → 迁移引用到新版后删除旧版本
