<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-subtitle">NEW COURSE</div>
          <div class="modal-title">创 建 课 程</div>
          <div class="gold-line"></div>
          
          <!-- Step Indicator -->
          <div class="step-indicator">
            <div 
              v-for="step in 4" 
              :key="step"
              class="step-dot"
              :class="{ active: currentStep === step, completed: currentStep > step }"
            >
              <span v-if="currentStep > step">✓</span>
              <span v-else>{{ step }}</span>
            </div>
          </div>
          <div class="step-label">
            <span v-if="currentStep === 1">选择学科</span>
            <span v-else-if="currentStep === 2">设定目标</span>
            <span v-else-if="currentStep === 3">学习节奏</span>
            <span v-else>确认创建</span>
          </div>
        </div>

        <!-- Step 1: Domain Selection -->
        <form v-if="currentStep === 1" class="modal-body step-content" @submit.prevent="goToStep2">
          <div class="field-group">
            <label class="field-label">课 程 名 称 <span class="required">*</span></label>
            <input
              v-model="form.name"
              type="text"
              class="galgame-input"
              placeholder="为你的课程命名……"
              maxlength="30"
              required
            />
          </div>

          <div class="field-group">
            <label class="field-label">学 科 领 域 <span class="required">*</span></label>
            <div class="domain-grid">
              <div
                v-for="domain in COURSE_DOMAINS"
                :key="domain.key"
                class="domain-card"
                :class="{ selected: form.domain === domain.key }"
                :style="{ '--domain-color': domain.color }"
                @click="form.domain = domain.key"
              >
                <span class="domain-icon">{{ domain.icon }}</span>
                <span class="domain-name">{{ domain.name }}</span>
              </div>
            </div>
          </div>

          <button type="submit" class="submit-btn" :disabled="!form.name.trim() || !form.domain">
            下 一 步
          </button>
        </form>

        <!-- Step 2: Target Levels -->
        <div v-else-if="currentStep === 2" class="modal-body step-content">
          <div class="field-group">
            <label class="field-label">你 的 起 点</label>
            <div class="level-grid">
              <button
                v-for="level in CURRENT_LEVELS"
                :key="level.key"
                type="button"
                class="level-card"
                :class="{ selected: form.currentLevel === level.key }"
                @click="form.currentLevel = level.key"
              >
                <span class="level-label">{{ level.label }}</span>
                <span class="level-desc">{{ level.description }}</span>
              </button>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">学 习 目 标</label>
            <div class="level-grid">
              <button
                v-for="level in TARGET_LEVELS"
                :key="level.key"
                type="button"
                class="level-card"
                :class="{ selected: form.targetLevel === level.key }"
                @click="form.targetLevel = level.key"
              >
                <span class="level-label">{{ level.label }}</span>
                <span class="level-desc">{{ level.description }}</span>
              </button>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">学 习 动 机</label>
            <div class="motivation-grid">
              <button
                v-for="m in MOTIVATIONS"
                :key="m.key"
                type="button"
                class="motivation-chip"
                :class="{ selected: form.motivation === m.key }"
                @click="form.motivation = m.key"
              >
                <span>{{ m.icon }}</span>
                <span>{{ m.label }}</span>
              </button>
            </div>
          </div>

          <div class="btn-row">
            <button type="button" class="back-btn" @click="currentStep = 1">上一步</button>
            <button type="button" class="submit-btn" @click="goToStep3">下一步</button>
          </div>
        </div>

        <!-- Step 3: Pace & Time -->
        <div v-else-if="currentStep === 3" class="modal-body step-content">
          <div class="field-group">
            <label class="field-label">学 习 节 奏</label>
            <div class="pace-grid">
              <button
                v-for="pace in PACES"
                :key="pace.key"
                type="button"
                class="pace-card"
                :class="{ selected: form.pace === pace.key }"
                @click="form.pace = pace.key"
              >
                <span class="pace-label">{{ pace.label }}</span>
                <span class="pace-desc">{{ pace.description }}</span>
              </button>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">每 周 时 长</label>
            <div class="minutes-grid">
              <button
                v-for="mins in WEEKLY_MINUTES_OPTIONS"
                :key="mins"
                type="button"
                class="minutes-chip"
                :class="{ selected: form.weeklyMinutes === mins }"
                @click="form.weeklyMinutes = mins"
              >
                {{ mins }}分钟
              </button>
              <button
                type="button"
                class="minutes-chip"
                :class="{ selected: form.weeklyMinutes === null }"
                @click="form.weeklyMinutes = null"
              >
                暂不设定
              </button>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">课 程 简 介</label>
            <textarea
              v-model="form.description"
              class="galgame-input"
              rows="3"
              placeholder="详细描述你的学习目标……（可选）"
              maxlength="200"
            ></textarea>
          </div>

          <div class="btn-row">
            <button type="button" class="back-btn" @click="currentStep = 2">上一步</button>
            <button type="button" class="submit-btn" @click="currentStep = 4">预览</button>
          </div>
        </div>

        <!-- Step 4: Preview & Confirm -->
        <div v-else-if="currentStep === 4" class="modal-body step-content">
          <div class="preview-section">
            <div class="preview-card">
              <div class="preview-header" :style="{ background: selectedDomain?.color || '#6b7280' }">
                <span class="preview-domain-icon">{{ selectedDomain?.icon }}</span>
                <span class="preview-domain-name">{{ selectedDomain?.name }}</span>
              </div>
              <div class="preview-body">
                <div class="preview-name">{{ form.name || '未命名课程' }}</div>
                
                <div class="preview-row">
                  <span class="preview-label">起点</span>
                  <span class="preview-value">{{ currentLevelLabel }}</span>
                </div>
                <div class="preview-arrow">↓</div>
                <div class="preview-row">
                  <span class="preview-label">目标</span>
                  <span class="preview-value target">{{ targetLevelLabel }}</span>
                </div>
                
                <div v-if="form.motivation" class="preview-row">
                  <span class="preview-label">动机</span>
                  <span class="preview-value">{{ motivationLabel }}</span>
                </div>
                
                <div v-if="form.weeklyMinutes" class="preview-row">
                  <span class="preview-label">每周</span>
                  <span class="preview-value">{{ form.weeklyMinutes }} 分钟</span>
                </div>
                
                <div v-if="form.description" class="preview-desc">
                  {{ form.description }}
                </div>
              </div>
            </div>
          </div>

          <div class="btn-row">
            <button type="button" class="back-btn" @click="currentStep = 3">上一步</button>
            <button type="button" class="submit-btn" :disabled="creating" @click="handleCreate">
              {{ creating ? '创建中…' : '创建课程' }}
            </button>
          </div>
        </div>

        <!-- Close hint -->
        <button class="close-hint" @click="$emit('close')">取消</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  COURSE_DOMAINS,
  CURRENT_LEVELS,
  TARGET_LEVELS,
  MOTIVATIONS,
  PACES,
  WEEKLY_MINUTES_OPTIONS,
  getDomainByKey,
  buildMetaPayload,
} from '@/constants/courseDomains'

interface Props {
  show: boolean
  worldId: number
}

interface Emits {
  (e: 'close'): void
  (e: 'create', data: {
    name: string
    description: string
    target_level: string
    meta: Record<string, any>
  }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const currentStep = ref(1)
const creating = ref(false)

const form = ref({
  name: '',
  domain: '',
  currentLevel: '',
  targetLevel: '',
  motivation: '',
  pace: 'normal',
  weeklyMinutes: null as number | null,
  description: '',
})

const selectedDomain = computed(() => getDomainByKey(form.value.domain))
const currentLevelLabel = computed(() => CURRENT_LEVELS.find(l => l.key === form.value.currentLevel)?.label || '未选择')
const targetLevelLabel = computed(() => TARGET_LEVELS.find(l => l.key === form.value.targetLevel)?.label || '未选择')
const motivationLabel = computed(() => MOTIVATIONS.find(m => m.key === form.value.motivation)?.label || '')

const goToStep2 = () => {
  if (form.value.name.trim() && form.value.domain) {
    currentStep.value = 2
  }
}

const goToStep3 = () => {
  currentStep.value = 3
}

const handleCreate = async () => {
  if (!form.value.name.trim()) return
  
  creating.value = true
  try {
    const meta = buildMetaPayload({
      domain: form.value.domain,
      currentLevel: form.value.currentLevel,
      targetLevel: form.value.targetLevel,
      motivation: form.value.motivation,
      pace: form.value.pace,
      weeklyMinutes: form.value.weeklyMinutes || undefined,
    })
    
    emit('create', {
      name: form.value.name.trim(),
      description: form.value.description.trim(),
      target_level: form.value.targetLevel || 'understand',
      meta,
    })
  } finally {
    creating.value = false
  }
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    currentStep.value = 1
    form.value = {
      name: '',
      domain: '',
      currentLevel: '',
      targetLevel: '',
      motivation: '',
      pace: 'normal',
      weeklyMinutes: null,
      description: '',
    }
  }
})
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
  padding: 28px 36px 24px;
  background: rgba(8, 8, 25, 0.98);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-top: none;
  backdrop-filter: blur(20px);
  border-radius: 12px;
}

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
  margin-bottom: 20px;
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

.step-indicator {
  display: flex;
  justify-content: center;
  gap: 14px;
  margin-top: 14px;
}

.step-dot {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  border: 2px solid rgba(255, 215, 0, 0.2);
  color: rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
}

.step-dot.active {
  border-color: #ffd700;
  color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.step-dot.completed {
  border-color: #10b981;
  background: #10b981;
  color: white;
}

.step-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 6px;
  letter-spacing: 2px;
}

.step-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.modal-body {
  display: flex;
  flex-direction: column;
}

.galgame-input {
  background: rgba(0, 0, 0, 0.40) !important;
  border: 2px solid rgba(255, 215, 0, 0.40) !important;
  font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif !important;
  font-size: 14px;
  padding: 12px 14px;
}

.galgame-input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 16px;
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

/* Domain Grid */
.domain-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.domain-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 8px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.domain-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
  background: rgba(255, 215, 0, 0.05);
}

.domain-card.selected {
  border-color: var(--domain-color, #ffd700);
  background: rgba(255, 215, 0, 0.1);
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.15);
}

.domain-icon {
  font-size: 24px;
}

.domain-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}

.domain-card.selected .domain-name {
  color: var(--domain-color, #ffd700);
}

/* Level Grid */
.level-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.level-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.level-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.level-card.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.level-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}

.level-card.selected .level-label {
  color: #ffd700;
}

.level-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

/* Motivation Grid */
.motivation-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.motivation-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.motivation-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
  background: rgba(255, 215, 0, 0.05);
}

.motivation-chip.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.15);
  color: #ffd700;
}

/* Pace Grid */
.pace-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.pace-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pace-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.pace-card.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.pace-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}

.pace-card.selected .pace-label {
  color: #ffd700;
}

.pace-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

/* Minutes Grid */
.minutes-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.minutes-chip {
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.minutes-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.minutes-chip.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.15);
  color: #ffd700;
}

/* Preview Section */
.preview-section {
  display: flex;
  justify-content: center;
  padding: 12px 0;
}

.preview-card {
  width: 100%;
  max-width: 300px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 215, 0, 0.2);
  background: rgba(0, 0, 0, 0.5);
}

.preview-header {
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.preview-domain-icon {
  font-size: 24px;
}

.preview-domain-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: white;
}

.preview-body {
  padding: 14px;
}

.preview-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 15px;
  font-weight: 600;
  color: #ffd700;
  margin-bottom: 12px;
}

.preview-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.preview-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.preview-value {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.preview-value.target {
  color: #10b981;
}

.preview-arrow {
  text-align: center;
  color: rgba(255, 215, 0, 0.4);
  font-size: 14px;
  padding: 4px 0;
}

.preview-desc {
  margin-top: 10px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  line-height: 1.5;
}

/* Buttons */
.btn-row {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.back-btn {
  flex: 1;
  font-family: "Noto Sans SC", sans-serif;
  padding: 12px 20px;
  font-size: 13px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-btn:hover {
  color: rgba(255, 255, 255, 0.8);
  border-color: rgba(255, 215, 0, 0.4);
}

.submit-btn {
  flex: 2;
  font-family: "Noto Sans SC", sans-serif;
  padding: 12px 20px;
  font-size: 14px;
  letter-spacing: 6px;
  font-weight: 600;
  color: #0a0a1e;
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
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
