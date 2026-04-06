<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-subtitle">NEW WORLD</div>
          <div class="modal-title">创 建 新 世 界</div>
          <div class="gold-line"></div>
        </div>

        <!-- Form -->
        <form class="modal-body" @submit.prevent="handleCreate">
          <!-- World Name -->
          <div class="field-group">
            <label class="field-label">世 界 名 称 <span class="required">*</span></label>
            <input
              v-model="form.name"
              type="text"
              class="galgame-input"
              placeholder="为你的世界命名……"
              maxlength="20"
              required
            />
          </div>

          <!-- World Description -->
          <div class="field-group">
            <label class="field-label">世 界 简 介</label>
            <textarea
              v-model="form.description"
              class="galgame-input"
              rows="2"
              placeholder="描述这个学习世界的氛围与主题……"
              maxlength="200"
            ></textarea>
          </div>

          <!-- Sage Selection -->
          <div class="field-group">
            <label class="field-label">知  者</label>
            <div class="character-section">
              <!-- Horizontal scrollable list -->
              <div class="character-scroll">
                <!-- Available sages -->
                <div
                  v-for="sage in availableSages"
                  :key="sage.id"
                  class="character-chip"
                  :class="{ selected: isSageSelected(sage.id) }"
                  :style="isSageSelected(sage.id) ? { background: `${sage.color}22`, borderColor: sage.color } : {}"
                  @click="toggleSage(sage)"
                >
                  <div class="chip-avatar" :style="{ background: sage.color }">
                    {{ sage.symbol }}
                  </div>
                  <div class="chip-name">{{ sage.name }}</div>
                </div>
              </div>
              <!-- Add custom sage button -->
              <div class="add-custom-btn" @click="goToCharacterPage()">
                <span class="add-icon">+</span>
                <span>自定义知者</span>
              </div>
            </div>
          </div>

          <!-- Traveler Selection -->
          <div class="field-group">
            <label class="field-label">旅  者</label>
            <div class="character-section">
              <!-- Horizontal scrollable list -->
              <div class="character-scroll">
                <!-- Available travelers -->
                <div
                  v-for="traveler in availableTravelers"
                  :key="traveler.id"
                  class="character-chip"
                  :class="{ selected: selectedTraveler?.id === traveler.id }"
                  :style="selectedTraveler?.id === traveler.id ? { background: `${traveler.color}22`, borderColor: traveler.color } : {}"
                  @click="toggleTraveler(traveler)"
                >
                  <div class="chip-avatar" :style="{ background: traveler.color }">
                    {{ traveler.symbol }}
                  </div>
                  <div class="chip-name">{{ traveler.name }}</div>
                </div>
              </div>
              <!-- Add custom traveler button -->
              <div class="add-custom-btn" @click="goToCharacterPage()">
                <span class="add-icon">+</span>
                <span>自定义旅者</span>
              </div>
            </div>
          </div>

          <!-- Submit -->
          <button type="submit" class="submit-btn" :disabled="!form.name.trim() || selectedSageIds.length === 0">
            创 建 世 界
          </button>
        </form>

        <!-- Close hint -->
        <button class="close-hint" @click="$emit('close')">取消</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'

interface Character {
  id: number
  name: string
  title: string
  symbol: string
  color: string
  type: 'sage' | 'traveler'
}

interface Props {
  show: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'create', data: {
    name: string
    description: string
    sageIds: number[]
    travelerId?: number
  }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const router = useRouter()

// Form state
const form = ref({
  name: '',
  description: ''
})

const selectedSageIds = ref<number[]>([])
const selectedTraveler = ref<Character | null>(null)

// Mock available characters (replace with API call)
const availableSages = ref<Character[]>([
  { id: 1, name: '苏格拉底', title: '哲学之父', symbol: '☉', color: '#f59e0b', type: 'sage' },
  { id: 2, name: '柏拉图', title: '理念论者', symbol: '◈', color: '#8b5cf6', type: 'sage' },
  { id: 3, name: '亚里士多德', title: '百科全书', symbol: '◇', color: '#10b981', type: 'sage' },
  { id: 4, name: '孙子', title: '兵圣', symbol: '兵', color: '#dc2626', type: 'sage' },
])

const availableTravelers = ref<Character[]>([
  { id: 101, name: '旅者', title: '求知者', symbol: '✦', color: '#3b82f6', type: 'traveler' },
  { id: 102, name: '行者', title: '探索者', symbol: '◉', color: '#06b6d4', type: 'traveler' },
  { id: 103, name: '学者', title: '研究者', symbol: '◎', color: '#8b5cf6', type: 'traveler' },
])

// Reset form when modal opens
watch(() => props.show, (newVal) => {
  if (newVal) {
    form.value.name = ''
    form.value.description = ''
    selectedSageIds.value = []
    selectedTraveler.value = null
  }
})

const isSageSelected = (id: number) => selectedSageIds.value.includes(id)

const toggleSage = (sage: Character) => {
  const idx = selectedSageIds.value.indexOf(sage.id)
  if (idx === -1) {
    selectedSageIds.value.push(sage.id)
  } else {
    selectedSageIds.value.splice(idx, 1)
  }
}

const toggleTraveler = (traveler: Character) => {
  if (selectedTraveler.value?.id === traveler.id) {
    selectedTraveler.value = null
  } else {
    selectedTraveler.value = traveler
  }
}

const goToCharacterPage = () => {
  router.push('/character')
}

const handleCreate = () => {
  if (!form.value.name.trim() || selectedSageIds.value.length === 0) return
  
  emit('create', {
    name: form.value.name.trim(),
    description: form.value.description.trim(),
    sageIds: selectedSageIds.value,
    travelerId: selectedTraveler.value?.id
  })
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
  width: 640px;
  max-width: 92vw;
  max-height: 90vh;
  overflow-y: auto;
  padding: 28px 40px 24px;
  background: rgba(8, 8, 25, 0.09);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-top: none;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 12px;
}

/* Top gold gradient border - matching login-panel */
.modal-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    to right,
    transparent 0%,
    rgba(255, 215, 0, 0.6) 20%,
    rgba(255, 215, 0, 0.9) 50%,
    rgba(255, 215, 0, 0.6) 80%,
    transparent 100%
  );
  border-radius: 12px 12px 0 0;
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

/* Form styles */
.modal-body {
  display: flex;
  flex-direction: column;
}

/* Override galgame-input to match Login.vue style */
.modal-body .galgame-input {
  background: rgba(0, 0, 0, 0.40) !important;
  border: 2px solid rgba(255, 215, 0, 0.40) !important;
  font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif !important;
  font-size: 14px;
  padding: 12px 14px;
}

.modal-body .galgame-input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 24px;
  padding-left: 0;
  padding-right: 0;
}

.field-label {
  font-family: "Noto Sans SC", sans-serif;
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  letter-spacing: 4px;
}

.required {
  color: #ef4444;
}

/* Character section with horizontal scroll */
.character-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.character-scroll {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 4px 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 215, 0, 0.2) transparent;
}

.character-scroll::-webkit-scrollbar {
  height: 4px;
}

.character-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.character-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 215, 0, 0.2);
  border-radius: 2px;
}

/* Character chip */
.character-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  background: rgba(8, 8, 28, 0.8);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s ease;
  flex-shrink: 0;
  min-width: 72px;
}

.character-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
}

.character-chip.selected {
  padding: 10px 14px;
}

.chip-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: white;
}

.chip-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 1px;
  white-space: nowrap;
}

.character-chip.selected .chip-name {
  color: #ffd700;
}

/* Add custom button */
.add-custom-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px dashed rgba(255, 215, 0, 0.3);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s ease;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 215, 0, 0.5);
  letter-spacing: 2px;
  align-self: flex-start;
}

.add-custom-btn:hover {
  background: rgba(255, 215, 0, 0.05);
  border-color: rgba(255, 215, 0, 0.5);
  color: rgba(255, 215, 0, 0.8);
}

.add-custom-btn .add-icon {
  font-size: 14px;
}

/* Submit button */
.submit-btn {
  font-family: "Noto Sans SC", sans-serif;
  width: 100%;
  padding: 14px 24px;
  font-size: 14px;
  letter-spacing: 6px;
  font-weight: 600;
  color: #0a0a1e;
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 8px;
}

.submit-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffe033, #ffd700);
  box-shadow: 0 4px 20px rgba(255, 215, 0, 0.35);
  transform: translateY(-1px);
}

.submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
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
  margin-top: 10px;
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
