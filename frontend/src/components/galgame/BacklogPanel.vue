<template>
  <Transition name="backlog-slide">
    <div v-if="visible" class="backlog-overlay" @click="$emit('close')">
      <div class="backlog-panel galgame-panel" @click.stop>
        <h3 class="backlog-title">📖 回忆录</h3>
        <div class="backlog-list galgame-scrollbar" ref="listRef">
          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="['backlog-entry', msg.sender_type]"
          >
            <span class="backlog-sender">
              {{ msg.sender_type === 'teacher' ? teacherName : '我' }}
            </span>
            <p class="backlog-text">{{ msg.content }}</p>
          </div>
          <div v-if="messages.length === 0" class="backlog-empty">
            暂无对话记录
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

interface Message {
  id: number
  sender_type: 'user' | 'teacher'
  content: string
}

const props = defineProps<{
  visible: boolean
  messages: Message[]
  teacherName: string
}>()

defineEmits<{ close: [] }>()

const listRef = ref<HTMLElement | null>(null)

// Scroll to bottom when opened
watch(() => props.visible, (v) => {
  if (v) {
    nextTick(() => {
      if (listRef.value) {
        listRef.value.scrollTop = listRef.value.scrollHeight
      }
    })
  }
})
</script>

<style scoped>
.backlog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}

.backlog-panel {
  width: min(360px, 90vw);
  height: 100%;
  border-radius: 0;
  border-right: none;
  padding: 20px;
}

.backlog-title {
  color: var(--accent-gold);
  font-family: var(--font-ui);
  font-size: 18px;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.backlog-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.backlog-entry {
  padding: 10px 14px;
  border-radius: 4px;
}

.backlog-entry.teacher {
  background: rgba(255, 215, 0, 0.05);
  border-left: 3px solid var(--accent-gold);
}

.backlog-entry.user {
  background: rgba(74, 138, 74, 0.08);
  border-left: 3px solid var(--emotion-positive);
}

.backlog-sender {
  display: block;
  font-family: var(--font-ui);
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.backlog-entry.teacher .backlog-sender {
  color: var(--accent-gold);
}

.backlog-text {
  font-family: var(--font-dialogue);
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.7;
  white-space: pre-wrap;
}

.backlog-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 40px 0;
}

/* Slide transition from right */
.backlog-slide-enter-from .backlog-panel {
  transform: translateX(100%);
}
.backlog-slide-enter-active .backlog-panel {
  transition: transform var(--transition-normal);
}
.backlog-slide-leave-to .backlog-panel {
  transform: translateX(100%);
}
.backlog-slide-leave-active .backlog-panel {
  transition: transform 0.24s ease;
}

@media (max-width: 768px) {
  .backlog-panel {
    width: 85%;
  }
}
</style>
