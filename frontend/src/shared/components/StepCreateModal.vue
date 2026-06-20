<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-subtitle">{{ isSage ? 'NEW SAGE' : 'NEW TRAVELER' }}</div>
          <div class="modal-title">{{ isSage ? '创建新角色' : '创建新旅者' }}</div>
          <div class="gold-line"></div>
        </div>

        <!-- Sage Flow -->
        <SageCreateFlow
          v-if="isSage"
          @create="handleCreate"
        />

        <!-- Traveler Flow -->
        <TravelerCreateFlow
          v-else
          @create="handleCreate"
        />

        <button class="close-hint" @click="$emit('close')">取消</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SageCreateFlow from '@/characters/components/SageCreateFlow.vue'
import TravelerCreateFlow from '@/characters/components/TravelerCreateFlow.vue'

interface Props {
  show: boolean
  defaultType?: 'sage' | 'traveler'
  editCharacter?: {
    id: number
    name: string
    title?: string
    description?: string
    avatar?: string
    type: 'sage' | 'traveler'
    personality?: string
    tags?: string[]
  } | null
}

interface Emits {
  (e: 'close'): void
  (e: 'create', data: any): void
  (e: 'update', data: any): void
}

const props = withDefaults(defineProps<Props>(), { defaultType: 'sage' })
const emit = defineEmits<Emits>()

const isSage = computed(() => (props.editCharacter?.type ?? props.defaultType) === 'sage')

const handleCreate = (data: any) => {
  emit('create', data)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-box {
  position: relative;
  width: 580px;
  max-width: 92vw;
  max-height: 90vh;
  overflow-y: auto;
  padding: 28px 40px 24px;
  background: rgba(8, 8, 25, 0.98);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-top: none;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 12px;
}

.modal-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(to right, transparent 0%, rgba(255, 215, 0, 0.6) 20%, rgba(255, 215, 0, 0.9) 50%, rgba(255, 215, 0, 0.6) 80%, transparent 100%);
}

.modal-header {
  text-align: center;
  margin-bottom: 24px;
}

.modal-subtitle {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.25);
  margin-bottom: 8px;
}

.modal-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 18px;
  letter-spacing: 6px;
  color: #ffd700;
}

.gold-line {
  width: 120px;
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(255, 215, 0, 0.4), transparent);
  margin: 12px auto 0;
}

.phase-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.phase-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 18px;
  color: #ffd700;
  text-align: center;
  margin-bottom: 8px;
}

.phase-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
  margin-bottom: 28px;
}

.identity-cards {
  display: flex;
  gap: 20px;
}

.identity-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 20px;
  background: rgba(0, 0, 0, 0.4);
  border: 2px solid rgba(255, 215, 0, 0.15);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.identity-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
}

.identity-icon {
  font-size: 48px;
}

.identity-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #ffd700;
  letter-spacing: 4px;
}

.identity-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.6;
}

.close-hint {
  font-family: "Noto Sans SC", sans-serif;
  width: 100%;
  padding: 10px;
  font-size: 12px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.3);
  background: transparent;
  border: none;
  cursor: pointer;
  margin-top: 16px;
  transition: color 0.2s ease;
}

.close-hint:hover {
  color: rgba(255, 255, 255, 0.5);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-box,
.modal-fade-leave-active .modal-box {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.modal-fade-enter-from .modal-box,
.modal-fade-leave-to .modal-box {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}
</style>
