<template>
  <div class="progress-bar-container">
    <div class="progress-labels">
      <span class="label-start">{{ startLabel }}</span>
      <span class="label-end">{{ endLabel }}</span>
    </div>
    <div class="progress-track">
      <div class="progress-track-bg"></div>
      <div class="progress-track-fill" :style="{ width: `${progress}%` }"></div>
      <div class="progress-anchor start-anchor">○</div>
      <div class="progress-anchor end-anchor" :class="{ completed: progress >= 100 }">●</div>
    </div>
    <div class="progress-footer">
      <span class="progress-percent">{{ Math.round(progress) }}%</span>
      <span v-if="milestoneMessage" class="milestone-message">{{ milestoneMessage }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getLevelLabel } from '@/constants/courseLevels'

const props = defineProps<{
  currentLevel: string
  targetLevel: string
  progress: number
  conceptMasteredCount?: number
}>()

const startLabel = computed(() => getLevelLabel(props.currentLevel, false))
const endLabel = computed(() => getLevelLabel(props.targetLevel, true))

const milestoneMessage = computed(() => {
  const p = props.progress
  if (p >= 100) return '🎉 达成目标！'
  if (p >= 75) return '快要到达目标了'
  if (p >= 50) return '过半了，继续加油'
  if (p >= 25) return '刚上路'
  return null
})
</script>

<style scoped>
.progress-bar-container {
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 8px;
}

.progress-track {
  position: relative;
  height: 12px;
  margin: 8px 0;
}

.progress-track-bg {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 4px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  transform: translateY(-50%);
}

.progress-track-fill {
  position: absolute;
  top: 50%;
  left: 0;
  height: 4px;
  background: linear-gradient(90deg, #60a5fa, #a78bfa);
  border-radius: 2px;
  transform: translateY(-50%);
  transition: width 0.5s ease;
}

.progress-anchor {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 16px;
  color: rgba(255, 255, 255, 0.5);
}

.start-anchor {
  left: 0;
}

.end-anchor {
  left: 100%;
  color: rgba(255, 255, 255, 0.3);
}

.end-anchor.completed {
  color: #fbbf24;
}

.progress-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.progress-percent {
  font-size: 14px;
  font-weight: 600;
  color: #a78bfa;
}

.milestone-message {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}
</style>
