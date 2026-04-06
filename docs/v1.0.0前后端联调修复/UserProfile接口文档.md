# UserProfile 用户画像接口文档

> **文档类型**：前端对接文档
> **日期**：2026-04-06
> **依据**：learning_memory_theory.md 第五部分设计

---

## 一、API 端点

### 1. 获取用户画像

```
GET /api/user/profile
```

**认证**：需要登录（Bearer Token）

**响应**：
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "computed_at": "2026-04-06T10:00:00+00:00",
    "metacognition_trend": {
      "planning": {"current": "moderate", "trend": "improving", "evidence_count": 2, "latest_evidence": "..."},
      "monitoring": {"current": "weak", "trend": "stable", "evidence_count": 2},
      "regulating": {"current": "moderate", "trend": "unknown", "evidence_count": 1},
      "reflecting": {"current": "strong", "trend": "stable", "evidence_count": 2}
    },
    "preference_stability": {
      "visual_examples": {"stable": true, "consistency": 0.85, "display": "稳定"},
      "analogy_based": {"stable": true, "consistency": 0.7, "display": "稳定"},
      "step_by_step": {"stable": false, "consistency": 0.5, "display": "变化中"},
      "pace": {"stable": true, "most_common": "slow", "display": "slow"}
    },
    "learning_stats": {
      "total_concepts_learned": 45,
      "total_sessions": 12,
      "average_mastery": 0.65,
      "worlds_explored": 3
    }
  }
}
```

---

### 2. 手动刷新用户画像

```
POST /api/user/profile/refresh
```

**认证**：需要登录

**请求体**：
```json
{
  "force": false
}
```

**响应**：
```json
{
  "success": true,
  "data": { /* 同上 */ },
  "computed_at": "2026-04-06T10:30:00+00:00"
}
```

---

## 二、字段说明

### metacognition_trend（元认知趋势）

| 字段 | 类型 | 说明 |
|------|------|------|
| `*.current` | string | 当前值: weak / moderate / strong |
| `*.trend` | string | 趋势: improving / stable / unknown |
| `*.evidence_count` | int | 证据数量 |
| `*.latest_evidence` | string | 最新证据（可选） |

### preference_stability（偏好稳定性）

| 字段 | 类型 | 说明 |
|------|------|------|
| `*.stable` | bool | 是否稳定 |
| `*.consistency` | float | 一致率 0-1（布尔值偏好） |
| `*.most_common` | string | 最常见值（枚举值偏好） |
| `*.display` | string | 显示文本 |
| `*.status` | string | insufficient_data（数据不足时） |

### learning_stats（学习统计）

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_concepts_learned` | int | 学会的概念总数 |
| `total_sessions` | int | 总会话数 |
| `average_mastery` | float | 平均掌握度 0-1 |
| `worlds_explored` | int | 探索的世界数 |

---

## 三、UI 呈现方案

### 1. 元认知趋势 — 雷达图 + 趋势箭头

**图表类型**：雷达图（Spider Chart）

**数据映射**：
| MSKT值 | 数值 | 雷达图半径 |
|--------|------|-----------|
| weak | 1 | 33% |
| moderate | 2 | 66% |
| strong | 3 | 100% |

**趋势图标**：
| 趋势值 | 图标 | 颜色 |
|--------|------|------|
| improving | ↑ | 绿色 |
| stable | → | 黄色 |
| unknown | ? | 灰色 |

**UI 示例**：
```
        规划 ↑(+1)
         ▲
        /    \
  反思 →-----● 监控
        \    /
         ▼
        调节
```

---

### 2. 偏好稳定性 — 进度条

**UI 示例**：
```
学习风格偏好

👁 视觉化学习     ████████░░ 85% 稳定
🔗 类比学习       ███████░░░ 70% 稳定  
📝 步骤优先       █████░░░░░ 50% 变化中
⏱ 学习节奏       slow          稳定
```

---

### 3. 学习统计 — 数字卡片

**UI 示例**：
```
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│   45    │ │   12    │ │   65%   │ │    3    │
│ 概念数   │ │  会话数  │ │ 平均掌握 │ │  世界数  │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

### 4. 综合布局

```
┌─────────────────────────────────────────────┐
│  我的学习成长报告                            │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         元认知能力 (雷达图)            │   │
│  │    (规划↑ 监控→ 调节↑ 反思→)         │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         学习风格偏好                   │   │
│  │    (进度条 + 稳定性标签)              │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐            │
│  │ 45 │ │ 12 │ │ 65%│ │  3 │            │
│  │概念 │ │会话 │ │掌握│ │世界 │            │
│  └────┘ └────┘ └────┘ └────┘            │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 四、触发时机（后端自动处理）

前端无需主动触发，后端自动处理：

| 触发条件 | 后端行为 |
|---------|---------|
| 用户发送消息 | 自动更新元认知/偏好 |
| 会话结束 | 自动更新会话统计 |
| 用户查看 profile | 懒计算（>24小时重算） |

---

## 五、组件推荐

| 组件类型 | 推荐库 |
|---------|-------|
| 雷达图 | ECharts / vue-chartjs |
| 进度条 | Element Plus Progress |
| 数字卡片 | 自定义组件 |

---

*文档更新时间：2026-04-06*
