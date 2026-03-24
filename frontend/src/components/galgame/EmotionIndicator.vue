<template>
  <div class="emotion-indicator">
    <div class="stage-label">
      关系阶段: <span class="stage-name">{{ stageName }}</span>
    </div>
    <div class="progress-bar">
      <div
        class="progress-fill"
        :style="{ width: progressPercent + '%' }"
      ></div>
    </div>
    <div class="stage-icons">
      <span
        v-for="s in stages"
        :key="s"
        class="stage-icon"
        :class="{ active: stages.indexOf(stage) >= stages.indexOf(s) }"
      >
        {{ getStageEmoji(s) }}
      </span>
    </div>
    <div v-if="emotion && emotion !== 'neutral'" class="current-emotion">
      <span class="emotion-dot" :class="emotionClass"></span>
      {{ emotionLabel }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  stage: string
  emotion?: string
}>()

const stages = ['stranger', 'acquaintance', 'friend', 'mentor', 'partner']

const stageNames: Record<string, string> = {
  stranger: '陌生人',
  acquaintance: '认识',
  friend: '朋友',
  mentor: '导师',
  partner: '伙伴'
}

const emotionLabels: Record<string, string> = {
  curiosity: '好奇',
  confusion: '困惑',
  frustration: '沮丧',
  excitement: '兴奋',
  satisfaction: '满足',
  boredom: '无聊',
  anxiety: '焦虑',
  neutral: '平静',
}

const emotionClasses: Record<string, string> = {
  curiosity: 'positive',
  excitement: 'positive',
  satisfaction: 'positive',
  confusion: 'negative',
  frustration: 'negative',
  anxiety: 'negative',
  boredom: 'negative',
  neutral: 'neutral',
}

const stageName = computed(() => stageNames[props.stage] || '陌生人')

const progressPercent = computed(() => {
  const idx = stages.indexOf(props.stage)
  return Math.min(100, ((idx + 1) / stages.length) * 100)
})

const emotionLabel = computed(() =>
  props.emotion ? emotionLabels[props.emotion] || '' : ''
)

const emotionClass = computed(() =>
  props.emotion ? emotionClasses[props.emotion] || 'neutral' : 'neutral'
)

const getStageEmoji = (stage: string) => {
  const emojis: Record<string, string> = {
    stranger: '👤',
    acquaintance: '🙂',
    friend: '😊',
    mentor: '📚',
    partner: '🤝'
  }
  return emojis[stage] || '👤'
}
</script>

<style scoped>
.emotion-indicator {
  background: rgba(0, 0, 0, 0.7);
  padding: 15px;
  border-radius: 10px;
  border: 1px solid #4a4a8a;
}

.stage-label {
  margin-bottom: 10px;
  font-size: 14px;
}

.stage-name {
  color: #ffd700;
  font-weight: bold;
}

.progress-bar {
  height: 8px;
  background: #2a2a4a;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4a8a4a, #ffd700);
  transition: width 0.5s ease;
}

.stage-icons {
  display: flex;
  justify-content: space-between;
}

.stage-icon {
  font-size: 24px;
  opacity: 0.4;
  transition: all 0.3s;
}

.stage-icon.active {
  opacity: 1;
  transform: scale(1.2);
}

.current-emotion {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #3a3a6a;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #ccc;
}

.emotion-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.emotion-dot.positive {
  background: #4adf6a;
  box-shadow: 0 0 4px #4adf6a;
}

.emotion-dot.negative {
  background: #df6a4a;
  box-shadow: 0 0 4px #df6a4a;
}

.emotion-dot.neutral {
  background: #8a8aaa;
}
</style>
