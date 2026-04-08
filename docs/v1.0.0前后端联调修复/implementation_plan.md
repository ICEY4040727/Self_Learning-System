# Implementation Plan

[Overview]

本计划涵盖 v1.0.0 前后端联调的最后两项关键任务：数据库迁移验证和前端 UserProfile 页面实现。

后端 API 和服务已完整实现，包括：
- `GET /api/user/profile` - 获取用户全局画像
- `POST /api/user/profile/refresh` - 手动刷新画像
- `backend/services/user_profile.py` - 完整的画像计算逻辑（增量更新版）

前端需要实现 UserProfile 页面，展示：
- 元认知趋势雷达图（MSKT 四维度）
- 学习偏好稳定性（进度条）
- 学习统计（数字卡片）

[Types]

**前端 TypeScript 类型定义：**

```typescript
// 扩展 frontend/src/types/index.ts

// 元认知趋势
interface MetacognitionTrend {
  current: 'weak' | 'moderate' | 'strong'
  trend: 'improving' | 'stable' | 'unknown'
  evidence_count: number
  latest_evidence?: string
}

// 偏好稳定性
interface PreferenceStability {
  stable: boolean
  consistency?: number  // 布尔值偏好
  most_common?: string  // 枚举值偏好
  display: string
  status?: 'insufficient_data'  // 数据不足时
}

// 学习统计
interface LearningStats {
  total_concepts_learned: number
  total_sessions: number
  average_mastery: number  // 0-1
  worlds_explored: number
}

// UserProfile 响应
interface UserProfile {
  user_id: number
  computed_at: string
  metacognition_trend: Record<string, MetacognitionTrend>
  preference_stability: Record<string, PreferenceStability>
  learning_stats: LearningStats
}
```

[Files]

**前端新增文件：**

| 文件路径 | 用途 |
|---------|------|
| `frontend/src/views/UserProfile.vue` | 用户画像主页面 |
| `frontend/src/components/MetacognitionRadar.vue` | 元认知雷达图组件 |
| `frontend/src/components/PreferenceBars.vue` | 偏好稳定性进度条组件 |
| `frontend/src/components/LearningStatsCards.vue` | 学习统计数字卡片组件 |

**前端修改文件：**

| 文件路径 | 修改内容 |
|---------|---------|
| `frontend/src/types/index.ts` | 添加 UserProfile 相关类型 |
| `frontend/src/router/index.ts` | 添加 UserProfile 路由 |
| `frontend/src/views/Home.vue` | 菜单添加"学习报告"入口 |
| `frontend/src/api/client.ts` | 添加 user/profile API 调用 |

**后端（已实现，无需修改）：**

| 文件路径 | 状态 |
|---------|------|
| `backend/api/routes/learning.py` | ✅ GET/POST /api/user/profile |
| `backend/services/user_profile.py` | ✅ 完整服务实现 |

**数据库迁移（需验证）：**

| 文件路径 | 状态 |
|---------|------|
| `backend/alembic/versions/2026_04_06_add_character_experience.py` | ⚠️ 需验证是否已执行 |
| `backend/alembic/versions/2026_04_06_add_user_profiles.py` | ⚠️ 需验证是否已执行 |

[Functions]

**前端新增函数：**

| 函数名 | 文件 | 用途 |
|-------|------|------|
| `useUserProfile` | `UserProfile.vue` (composition API) | 组合式函数，管理画像数据 |
| `fetchUserProfile` | `UserProfile.vue` | 获取用户画像 |
| `refreshUserProfile` | `UserProfile.vue` | 刷新用户画像 |
| `getRadarData` | `MetacognitionRadar.vue` | 计算雷达图数据 |
| `getPreferenceData` | `PreferenceBars.vue` | 计算进度条数据 |

**API 调用：**

```typescript
// frontend/src/api/client.ts 添加
export const userProfileApi = {
  get: () => client.get('/user/profile'),
  refresh: (force: boolean = false) => client.post('/user/profile/refresh', { force })
}
```

[Classes]

**前端 Vue 组件：**

| 组件 | 路径 | 说明 |
|------|------|------|
| `UserProfile` | `views/UserProfile.vue` | 主页面，4层布局 |
| `MetacognitionRadar` | `components/MetacognitionRadar.vue` | 雷达图，使用 ECharts |
| `PreferenceBars` | `components/PreferenceBars.vue` | 进度条列表 |
| `LearningStatsCards` | `components/LearningStatsCards.vue` | 数字卡片网格 |

[Dependencies]

**新增前端依赖：**

| 包名 | 版本 | 用途 |
|------|------|------|
| `echarts` | ^5.5.0 | 雷达图可视化 |
| `vue-echarts` | ^6.6.0 | Vue 3 ECharts 封装 |

**添加到 package.json：**
```json
{
  "dependencies": {
    "echarts": "^5.5.0",
    "vue-echarts": "^6.6.0"
  }
}
```

[Testing]

**手动测试清单：**

1. 数据库迁移验证
   - [ ] `alembic current` 显示最新版本
   - [ ] `alembic history` 显示所有迁移
   - [ ] 数据库 characters 表包含 experience_points 和 level 列
   - [ ] 数据库 user_profiles 表存在

2. 前端 UserProfile 页面
   - [ ] 页面可正常访问 `/home/profile`
   - [ ] 元认知雷达图正确显示（需要 ≥1 个世界数据）
   - [ ] 偏好进度条正确显示
   - [ ] 学习统计卡片显示正确数据
   - [ ] 刷新按钮功能正常

3. 前后端联调
   - [ ] `GET /api/user/profile` 返回正确数据
   - [ ] `POST /api/user/profile/refresh` 重新计算成功

[Implementation Order]

1. **数据库迁移验证（你负责）**
   - 执行 `alembic current` 检查当前版本
   - 执行 `alembic upgrade head` 应用迁移
   - 验证表结构正确

2. **安装前端依赖**
   - `npm install echarts vue-echarts`

3. **添加类型定义**
   - 更新 `types/index.ts`

4. **添加 API 调用**
   - 更新 `api/client.ts`

5. **实现 MetacognitionRadar 组件**
   - 使用 ECharts 雷达图

6. **实现 PreferenceBars 组件**
   - 使用进度条显示稳定性

7. **实现 LearningStatsCards 组件**
   - 数字卡片网格布局

8. **实现 UserProfile 主页面**
   - 组装所有组件

9. **添加路由和菜单**
   - 更新 router/index.ts
   - 更新 Home.vue 菜单

10. **手动测试验证**
