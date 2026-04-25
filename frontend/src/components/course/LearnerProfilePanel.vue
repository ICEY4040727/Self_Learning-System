<template>
  <div class="learner-profile-panel">
    <div class="panel-header">
      <h3 class="panel-title">学习画像</h3>
      <span v-if="lastUpdated" class="panel-time">{{ lastUpdated }}</span>
    </div>

    <!-- Strengths & Weaknesses -->
    <div v-if="strengths.length || weaknesses.length" class="sw-section">
      <div v-if="strengths.length" class="sw-group">
        <span class="sw-label strength-label">优势</span>
        <div class="sw-tags">
          <span v-for="s in strengths" :key="s" class="sw-tag strength-tag">
            {{ dimLabel(s) }}
          </span>
        </div>
      </div>
      <div v-if="weaknesses.length" class="sw-group">
        <span class="sw-label weakness-label">待加强</span>
        <div class="sw-tags">
          <span v-for="w in weaknesses" :key="w" class="sw-tag weakness-tag">
            {{ dimLabel(w) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Dimension Bars -->
    <div v-if="Object.keys(dimensionScores).length" class="dimensions-section">
      <div
        v-for="(score, key) in dimensionScores"
        :key="key"
        class="dim-row"
      >
        <div class="dim-header">
          <span class="dim-name">{{ dimLabel(key) }}</span>
          <span class="dim-value">{{ (score * 100).toFixed(0) }}%</span>
        </div>
        <div class="dim-bar-bg">
          <div
            class="dim-bar-fill"
            :style="{ width: `${score * 100}%` }"
            :class="dimClass(score)"
          ></div>
        </div>
      </div>
    </div>

    <!-- Learning Stats -->
    <div v-if="learningStats" class="stats-section">
      <div class="stat-row">
        <span class="stat-key">总学时</span>
        <span class="stat-val">{{ learningStats.total_sessions || 0 }} 次</span>
      </div>
      <div class="stat-row">
        <span class="stat-key">掌握概念</span>
        <span class="stat-val">{{ learningStats.concepts_mastered || 0 }}</span>
      </div>
      <div class="stat-row">
        <span class="stat-key">薄弱概念</span>
        <span class="stat-val">{{ learningStats.concepts_struggling || 0 }}</span>
      </div>
    </div>

    <div v-if="!Object.keys(dimensionScores).length && !strengths.length" class="empty-hint">
      尚未积累足够数据生成画像，继续学习后将自动分析
    </div>
  </div>
</template>

<script setup lang="ts">

const DIM_LABELS: Record<string, string> = {
  abstract_thinking: '抽象思维',
  concrete_application: '实践应用',
  visual_learning: '视觉学习',
  verbal_learning: '语言学习',
  problem_solving: '问题解决',
  memory_retention: '记忆保持',
  curiosity: '好奇心',
  persistence: '坚持度',
  collaboration: '协作学习',
  self_correction: '自我纠错',
}

defineProps<{
  dimensionScores: Record<string, number>
  strengths: string[]
  weaknesses: string[]
  learningStats?: {
    total_sessions?: number
    concepts_mastered?: number
    concepts_struggling?: number
  }
  lastUpdated?: string
}>()

const dimLabel = (key: string) => DIM_LABELS[key] || key

const dimClass = (score: number) => {
  if (score >= 0.7) return 'fill-high'
  if (score >= 0.4) return 'fill-mid'
  return 'fill-low'
}
</script>

<style scoped>
.learner-profile-panel {
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 215, 0, 0.08);
  border-radius: 12px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffd700;
  margin: 0;
  letter-spacing: 2px;
}

.panel-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
}

/* Strengths & Weaknesses */
.sw-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.sw-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sw-label {
  font-size: 12px;
  font-weight: 600;
  min-width: 52px;
}

.strength-label { color: #4adf6a; }
.weakness-label { color: #fbbf24; }

.sw-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sw-tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 12px;
}

.strength-tag {
  background: rgba(74, 223, 106, 0.12);
  color: #4adf6a;
  border: 1px solid rgba(74, 223, 106, 0.25);
}

.weakness-tag {
  background: rgba(251, 191, 36, 0.12);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.25);
}

/* Dimension Bars */
.dimensions-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.dim-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dim-name {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.dim-value {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}

.dim-bar-bg {
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.dim-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.fill-high { background: linear-gradient(90deg, #4adf6a, #22c55e); }
.fill-mid { background: linear-gradient(90deg, #60a5fa, #3b82f6); }
.fill-low { background: linear-gradient(90deg, #fbbf24, #f59e0b); }

/* Stats */
.stats-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.stat-key { color: rgba(255, 255, 255, 0.4); }
.stat-val { color: rgba(255, 255, 255, 0.7); font-weight: 500; }

.empty-hint {
  text-align: center;
  padding: 24px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.3);
}
</style>
</task_progress>
</write_to_file>
<task_progress>
- [x] Phase 3 全部完成并提交
- [x] 教材上传前端集成
- [x] 删除所有 emoji
- [ ] 学习画像 UI (Phase 2F)
  - [x] LearnerProfilePanel 组件
  - [ ] API 端点接入
  - [ ] 集成到 CoursePage
  - [ ] build + test 验证
  - [ ] Git 提交
</task_progress>
</write_to_file>