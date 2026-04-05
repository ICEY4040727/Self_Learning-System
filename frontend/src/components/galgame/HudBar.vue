<template>
  <div class="hud-bar galgame-hud">
    <div class="hud-left">
      <button class="hud-btn galgame-hud-btn" @click="$emit('save')">💾 存档</button>
      <button class="hud-btn galgame-hud-btn" @click="$emit('load')">📂 读档</button>
      <button class="hud-btn galgame-hud-btn" @click="$emit('skip')">⏩ 跳过</button>
      <button
        class="hud-btn galgame-hud-btn"
        :class="{ 'hud-btn-active': isAuto, active: isAuto }"
        @click="$emit('toggle-auto')"
      >▶ 自动</button>
      <button class="hud-btn galgame-hud-btn" @click="$emit('backlog')">📖 回忆</button>
      <button class="hud-btn galgame-hud-btn" @click="$emit('knowledge-graph')">📊 图谱</button>
      <button class="hud-btn galgame-hud-btn" @click="$emit('toggle-ui')">🙈 隐藏UI</button>
      <button class="hud-btn galgame-hud-btn" @click="$emit('settings')">⚙ 设置</button>
      <button class="hud-btn galgame-hud-btn" @click="$emit('exit')">🏠 主页</button>
    </div>
    <div class="hud-right">
      <slot name="status">
        <span class="hud-status">{{ emotionLabel }} │ {{ stageLabel }} │ {{ mastery }}%</span>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  emotion?: string
  stage?: string
  mastery?: number
  isAuto?: boolean
}>()

defineEmits<{
  save: []
  load: []
  skip: []
  'toggle-auto': []
  backlog: []
  'knowledge-graph': []
  'toggle-ui': []
  settings: []
  exit: []
}>()

const EMOTION_LABELS: Record<string, string> = {
  curiosity: '好奇', confusion: '困惑', frustration: '沮丧',
  excitement: '兴奋', satisfaction: '满足', boredom: '无聊',
  anxiety: '焦虑', neutral: '平静',
}

const STAGE_LABELS: Record<string, string> = {
  stranger: '陌生人', acquaintance: '熟人', friend: '朋友',
  mentor: '导师', partner: '伙伴',
}

const emotionLabel = computed(() => EMOTION_LABELS[props.emotion || 'neutral'] || '平静')
const stageLabel = computed(() => STAGE_LABELS[props.stage || 'stranger'] || '陌生人')
const mastery = computed(() => props.mastery ?? 0)
</script>

<style scoped>
.hud-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 12px;
  z-index: 30;
  font-family: var(--font-ui);
}

.hud-left, .hud-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.hud-btn {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: var(--radius-hud-btn);
  transition: color var(--transition-fast), border-color var(--transition-fast);
  white-space: nowrap;
}

.hud-btn:hover {
  color: var(--accent-gold);
}

.hud-btn-active {
  color: var(--emotion-positive);
}

.hud-status {
  color: var(--text-muted);
  font-size: 12px;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .hud-btn {
    font-size: 11px;
    padding: 4px 6px;
  }
  .hud-status {
    font-size: 11px;
  }
}
</style>
