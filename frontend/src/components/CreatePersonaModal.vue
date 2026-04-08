<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-subtitle">NEW PERSONA</div>
          <div class="modal-title">创 建 导 师</div>
          <div class="gold-line"></div>
          
          <!-- Step Indicator -->
          <div class="step-indicator">
            <div 
              v-for="step in 3" 
              :key="step"
              class="step-dot"
              :class="{ active: currentStep === step, completed: currentStep > step }"
            >
              <span v-if="currentStep > step">✓</span>
              <span v-else>{{ step }}</span>
            </div>
          </div>
          <div class="step-label">
            <span v-if="currentStep === 1">选择模板</span>
            <span v-else-if="currentStep === 2">设定性格</span>
            <span v-else>确认创建</span>
          </div>
        </div>

        <!-- Step 1: Template Selection + AI Generate -->
        <form v-if="currentStep === 1" class="modal-body step-content" @submit.prevent="goToStep2">
          <!-- AI Generate Section -->
          <div class="field-group">
            <label class="field-label">💫 AI 一键生成（可选）</label>
            <div class="ai-generate-section">
              <textarea
                v-model="aiDescription"
                class="galgame-input"
                rows="2"
                placeholder="描述你想要的导师风格，如：'一位喜欢用比喻讲解数学的慈祥老爷爷'"
                maxlength="200"
              ></textarea>
              <button 
                type="button"
                class="ai-generate-btn"
                :disabled="generating || !aiDescription.trim()"
                @click="handleAIGenerate"
              >
                <span v-if="generating">生成中…</span>
                <span v-else>✨ 智能生成</span>
              </button>
            </div>
            <div v-if="generatedSuggestion" class="ai-suggestion">
              <div class="suggestion-label">建议名称：</div>
              <div class="suggestion-name">{{ generatedSuggestion.name_suggestion }}</div>
              <div v-if="generatedSuggestion.title_suggestion" class="suggestion-title">
                头衔：{{ generatedSuggestion.title_suggestion }}
              </div>
              <button type="button" class="apply-btn" @click="applySuggestion">
                应用此建议
              </button>
            </div>
          </div>

          <!-- Template Selection -->
          <div class="field-group">
            <label class="field-label">或 选 择 模 板</label>
            <div class="template-grid">
              <div
                v-for="tpl in PERSONA_TEMPLATES"
                :key="tpl.key"
                class="template-card"
                :class="{ selected: form.templateKey === tpl.key }"
                @click="form.templateKey = tpl.key"
              >
                <span class="template-icon">{{ tpl.icon }}</span>
                <span class="template-name">{{ tpl.name }}</span>
                <span class="template-desc">{{ tpl.description }}</span>
              </div>
            </div>
          </div>

          <!-- Basic Info -->
          <div class="field-group">
            <label class="field-label">名 称 <span class="required">*</span></label>
            <input
              v-model="form.name"
              type="text"
              class="galgame-input"
              placeholder="给你的导师起个名字"
              maxlength="20"
              required
            />
          </div>

          <div class="field-group">
            <label class="field-label">头 衔</label>
            <input
              v-model="form.title"
              type="text"
              class="galgame-input"
              placeholder="如：学院教授、修行导师（可选）"
              maxlength="15"
            />
          </div>

          <button type="submit" class="submit-btn" :disabled="!form.name.trim()">
            下 一 步
          </button>
        </form>

        <!-- Step 2: Traits Sliders -->
        <div v-else-if="currentStep === 2" class="modal-body step-content">
          <!-- Avatar & Color -->
          <div class="field-group">
            <label class="field-label">头 像</label>
            <div class="avatar-color-row">
              <div class="avatar-options">
                <button
                  v-for="av in AVATAR_OPTIONS"
                  :key="av"
                  type="button"
                  class="avatar-btn"
                  :class="{ selected: form.avatar === av }"
                  @click="form.avatar = av"
                >
                  {{ av }}
                </button>
              </div>
              <div class="color-options">
                <button
                  v-for="color in COLOR_OPTIONS"
                  :key="color"
                  type="button"
                  class="color-btn"
                  :class="{ selected: form.color === color }"
                  :style="{ background: color }"
                  @click="form.color = color"
                ></button>
              </div>
            </div>
          </div>

          <!-- Trait Sliders -->
          <div class="field-group">
            <label class="field-label">性 格 设 定</label>
            <div class="sliders">
              <div v-for="slider in TRAIT_SLIDERS" :key="slider.key" class="slider-item">
                <div class="slider-header">
                  <span class="slider-name">{{ slider.name }}</span>
                  <span class="slider-value">{{ form.traits[slider.key] || slider.default }}</span>
                </div>
                <input
                  type="range"
                  :min="slider.min"
                  :max="slider.max"
                  :value="form.traits[slider.key] || slider.default"
                  class="trait-slider"
                  @input="form.traits[slider.key] = Number(($event.target as HTMLInputElement).value)"
                />
                <div class="slider-labels">
                  <span>{{ slider.minLabel }}</span>
                  <span>{{ slider.maxLabel }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Description -->
          <div class="field-group">
            <label class="field-label">描 述</label>
            <textarea
              v-model="form.description"
              class="galgame-input"
              rows="2"
              placeholder="描述这位导师的特点（可选）"
              maxlength="100"
            ></textarea>
          </div>

          <div class="btn-row">
            <button type="button" class="back-btn" @click="currentStep = 1">上一步</button>
            <button type="button" class="submit-btn" @click="currentStep = 3">预览</button>
          </div>
        </div>

        <!-- Step 3: Preview -->
        <div v-else-if="currentStep === 3" class="modal-body step-content">
          <div class="preview-section">
            <div class="preview-card">
              <div class="preview-avatar" :style="{ background: form.color }">
                {{ form.avatar }}
              </div>
              <div class="preview-info">
                <div class="preview-name">{{ form.name }}</div>
                <div v-if="form.title" class="preview-title">{{ form.title }}</div>
                <div class="preview-template">{{ selectedTemplate?.name }}</div>
              </div>
            </div>

            <div class="preview-traits">
              <div class="traits-label">性格特质</div>
              <div class="traits-grid">
                <div v-for="slider in TRAIT_SLIDERS" :key="slider.key" class="trait-row">
                  <span class="trait-name">{{ slider.name }}</span>
                  <div class="trait-bar">
                    <div 
                      class="trait-fill" 
                      :style="{ width: `${((form.traits[slider.key] || slider.default) / slider.max) * 100}%`, background: form.color }"
                    ></div>
                  </div>
                  <span class="trait-value">{{ form.traits[slider.key] || slider.default }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="btn-row">
            <button type="button" class="back-btn" @click="currentStep = 2">上一步</button>
            <button type="button" class="submit-btn" :disabled="creating" @click="handleCreate">
              {{ creating ? '创建中…' : '创建导师' }}
            </button>
          </div>
        </div>

        <button class="close-hint" @click="$emit('close')">取消</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  PERSONA_TEMPLATES,
  TRAIT_SLIDERS,
  AVATAR_OPTIONS,
  COLOR_OPTIONS,
  getTemplateByKey,
  buildTraitsPayload,
  buildCharacterPayload,
} from '@/constants/personaTemplates'
import client from '@/api/client'

interface Props {
  show: boolean
  worldId?: number
}

interface Emits {
  (e: 'close'): void
  (e: 'create', data: Record<string, any>): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const currentStep = ref(1)
const generating = ref(false)
const creating = ref(false)
const aiDescription = ref('')
const generatedSuggestion = ref<{ name_suggestion: string; title_suggestion?: string } | null>(null)

const form = ref({
  name: '',
  title: '',
  avatar: '☉',
  color: '#ffd700',
  templateKey: 'socrates',
  description: '',
  traits: Object.fromEntries(TRAIT_SLIDERS.map(s => [s.key, s.default])),
})

const selectedTemplate = computed(() => getTemplateByKey(form.value.templateKey))

const goToStep2 = () => {
  if (form.value.name.trim()) {
    currentStep.value = 2
  }
}

const handleAIGenerate = async () => {
  if (!aiDescription.value.trim()) return
  
  generating.value = true
  try {
    const { data } = await client.post('/persona/generate', {
      description: aiDescription.value,
    })
    generatedSuggestion.value = data
  } catch (error) {
    console.error('AI generate failed:', error)
  } finally {
    generating.value = false
  }
}

const applySuggestion = () => {
  if (generatedSuggestion.value) {
    if (generatedSuggestion.value.name_suggestion) {
      form.value.name = generatedSuggestion.value.name_suggestion
    }
    if (generatedSuggestion.value.title_suggestion) {
      form.value.title = generatedSuggestion.value.title_suggestion
    }
  }
}

const handleCreate = async () => {
  if (!form.value.name.trim()) return
  
  creating.value = true
  try {
    const payload = buildCharacterPayload({
      name: form.value.name.trim(),
      title: form.value.title.trim(),
      avatar: form.value.avatar,
      color: form.value.color,
      templateKey: form.value.templateKey,
      description: form.value.description.trim(),
      traits: form.value.traits,
    })
    
    emit('create', payload)
  } finally {
    creating.value = false
  }
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    currentStep.value = 1
    aiDescription.value = ''
    generatedSuggestion.value = null
    form.value = {
      name: '',
      title: '',
      avatar: '☉',
      color: '#ffd700',
      templateKey: 'socrates',
      description: '',
      traits: Object.fromEntries(TRAIT_SLIDERS.map(s => [s.key, s.default])),
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
  margin-bottom: 20px;
}

.modal-subtitle {
  font-size: 10px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.25);
  margin-bottom: 8px;
}

.modal-title {
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
  font-family: "Noto Sans SC", sans-serif !important;
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

/* AI Generate */
.ai-generate-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-generate-btn {
  font-family: "Noto Sans SC", sans-serif;
  padding: 8px 16px;
  font-size: 12px;
  color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  align-self: flex-start;
}

.ai-generate-btn:hover:not(:disabled) {
  background: rgba(255, 215, 0, 0.2);
}

.ai-generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ai-suggestion {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 8px;
  padding: 12px;
  margin-top: 8px;
}

.suggestion-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 4px;
}

.suggestion-name {
  font-size: 16px;
  font-weight: 600;
  color: #10b981;
  margin-bottom: 4px;
}

.suggestion-title {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 8px;
}

.apply-btn {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  padding: 4px 12px;
  color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.4);
  border-radius: 4px;
  cursor: pointer;
}

/* Template Grid */
.template-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.template-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 8px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.template-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
  background: rgba(255, 215, 0, 0.05);
}

.template-card.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.15);
}

.template-icon {
  font-size: 24px;
}

.template-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}

.template-card.selected .template-name {
  color: #ffd700;
}

.template-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 9px;
  color: rgba(255, 255, 255, 0.4);
  text-align: center;
}

/* Avatar & Color */
.avatar-color-row {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.avatar-options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-width: 180px;
}

.avatar-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.avatar-btn:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.avatar-btn.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.15);
}

.color-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.color-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.color-btn:hover {
  transform: scale(1.1);
}

.color-btn.selected {
  border-color: white;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
}

/* Sliders */
.sliders {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.slider-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.slider-name {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.slider-value {
  font-size: 12px;
  color: #ffd700;
  font-weight: 600;
}

.trait-slider {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  background: rgba(255, 215, 0, 0.2);
  border-radius: 3px;
  outline: none;
}

.trait-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #ffd700;
  border-radius: 50%;
  cursor: pointer;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  color: rgba(255, 255, 255, 0.35);
}

/* Preview */
.preview-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}

.preview-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 12px;
  width: 100%;
}

.preview-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}

.preview-info {
  flex: 1;
}

.preview-name {
  font-size: 18px;
  font-weight: 600;
  color: #ffd700;
  margin-bottom: 2px;
}

.preview-title {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 4px;
}

.preview-template {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.preview-traits {
  width: 100%;
}

.traits-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 10px;
  text-align: center;
}

.traits-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.trait-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.trait-name {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  width: 70px;
  flex-shrink: 0;
}

.trait-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.trait-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.trait-value {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  width: 20px;
  text-align: right;
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
