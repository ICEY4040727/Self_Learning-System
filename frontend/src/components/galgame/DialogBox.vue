<template>
  <div class="dialog-box" @click="handleClick">
    <!-- Name tag -->
    <div class="name-tag" :class="{ 'name-tag-user': mode === 'USER_INPUT' }">
      {{ mode === 'USER_INPUT' ? '我' : characterName }}
    </div>

    <!-- Mode: TEACHER_SPEAKING -->
    <div v-if="mode === 'TEACHER_SPEAKING'" class="dialog-content">
      <div class="dialog-text" style="font-family: var(--font-dialogue);">
        <span v-html="displayContent"></span>
        <span v-if="isTyping" class="cursor">▊</span>
      </div>
      <div v-if="!isTyping && displayContent" class="next-indicator">
        {{ hasMoreSegments ? '▼ 下一段' : '▶ 点击继续' }}
      </div>
    </div>

    <!-- Mode: USER_INPUT -->
    <div v-else-if="mode === 'USER_INPUT'" class="dialog-content input-mode">
      <textarea
        ref="inputRef"
        v-model="inputValue"
        class="dialog-input"
        placeholder="输入你的想法..."
        rows="2"
        @keydown.enter.exact.prevent="handleSend"
        @click.stop
      ></textarea>
      <button class="send-btn" @click.stop="handleSend" :disabled="!inputValue.trim()">→</button>
    </div>

    <!-- Mode: CHOICES -->
    <div v-else-if="mode === 'CHOICES'" class="dialog-content">
      <div class="dialog-text" style="font-family: var(--font-dialogue);">
        <span v-html="displayContent"></span>
      </div>
      <div class="choices-list">
        <button
          v-for="(choice, i) in choices"
          :key="i"
          class="choice-item"
          :style="{ animationDelay: `${i * 0.1}s` }"
          @click.stop="$emit('select-choice', choice)"
        >
          ▸ {{ choice }}
        </button>
      </div>
    </div>

    <!-- Mode: WAITING -->
    <div v-else-if="mode === 'WAITING'" class="dialog-content">
      <div class="dialog-text waiting-text" style="font-family: var(--font-dialogue);">
        ……
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'

const props = defineProps<{
  mode: 'TEACHER_SPEAKING' | 'USER_INPUT' | 'CHOICES' | 'WAITING'
  characterName: string
  hasMoreSegments?: boolean
  displayContent?: string
  isTyping?: boolean
  choices?: string[]
}>()

const emit = defineEmits<{
  'click-next': []
  'send-message': [message: string]
  'select-choice': [choice: string]
  'skip-typing': []
}>()

const inputValue = ref('')
const inputRef = ref<HTMLTextAreaElement | null>(null)

// Auto-focus input when switching to USER_INPUT mode
watch(() => props.mode, (newMode) => {
  if (newMode === 'USER_INPUT') {
    nextTick(() => inputRef.value?.focus())
  }
})

const handleClick = () => {
  if (props.mode === 'TEACHER_SPEAKING') {
    if (props.isTyping) {
      emit('skip-typing')
    } else {
      emit('click-next')
    }
  }
}

const handleSend = () => {
  if (!inputValue.value.trim()) return
  emit('send-message', inputValue.value.trim())
  inputValue.value = ''
}
</script>

<style scoped>
.dialog-box {
  background: var(--bg-panel);
  border: 1px solid var(--border-accent);
  border-radius: 4px;
  padding: 20px 24px;
  min-height: 160px;
  max-height: 240px;
  position: relative;
  cursor: pointer;
  box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.5);
  animation: slideUp var(--transition-normal);
  overflow-y: auto;
}

/* Name tag */
.name-tag {
  position: absolute;
  top: -14px;
  left: 20px;
  background: linear-gradient(135deg, var(--accent-gold), var(--accent-orange));
  color: var(--bg-primary);
  padding: 3px 16px;
  font-family: var(--font-ui);
  font-weight: bold;
  font-size: 14px;
  transform: skewX(-8deg);
}

.name-tag-user {
  background: linear-gradient(135deg, var(--emotion-positive), #6aba6a);
  color: var(--text-primary);
}

/* Dialog text */
.dialog-text {
  color: var(--text-primary);
  font-size: 17px;
  line-height: 1.9;
  white-space: pre-wrap;
  margin-top: 4px;
}

.waiting-text {
  color: var(--text-muted);
  animation: breathe 2s ease-in-out infinite;
}

.cursor {
  animation: blink 1s infinite;
  color: var(--accent-gold);
  margin-left: 2px;
}

.next-indicator {
  text-align: right;
  color: var(--text-muted);
  font-size: 12px;
  font-family: var(--font-ui);
  margin-top: 8px;
  animation: breathe 2s ease-in-out infinite;
}

/* User input mode */
.input-mode {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.dialog-input {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  color: var(--text-primary);
  font-family: var(--font-dialogue);
  font-size: 16px;
  line-height: 1.8;
  padding: 10px 14px;
  resize: none;
  outline: none;
  transition: border-color var(--transition-fast);
}

.dialog-input:focus {
  border-color: var(--accent-gold);
}

.dialog-input::placeholder {
  color: var(--text-muted);
}

.send-btn {
  width: 44px;
  height: 44px;
  background: var(--accent-gold);
  color: var(--bg-primary);
  border: none;
  border-radius: 50%;
  font-size: 20px;
  font-weight: bold;
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.1);
  box-shadow: 0 0 12px rgba(255, 215, 0, 0.4);
}

.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Choices */
.choices-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 14px;
}

.choice-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-subtle);
  border-radius: 4px;
  color: var(--text-primary);
  font-family: var(--font-ui);
  font-size: 15px;
  padding: 10px 16px;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
  animation: slideInChoice var(--transition-normal) both;
}

@keyframes slideInChoice {
  from { transform: translateX(20px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.choice-item:hover {
  border-color: var(--accent-gold);
  transform: translateX(6px);
  background: rgba(255, 215, 0, 0.08);
}

/* Mobile */
@media (max-width: 768px) {
  .dialog-box {
    padding: 16px 18px;
    min-height: 140px;
  }
  .dialog-text {
    font-size: 15px;
  }
}
</style>
