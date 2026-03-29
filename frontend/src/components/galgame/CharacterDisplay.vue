<template>
  <div class="character-display" :class="position" :key="jumpKey" :style="jumpKey > 0 ? { animation: 'jumpOnce 0.3s ease' } : {}">
    <Transition name="sprite-switch" mode="out-in">
      <img
        v-if="spriteUrl"
        :key="spriteUrl"
        :src="spriteUrl"
        :alt="name"
        class="character-image"
        :class="{ 'flipped': position === 'right' }"
        @error="spriteError = true"
      />
      <div v-else class="character-placeholder">
        <div class="placeholder-avatar" :class="expressionClass">
          {{ name?.[0] || '?' }}
        </div>
        <div class="placeholder-expression">{{ expressionLabel }}</div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  name?: string
  sprites?: Record<string, string>  // {"default": "url", "happy": "url", ...}
  expression?: string               // "default" | "happy" | "thinking" | "concerned"
  position?: 'left' | 'center' | 'right'
}>()

const spriteError = ref(false)

const currentExpression = computed(() => props.expression || 'default')

const jumpKey = ref(0)

// Reset error and trigger jump when expression changes
watch(currentExpression, () => {
  spriteError.value = false
  jumpKey.value++
})

const spriteUrl = computed(() => {
  if (spriteError.value) return null
  if (!props.sprites) return null

  // Try exact expression match, fallback to default
  return props.sprites[currentExpression.value]
    || props.sprites['default']
    || null
})

// Expression visual feedback on placeholder (when no sprites)
const EXPRESSION_LABELS: Record<string, string> = {
  default: '',
  happy: '😊',
  thinking: '🤔',
  concerned: '😟',
}

const expressionLabel = computed(() => EXPRESSION_LABELS[currentExpression.value] || '')

const expressionClass = computed(() => `expr-${currentExpression.value}`)
</script>

<style scoped>
.character-display {
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.character-display.left {
  justify-content: flex-start;
}

.character-display.right {
  justify-content: flex-end;
}

.character-image {
  max-height: 70vh;
  max-width: 300px;
  object-fit: contain;
  filter: drop-shadow(0 4px 20px rgba(0, 0, 0, 0.5));
  transition: filter var(--transition-normal);
}

.character-image.flipped {
  transform: scaleX(-1);
}

/* Sprite switch transition */
.sprite-switch-enter-active,
.sprite-switch-leave-active {
  transition: opacity 0.2s ease;
}

.sprite-switch-enter-from,
.sprite-switch-leave-to {
  opacity: 0;
}

/* Placeholder (no sprites available) */
.character-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.placeholder-avatar {
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, #4a4a8a, #2a2a4a);
  border: 3px solid var(--accent-gold);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  color: var(--accent-gold);
  box-shadow: 0 0 30px rgba(255, 215, 0, 0.2);
  transition: all var(--transition-normal);
}

/* Expression variants on placeholder */
.placeholder-avatar.expr-happy {
  border-color: var(--emotion-positive);
  box-shadow: 0 0 30px rgba(74, 223, 106, 0.2);
}

.placeholder-avatar.expr-thinking {
  border-color: var(--emotion-thinking);
  box-shadow: 0 0 30px rgba(96, 165, 250, 0.2);
}

.placeholder-avatar.expr-concerned {
  border-color: var(--emotion-negative);
  box-shadow: 0 0 30px rgba(223, 74, 74, 0.2);
}

.placeholder-expression {
  font-size: 24px;
  height: 30px;
}

@media (max-width: 768px) {
  .character-image {
    max-height: 50vh;
    max-width: 200px;
  }
  .placeholder-avatar {
    width: 80px;
    height: 80px;
    font-size: 32px;
  }
}

@keyframes jumpOnce {
  0% { transform: translateY(0); }
  40% { transform: translateY(-15px); }
  100% { transform: translateY(0); }
}
</style>
