<template>
  <Transition name="drawer">
    <div v-if="show" class="memory-drawer-overlay" @click.self="$emit('close')">
      <div class="memory-drawer">
        <div class="drawer-header">
          <h3 class="drawer-title">📋 学习档案</h3>
          <button class="close-btn" @click="$emit('close')">✕</button>
        </div>

        <!-- Stats Summary -->
        <div class="stats-summary">
          <div class="stat-card">
            <span class="stat-icon">🧠</span>
            <span class="stat-value">{{ stats.total || 0 }}</span>
            <span class="stat-label">记忆总数</span>
          </div>
          <div class="stat-card">
            <span class="stat-icon">✅</span>
            <span class="stat-value">{{ stats.concept_mastered || 0 }}</span>
            <span class="stat-label">已掌握</span>
          </div>
          <div class="stat-card">
            <span class="stat-icon">⚠️</span>
            <span class="stat-value">{{ stats.concept_struggle || 0 }}</span>
            <span class="stat-label">薄弱点</span>
          </div>
          <div class="stat-card">
            <span class="stat-icon">💡</span>
            <span class="stat-value">{{ stats.preference || 0 }}</span>
            <span class="stat-label">偏好</span>
          </div>
        </div>

        <!-- Filter Tabs -->
        <div class="filter-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            class="filter-tab"
            :class="{ active: activeFilter === tab.value }"
            @click="activeFilter = tab.value"
          >
            {{ tab.label }}
            <span class="tab-count">{{ getTabCount(tab.value) }}</span>
          </button>
        </div>

        <!-- Facts List -->
        <div class="facts-container">
          <div v-if="loading" class="loading-state">
            <span class="loading-spinner"></span>
            加载中...
          </div>
          <div v-else-if="filteredFacts.length === 0" class="empty-state">
            <div class="empty-icon">📭</div>
            <div class="empty-text">暂无相关记忆</div>
          </div>
          <div v-else class="facts-list">
            <div
              v-for="fact in filteredFacts"
              :key="fact.id"
              class="fact-item"
              :class="fact.fact_type"
            >
              <div class="fact-header">
                <span class="fact-type-badge">{{ typeLabel(fact.fact_type) }}</span>
                <span class="fact-salience" :style="{ opacity: fact.salience }">
                  {{ Math.round(fact.salience * 100) }}%
                </span>
              </div>
              <div class="fact-content">{{ fact.content }}</div>
              <div v-if="fact.concept_tags?.length" class="fact-tags">
                <span
                  v-for="tag in fact.concept_tags"
                  :key="tag"
                  class="concept-tag"
                >
                  {{ tag }}
                </span>
              </div>
              <div class="fact-footer">
                <span class="fact-date">{{ formatDate(fact.created_at) }}</span>
                <span v-if="fact.recall_count > 0" class="recall-count">
                  被回忆 {{ fact.recall_count }} 次
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface MemoryFact {
  id: number
  fact_type: string
  content: string
  concept_tags?: string[]
  salience: number
  created_at: string
  recall_count: number
}

interface Stats {
  total?: number
  concept_mastered?: number
  concept_struggle?: number
  preference?: number
  student_state?: number
  event?: number
  by_type?: Record<string, number>
}

const props = defineProps<{
  show: boolean
  facts: MemoryFact[]
  stats: Stats
  loading?: boolean
}>()

defineEmits<{
  close: []
}>()

const activeFilter = ref('all')

const tabs = [
  { value: 'all', label: '全部' },
  { value: 'student_state', label: '状态' },
  { value: 'concept_mastered', label: '已掌握' },
  { value: 'concept_struggle', label: '薄弱' },
  { value: 'preference', label: '偏好' },
  { value: 'event', label: '事件' },
]

const typeLabels: Record<string, string> = {
  student_state: '学习状态',
  concept_mastered: '掌握概念',
  concept_struggle: '薄弱点',
  preference: '学习偏好',
  event: '学习事件',
  commitment: '承诺',
}

const typeLabel = (type: string) => typeLabels[type] || type

const getTabCount = (filter: string) => {
  if (filter === 'all') return props.stats.total || 0
  return props.stats.by_type?.[filter] || 0
}

const filteredFacts = computed(() => {
  if (activeFilter.value === 'all') return props.facts
  return props.facts.filter(f => f.fact_type === activeFilter.value)
})

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.memory-drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.memory-drawer {
  width: 420px;
  max-width: 90vw;
  height: 100%;
  background: linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%);
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.drawer-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* Stats Summary */
.stats-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}

.stat-icon {
  font-size: 16px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #a78bfa;
}

.stat-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
}

/* Filter Tabs */
.filter-tabs {
  display: flex;
  gap: 6px;
  padding: 12px 24px;
  overflow-x: auto;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.filter-tab:hover {
  background: rgba(255, 255, 255, 0.06);
}

.filter-tab.active {
  background: rgba(167, 139, 250, 0.2);
  border-color: rgba(167, 139, 250, 0.4);
  color: #a78bfa;
}

.tab-count {
  font-size: 10px;
  padding: 2px 5px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}

.filter-tab.active .tab-count {
  background: rgba(167, 139, 250, 0.3);
}

/* Facts List */
.facts-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: rgba(255, 255, 255, 0.5);
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-top-color: #a78bfa;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  color: rgba(255, 255, 255, 0.5);
}

.facts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fact-item {
  padding: 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  transition: all 0.2s;
}

.fact-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.fact-item.concept_mastered {
  border-left: 3px solid #4adf6a;
}

.fact-item.concept_struggle {
  border-left: 3px solid #fbbf24;
}

.fact-item.student_state {
  border-left: 3px solid #60a5fa;
}

.fact-item.preference {
  border-left: 3px solid #a78bfa;
}

.fact-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.fact-type-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(167, 139, 250, 0.2);
  color: #a78bfa;
  border-radius: 4px;
}

.fact-salience {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.fact-content {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.5;
  margin-bottom: 8px;
}

.fact-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.concept-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
  border-radius: 4px;
}

.fact-footer {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
}

/* Transitions */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.3s ease;
}

.drawer-enter-active .memory-drawer,
.drawer-leave-active .memory-drawer {
  transition: transform 0.3s ease;
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .memory-drawer,
.drawer-leave-to .memory-drawer {
  transform: translateX(100%);
}
</style>
