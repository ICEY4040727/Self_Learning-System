<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-subtitle">{{ isSage ? 'NEW SAGE' : 'NEW TRAVELER' }}</div>
          <div class="modal-title">{{ isSage ? '创 建 新 知 者' : '创 建 新 旅 者' }}</div>
          <div class="gold-line"></div>
        </div>

        <!-- Step 0: Choose Identity (only show if not editing) -->
        <div v-if="!isEdit && currentPhase === 'choose'" class="phase-content">
          <h3 class="phase-title">选择你的身份</h3>
          <p class="phase-desc">你是来学习的旅者，还是指导他人的知者？</p>
          
          <div class="identity-cards">
            <div 
              class="identity-card"
              @click="selectType('traveler')"
            >
              <span class="identity-icon">🧭</span>
              <span class="identity-title">旅者</span>
              <span class="identity-desc">这是我自己。代表我在世界里探索的化身。</span>
            </div>
            <div 
              class="identity-card"
              @click="selectType('sage')"
            >
              <span class="identity-icon">📖</span>
              <span class="identity-title">知者</span>
              <span class="identity-desc">一位老师/同伴/灵感来源，会陪我学习。</span>
            </div>
          </div>
        </div>

        <!-- Sage Flow -->
        <SageCreateFlow 
          v-else-if="isSage"
          @create="handleCreate"
        />

        <!-- Traveler Flow -->
        <TravelerCreateFlow 
          v-else-if="!isSage"
          @create="handleCreate"
        />

        <button class="close-hint" @click="$emit('close')">取消</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import SageCreateFlow from './SageCreateFlow.vue'
import TravelerCreateFlow from './TravelerCreateFlow.vue'

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

const currentPhase = ref<'choose' | 'flow'>('choose')

const isEdit = computed(() => !!props.editCharacter)
const isSage = computed(() => props.editCharacter?.type ?? props.defaultType === 'sage')

watch(() => props.show, (newVal) => {
  if (newVal) {
    // 编辑模式直接进入 flow
    currentPhase.value = isEdit.value ? 'flow' : 'choose'
  }
})

const selectType = (_type: 'sage' | 'traveler') => {
  currentPhase.value = 'flow'
}

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

/* Identity Phase */
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

/* Transitions */
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
