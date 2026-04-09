<template>
  <div class="session-history">
    <div v-if="sessions.length > 0" class="sessions-list">
      <div
        v-for="session in sessions"
        :key="session.id"
        class="session-item"
        :class="{ active: !session.ended_at }"
        @click="$emit('select', session)"
      >
        <div class="session-indicator">
          <span v-if="!session.ended_at" class="active-dot"></span>
        </div>
        <div class="session-content">
          <div class="session-header">
            <span class="session-time">{{ formatSessionTime(session.started_at) }}</span>
            <span v-if="!session.ended_at" class="session-badge">进行中</span>
          </div>
          <div class="session-details">
            <span class="session-stage">{{ stageLabel(session.relationship_stage) }}</span>
            <span v-if="session.message_count" class="session-messages">
              {{ session.message_count }} 条消息
            </span>
          </div>
          <div v-if="session.ended_at && session.duration" class="session-duration">
            时长: {{ formatDuration(session.duration) }}
          </div>
        </div>
        <div class="session-arrow">
          <span v-if="!session.ended_at">继续 ▸</span>
          <span v-else>回顾 ▸</span>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">
      <div class="empty-icon">📝</div>
      <div class="empty-text">暂无会话记录</div>
      <div class="empty-hint">开始学习后，这里将显示你的会话历史</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RELATIONSHIP_STAGE_LABELS } from '@/constants/courseLevels'

interface Session {
  id: number
  started_at: string
  ended_at?: string
  relationship_stage?: string
  message_count?: number
  duration?: number  // minutes
  course_name?: string
}

defineProps<{
  sessions: Session[]
}>()

defineEmits<{
  select: [session: Session]
}>()

const stageLabel = (stage?: string) => {
  if (!stage) return '未知'
  return RELATIONSHIP_STAGE_LABELS[stage] || stage
}

const formatSessionTime = (startedAt: string) => {
  if (!startedAt) return '未知时间'
  const date = new Date(startedAt)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(hours / 24)

  const timeStr = date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })

  if (days === 0) return `今天 ${timeStr}`
  if (days === 1) return `昨天 ${timeStr}`
  if (days < 7) return `${days}天前 ${timeStr}`
  return date.toLocaleDateString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatDuration = (minutes: number) => {
  if (minutes < 60) return `${minutes}分钟`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}小时${mins}分钟` : `${hours}小时`
}
</script>

<style scoped>
.session-history {
  width: 100%;
}

.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(167, 139, 250, 0.3);
  transform: translateX(4px);
}

.session-item.active {
  border-color: rgba(74, 222, 106, 0.4);
  background: rgba(74, 222, 106, 0.05);
}

.session-indicator {
  flex-shrink: 0;
  width: 20px;
  display: flex;
  justify-content: center;
  padding-top: 4px;
}

.active-dot {
  width: 8px;
  height: 8px;
  background: #4adf6a;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.session-time {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
}

.session-badge {
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(74, 222, 106, 0.2);
  color: #4adf6a;
  border-radius: 4px;
  font-weight: 600;
}

.session-details {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.session-stage {
  color: #a78bfa;
}

.session-messages {
  color: rgba(255, 255, 255, 0.5);
}

.session-duration {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.session-arrow {
  flex-shrink: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
  align-self: center;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 6px;
}

.empty-hint {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.3);
}
</style>
