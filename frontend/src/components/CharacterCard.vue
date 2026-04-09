<template>
  <div class="char-card" @click="$emit('click')">
    <!-- Avatar area -->
    <div class="char-avatar" :style="{ background: avatarColor }">
      <img v-if="avatar" :src="avatar" :alt="name" class="avatar-img" />
      <span v-else class="avatar-placeholder">{{ name?.charAt(0) || '?' }}</span>
    </div>

    <!-- Info -->
    <div class="char-info">
      <div class="char-name">{{ name }}</div>
      <div class="char-title">{{ title }}</div>
    </div>

    <!-- Footer -->
    <div class="char-footer">
      <span class="type-badge">{{ typeLabel }}</span>
      <span class="source-badge">{{ isBuiltin ? '内置' : '自定义' }}</span>
    </div>

    <!-- Action buttons (show on hover) -->
    <div class="char-actions">
      <button class="action-btn edit-btn" @click.stop="$emit('edit')" title="编辑角色">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
      </button>
      <button v-if="!isBuiltin" class="action-btn delete-btn" @click.stop="$emit('delete')" title="删除角色">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          <line x1="10" y1="11" x2="10" y2="17"></line>
          <line x1="14" y1="11" x2="14" y2="17"></line>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  name: string
  title?: string
  avatar?: string
  type: 'sage' | 'traveler'
  isBuiltin?: boolean
  color?: string
}

const props = defineProps<Props>()
defineEmits<{
  click: []
  edit: []
  delete: []
}>()

const COLORS = [
  'rgba(245, 158, 11, 0.35)',
  'rgba(139, 92, 246, 0.35)',
  'rgba(16, 185, 129, 0.35)',
  'rgba(220, 38, 38, 0.35)',
  'rgba(59, 130, 246, 0.35)',
  'rgba(6, 182, 212, 0.35)',
]

const avatarColor = computed(() => {
  if (props.color) return props.color
  const idx = (props.name.charCodeAt(0) || 0) % COLORS.length
  return COLORS[idx]
})

const typeLabel = computed(() => props.type === 'sage' ? '知者' : '旅者')
</script>

<style scoped>
.char-card {
  display: flex;
  flex-direction: column;
  width: 160px;
  background: transparent;
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 12px;
  overflow: visible;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
}

.char-card:hover {
  border-color: rgba(255, 215, 0, 0.55);
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(255, 215, 0, 0.15);
}

.char-card:hover .char-actions {
  opacity: 1;
  transform: translateY(0);
}

.char-avatar {
  border-radius: 12px 12px 0 0;
  width: 100%;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.char-card:hover .avatar-img {
  transform: scale(1.05);
}

.avatar-placeholder {
  font-size: 36px;
  font-weight: 700;
  color: #ffd700;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
}

.char-info {
  padding: 12px 12px 8px;
  text-align: center;
}

.char-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: #ffd700;
  letter-spacing: 2px;
  margin-bottom: 4px;
}

.char-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 2px;
}

.char-footer {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  border-top: 1px solid rgba(255, 215, 0, 0.1);
}

.type-badge,
.source-badge {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 1px;
}

/* Action buttons - 精致设计 */
.char-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 8px;
  opacity: 0;
  transform: translateY(-4px);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;
}

.char-card:hover .char-actions {
  opacity: 1;
  transform: translateY(0);
}

.action-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.action-btn svg {
  transition: all 0.2s ease;
}

.edit-btn {
  background: rgba(30, 41, 59, 0.85);
  color: #60a5fa;
}

.edit-btn:hover {
  background: rgba(59, 130, 246, 0.9);
  color: white;
  border-color: transparent;
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.edit-btn:hover svg {
  transform: rotate(-5deg);
}

.delete-btn {
  background: rgba(30, 41, 59, 0.85);
  color: #f87171;
}

.delete-btn:hover {
  background: rgba(220, 38, 38, 0.9);
  color: white;
  border-color: transparent;
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4);
}

/* Entry animation */
.char-card {
  animation: cardEntry 0.4s ease backwards;
}

@keyframes cardEntry {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
