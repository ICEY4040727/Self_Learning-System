<template>
  <div class="sage-card" @click="$emit('select', sage)">
    <div class="sage-avatar">
      <img v-if="sage.avatar" :src="sage.avatar" :alt="sage.name" />
      <span v-else class="sage-icon">{{ sage.symbol || '☉' }}</span>
    </div>
    <div class="sage-info">
      <div class="sage-name">{{ sage.name }}</div>
      <div class="sage-title">{{ sage.title || '' }}</div>
      <div class="sage-relation">
        <span class="relation-icon">{{ stageIcon }}</span>
        <span class="relation-label">{{ stageLabel }}</span>
      </div>
      <div v-if="lastSessionTime" class="last-session">{{ lastSessionTime }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RELATIONSHIP_STAGE_LABELS, RELATIONSHIP_STAGE_ICONS } from '@/constants/courseLevels'

interface SageInfo {
  id: number
  name: string
  title?: string
  avatar?: string
  symbol?: string
  relationshipStage?: string
  lastSessionTime?: string
}

const props = defineProps<{
  sage: SageInfo
}>()

defineEmits<{
  select: [sage: SageInfo]
}>()

const stageLabel = computed(() => {
  const stage = props.sage.relationshipStage || 'stranger'
  return RELATIONSHIP_STAGE_LABELS[stage] || stage
})

const stageIcon = computed(() => {
  const stage = props.sage.relationshipStage || 'stranger'
  return RELATIONSHIP_STAGE_ICONS[stage] || '👤'
})

const lastSessionTime = computed(() => {
  if (!props.sage.lastSessionTime) return null
  // 格式化时间，如 "3小时前"
  const date = new Date(props.sage.lastSessionTime)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(hours / 24)
  
  if (days > 0) return `${days}天前对话`
  if (hours > 0) return `${hours}小时前对话`
  return '刚刚对话'
})
</script>

<style scoped>
.sage-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 120px;
}

.sage-card:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(251, 191, 36, 0.4);
  transform: translateY(-2px);
}

.sage-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.sage-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sage-icon {
  font-size: 28px;
  color: #fbbf24;
}

.sage-info {
  text-align: center;
}

.sage-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.sage-title {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 2px;
}

.sage-relation {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.relation-icon {
  font-size: 14px;
}

.last-session {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 4px;
}
</style>
