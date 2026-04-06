<template>
  <div class="char-card">
    <!-- Avatar area -->
    <div class="char-avatar" :style="{ background: avatarGradient }">
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
}

const props = defineProps<Props>()

const avatarGradient = computed(() => {
  const colors = ['#f59e0b', '#8b5cf6', '#10b981', '#dc2626', '#3b82f6', '#06b6d4']
  const color = colors[props.name.charCodeAt(0) % colors.length]
  return `linear-gradient(135deg, ${color}, ${color}88)`
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
  overflow: hidden;
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
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
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
