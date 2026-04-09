<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-subtitle">NEW WORLD</div>
          <div class="modal-title">创 建 新 世 界</div>
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
            <span v-if="currentStep === 1">命名你的世界</span>
            <span v-else-if="currentStep === 2">设定世界氛围</span>
            <span v-else>预览与创建</span>
          </div>
        </div>

        <!-- Step 1: Name + Theme -->
        <form v-if="currentStep === 1" class="modal-body step-content" @submit.prevent="goToStep2">
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

          <div class="field-group">
            <label class="field-label">主 题 风 格 <span class="required">*</span></label>
            <div class="theme-grid">
              <div
                v-for="theme in WORLD_THEMES"
                :key="theme.key"
                class="theme-card"
                :class="{ selected: form.themePreset === theme.key }"
                :style="{
                  '--theme-color': theme.themeColor,
                  backgroundImage: theme.background ? `url(${theme.background})` : undefined
                }"
                @click="form.themePreset = theme.key"
              >
                <div class="theme-overlay">
                  <span class="theme-icon">{{ theme.icon }}</span>
                  <span class="theme-name">{{ theme.name }}</span>
                  <span class="theme-desc">{{ theme.description }}</span>
                </div>
              </div>
            </div>
          </div>

          <button type="submit" class="submit-btn" :disabled="!form.name.trim() || !form.themePreset">
            下 一 步
          </button>
        </form>

        <!-- Step 2: Atmosphere -->
        <div v-else-if="currentStep === 2" class="modal-body step-content">
          <div class="field-group">
            <label class="field-label">世 界 简 介</label>
            <textarea
              v-model="form.description"
              class="galgame-input"
              rows="3"
              placeholder="用一句话描述这里发生的故事……"
              maxlength="140"
            ></textarea>
            <div class="char-count">{{ form.description.length }}/140</div>
          </div>

          <div class="field-group">
            <label class="field-label">氛 围 标 签</label>
            <div class="mood-grid">
              <button
                v-for="mood in MOOD_TAGS"
                :key="mood.key"
                type="button"
                class="mood-chip"
                :class="{ selected: form.moodKeys.includes(mood.key) }"
                @click="toggleMood(mood.key)"
              >
                <span class="mood-icon">{{ mood.icon }}</span>
                <span class="mood-label">{{ mood.label }}</span>
              </button>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">背 景 音 乐</label>
            <div class="bgm-grid">
              <button
                v-for="bgm in BGM_PRESETS"
                :key="bgm.key"
                type="button"
                class="bgm-card"
                :class="{ selected: form.bgmKey === bgm.key }"
                @click="form.bgmKey = bgm.key"
              >
                <span class="bgm-icon">{{ bgm.icon }}</span>
                <span class="bgm-label">{{ bgm.label }}</span>
                <span class="bgm-desc">{{ bgm.description }}</span>
              </button>
            </div>
          </div>

          <div class="btn-row">
            <button type="button" class="back-btn" @click="currentStep = 1">上一步</button>
            <button type="button" class="submit-btn" @click="currentStep = 3">预 览</button>
          </div>
        </div>

        <!-- Step 3: Preview -->
        <div v-else-if="currentStep === 3" class="modal-body step-content">
          <div class="preview-section">
            <div class="preview-card">
              <div 
                class="preview-bg"
                :style="getPreviewBgStyle()"
              >
                <div class="preview-theme-tag" :style="{ background: selectedTheme?.themeColor }">
                  {{ selectedTheme?.icon }} {{ selectedTheme?.name }}
                </div>
              </div>
              <div class="preview-body">
                <div class="preview-name">{{ form.name || '未命名世界' }}</div>
                <div class="preview-desc">{{ form.description || '这个世界还未被描述……' }}</div>
                <div v-if="form.moodKeys.length > 0" class="preview-moods">
                  <span 
                    v-for="moodKey in form.moodKeys" 
                    :key="moodKey"
                    class="preview-mood-tag"
                  >
                    {{ getMoodLabel(moodKey) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="btn-row">
            <button type="button" class="back-btn" @click="currentStep = 2">上一步</button>
            <button type="button" class="submit-btn" :disabled="creating" @click="handleCreate">
              {{ creating ? '创建中…' : '进入这个世界' }}
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
import { WORLD_THEMES, MOOD_TAGS, BGM_PRESETS, getThemeByKey } from '@/constants/worldThemes'

interface Props {
  show: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'create', data: {
    name: string
    description: string
    scenes: Record<string, any>
  }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const currentStep = ref(1)
const creating = ref(false)

const form = ref({
  name: '',
  description: '',
  themePreset: '',
  moodKeys: [] as string[],
  bgmKey: 'silent',
})

const selectedTheme = computed(() => getThemeByKey(form.value.themePreset))

const getPreviewBgStyle = () => {
  if (selectedTheme.value?.background) {
    return {
      backgroundImage: `url(${selectedTheme.value.background})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }
  }
  return {
    background: `linear-gradient(135deg, ${selectedTheme.value?.themeColor}33, #1e1e3f)`,
  }
}

const getMoodLabel = (key: string) => {
  return MOOD_TAGS.find((m) => m.key === key)?.label || key
}

const toggleMood = (key: string) => {
  const idx = form.value.moodKeys.indexOf(key)
  if (idx === -1) {
    form.value.moodKeys.push(key)
  } else {
    form.value.moodKeys.splice(idx, 1)
  }
}

const goToStep2 = () => {
  if (form.value.name.trim() && form.value.themePreset) {
    currentStep.value = 2
  }
}

const handleCreate = async () => {
  if (!form.value.name.trim()) return
  
  creating.value = true
  try {
    const theme = selectedTheme.value
    const scenes = {
      theme_preset: form.value.themePreset,
      background: theme?.background || '',
      theme_color: theme?.themeColor || '#6b7280',
      mood: form.value.moodKeys,
      bgm: form.value.bgmKey,
    }
    
    emit('create', {
      name: form.value.name.trim(),
      description: form.value.description.trim(),
      scenes,
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
      description: '',
      themePreset: '',
      moodKeys: [],
      bgmKey: 'silent',
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
  width: 680px;
  max-width: 92vw;
  max-height: 90vh;
  overflow-y: auto;
  padding: 28px 40px 24px;
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

/* Step Indicator */
.step-indicator {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
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
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 8px;
  letter-spacing: 2px;
}

/* Step Content */
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

/* Form Elements */
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
  padding-bottom: 20px;
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

.char-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  text-align: right;
  margin-top: -4px;
}

/* Theme Grid */
.theme-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.theme-card {
  position: relative;
  height: 90px;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid rgba(255, 215, 0, 0.15);
  transition: all 0.25s ease;
}

.theme-card:not(.selected) {
  background: rgba(0, 0, 0, 0.3);
}

.theme-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
  transform: translateY(-2px);
}

.theme-card.selected {
  border-color: var(--theme-color, #ffd700);
  box-shadow: 0 0 20px var(--theme-color, rgba(255, 215, 0, 0.3));
}

.theme-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.2), rgba(0,0,0,0.6));
  padding: 8px;
}

.theme-icon {
  font-size: 24px;
}

.theme-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: white;
  letter-spacing: 1px;
}

.theme-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
}

.theme-card.selected .theme-name {
  color: var(--theme-color, #ffd700);
}

/* Mood Grid */
.mood-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mood-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: "Noto Sans SC", sans-serif;
}

.mood-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
  background: rgba(255, 215, 0, 0.05);
}

.mood-chip.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.15);
}

.mood-icon {
  font-size: 14px;
}

.mood-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.mood-chip.selected .mood-label {
  color: #ffd700;
}

/* BGM Grid */
.bgm-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.bgm-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.bgm-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
  background: rgba(255, 215, 0, 0.05);
}

.bgm-card.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.bgm-icon {
  font-size: 20px;
}

.bgm-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 1px;
}

.bgm-card.selected .bgm-label {
  color: #ffd700;
}

.bgm-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

/* Preview Section */
.preview-section {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}

.preview-card {
  width: 100%;
  max-width: 320px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 215, 0, 0.2);
  background: rgba(0, 0, 0, 0.5);
}

.preview-bg {
  height: 120px;
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 8px;
}

.preview-theme-tag {
  padding: 4px 10px;
  border-radius: 12px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: white;
  letter-spacing: 1px;
}

.preview-body {
  padding: 14px;
}

.preview-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #ffd700;
  letter-spacing: 2px;
  margin-bottom: 6px;
}

.preview-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.5;
  margin-bottom: 10px;
}

.preview-moods {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preview-mood-tag {
  padding: 3px 8px;
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 10px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 215, 0, 0.8);
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
  padding: 14px 24px;
  font-size: 14px;
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
