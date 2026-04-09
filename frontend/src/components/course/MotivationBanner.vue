<template>
  <div v-if="motivation" class="motivation-banner">
    <div class="motivation-icon">💡</div>
    <div class="motivation-content">
      <div class="motivation-label">我学这门课是为了：{{ motivationLabel }}</div>
      <div v-if="motivationDetail" class="motivation-detail">"{{ motivationDetail }}"</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { MOTIVATION_LABELS } from '@/constants/courseLevels'

const props = defineProps<{
  motivation?: string
  motivationDetail?: string
}>()

const motivationLabel = computed(() => {
  if (!props.motivation) return ''
  return MOTIVATION_LABELS[props.motivation] || props.motivation
})
</script>

<style scoped>
.motivation-banner {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(251, 191, 36, 0.05));
  border: 1px solid rgba(251, 191, 36, 0.2);
  border-radius: 12px;
}

.motivation-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.motivation-content {
  flex: 1;
}

.motivation-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
}

.motivation-detail {
  margin-top: 4px;
  font-size: 14px;
  color: #fbbf24;
  font-style: italic;
}
</style>
