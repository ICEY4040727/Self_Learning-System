<template>
  <div class="char-card">
    <!-- Avatar area -->
    <div class="char-avatar" :style="{ background: avatarColor }">
      <img v-if="avatarUrl" :src="avatarUrl" :alt="name" class="avatar-img" />
      <span v-else class="avatar-placeholder">{{ name?.charAt(0) || '?' }}</span>
    </div>

    <!-- Info -->
    <div class="char-info">
      <div class="char-name">{{ name }}</div>
      <div class="char-title">{{ title }}</div>
      <div class="char-identity">{{ identity }}</div>
    </div>

    <!-- Footer -->
    <div class="char-footer">
      <span class="type-badge">{{ typeLabel }}</span>
      <span class="source-badge">{{ sourceLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  name: string
  title?: string
  identity?: string
  avatarUrl?: string
  type: 'sage' | 'traveler'
  isBuiltin?: boolean
  color?: string
}

const props = defineProps<Props>()

const COLORS = [
  'rgba(245, 158, 11, 0.35)',   // 琥珀色
  'rgba(139, 92, 246, 0.35)',   // 紫色
  'rgba(16, 185, 129, 0.35)',   // 翠绿
  'rgba(220, 38, 38, 0.35)',    // 朱红
  'rgba(59, 130, 246, 0.35)',   // 天蓝
  'rgba(6, 182, 212, 0.35)',    // 青色
]

const avatarColor = computed(() => {
  if (props.color) return props.color
  const idx = (props.name.charCodeAt(0) || 0) % COLORS.length
  return COLORS[idx]
})

const typeLabel = computed(() => props.type === 'sage' ? '知者' : '旅者')
const sourceLabel = computed(() => props.isBuiltin ? '内置' : '自定义')
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

.char-avatar {
  border-radius: 12px 12px 0 0;
  width: 100%;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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

.char-identity {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
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
</style>
