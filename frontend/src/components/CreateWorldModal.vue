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

        <!-- Single-page form: everything visible -->
        <div class="modal-body">
          <!-- AI Inspiration (top, prominent) -->
          <div class="field-group">
            <label class="field-label">✨ AI 灵感生成</label>
            <p class="field-hint">描述你想要的世界，AI 将自动生成全部设定</p>
            <div class="ai-input-row">
              <input
                v-model="aiDescription"
                type="text"
                class="galgame-input ai-input"
                placeholder="如：一个充满魔法的维多利亚时代学院"
                maxlength="500"
                :disabled="aiGenerating"
                @keyup.enter="handleAiGenerate"
              />
              <button
                type="button"
                class="ai-btn"
                :disabled="!aiDescription.trim() || aiGenerating"
                @click="handleAiGenerate"
              >
                <span v-if="aiGenerating" class="ai-spinner"></span>
                <span v-else>生成</span>
              </button>
            </div>
            <div v-if="aiGenerating" class="ai-progress-bar">
              <div class="ai-progress-fill" :style="{ width: aiProgress + '%' }"></div>
            </div>
            <div v-if="aiError" class="ai-error-inline">{{ aiError }}</div>
          </div>

          <div class="divider"></div>

          <!-- Name -->
          <div class="field-row">
            <div class="field-group flex-1">
              <label class="field-label">世 界 名 称 <span class="required">*</span></label>
              <input
                v-model="form.name"
                type="text"
                class="galgame-input"
                placeholder="为你的世界命名……"
                maxlength="20"
              />
            </div>
          </div>

          <!-- Theme -->
          <div class="field-group">
            <label class="field-label">主 题 风 格</label>
            <div class="theme-grid">
              <div
                v-for="theme in WORLD_THEMES"
                :key="theme.key"
                class="theme-card"
                :class="{ selected: form.themePreset === theme.key }"
                :style="{ '--theme-color': theme.themeColor }"
                @click="form.themePreset = theme.key"
              >
                <span class="theme-icon">{{ theme.icon }}</span>
                <span class="theme-name">{{ theme.name }}</span>
              </div>
            </div>
          </div>

          <!-- Description -->
          <div class="field-group">
            <label class="field-label">世 界 简 介</label>
            <textarea
              v-model="form.description"
              class="galgame-input"
              rows="2"
              placeholder="用一句话描述这个世界的学习氛围……"
              maxlength="140"
            ></textarea>
          </div>

          <!-- Mood + BGM side by side -->
          <div class="two-col">
            <div class="field-group">
              <label class="field-label">氛 围</label>
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
                  {{ mood.label }}
                </button>
              </div>
            </div>
            <div class="field-group">
              <label class="field-label">背 景 音</label>
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
                </button>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="btn-row">
            <button type="button" class="back-btn" @click="$emit('close')">取消</button>
            <button
              type="button"
              class="submit-btn"
              :disabled="!form.name.trim() || creating"
              @click="handleCreate"
            >
              {{ creating ? '创建中…' : '进入这个世界' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { WORLD_THEMES, MOOD_TAGS, BGM_PRESETS, getThemeByKey } from '@/constants/worldThemes'
import { worldApi } from '@/api/world'

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

const creating = ref(false)

const form = ref({
  name: '',
  description: '',
  themePreset: '',
  moodKeys: [] as string[],
  bgmKey: 'silent',
  worldDetail: '',  // AI 生成的世界详细设定
})

// AI generation state
const aiDescription = ref('')
const aiGenerating = ref(false)
const aiProgress = ref(0)
const aiError = ref('')

const selectedTheme = computed(() => getThemeByKey(form.value.themePreset))

const toggleMood = (key: string) => {
  const idx = form.value.moodKeys.indexOf(key)
  if (idx === -1) {
    form.value.moodKeys.push(key)
  } else {
    form.value.moodKeys.splice(idx, 1)
  }
}

// AI generate handler — auto-fills ALL fields
const handleAiGenerate = async () => {
  if (!aiDescription.value.trim() || aiGenerating.value) return

  aiGenerating.value = true
  aiProgress.value = 0
  aiError.value = ''

  const progressInterval = setInterval(() => {
    if (aiProgress.value < 90) {
      aiProgress.value += Math.random() * 15
    }
  }, 500)

  try {
    const result = await worldApi.generateWorld(aiDescription.value.trim())
    aiProgress.value = 100

    // Auto-fill ALL form fields from AI result
    if (result.name_suggestion) form.value.name = result.name_suggestion
    if (result.description) form.value.description = result.description
    if (result.world_detail) form.value.worldDetail = result.world_detail

    // Apply theme
    if (result.theme_preset) {
      const themeMatch = WORLD_THEMES.find(t => t.key === result.theme_preset)
      if (themeMatch) form.value.themePreset = result.theme_preset
    }

    // Apply mood tags
    form.value.moodKeys = result.mood_tags.filter(tag =>
      MOOD_TAGS.some(m => m.key === tag || m.label === tag)
    ).map(tag => {
      const found = MOOD_TAGS.find(m => m.key === tag || m.label === tag)
      return found ? found.key : tag
    })

    // Apply BGM
    if (BGM_PRESETS.some(b => b.key === result.bgm_suggestion)) {
      form.value.bgmKey = result.bgm_suggestion
    }

    aiDescription.value = ''
  } catch (err: any) {
    const msg = err?.response?.data?.detail || err?.message || 'AI 生成失败，请重试'
    aiError.value = msg
  } finally {
    clearInterval(progressInterval)
    aiGenerating.value = false
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
      world_detail: form.value.worldDetail,
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
    form.value = {
      name: '',
      description: '',
      themePreset: '',
      moodKeys: [],
      bgmKey: 'silent',
      worldDetail: '',
    }
    aiDescription.value = ''
    aiGenerating.value = false
    aiProgress.value = 0
    aiError.value = ''
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
  margin-bottom: 16px;
}

.modal-subtitle {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.25);
  margin-bottom: 6px;
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
  margin: 10px auto 0;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.divider {
  height: 1px;
  background: rgba(255, 215, 0, 0.1);
  margin: 4px 0;
}

/* Form Elements */
.galgame-input {
  width: 100%;
  background: rgba(0, 0, 0, 0.40) !important;
  border: 2px solid rgba(255, 215, 0, 0.30) !important;
  font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif !important;
  font-size: 13px;
  padding: 10px 12px;
  color: rgba(255, 255, 255, 0.85);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s ease;
}

.galgame-input:focus {
  border-color: rgba(255, 215, 0, 0.7) !important;
}

.galgame-input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-row {
  display: flex;
  gap: 12px;
}

.flex-1 {
  flex: 1;
}

.field-label {
  font-family: "Noto Sans SC", sans-serif;
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
  letter-spacing: 3px;
}

.field-hint {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  margin: 0;
}

.required {
  color: #ef4444;
}

/* AI Section */
.ai-input-row {
  display: flex;
  gap: 8px;
}

.ai-input {
  flex: 1;
}

.ai-btn {
  flex-shrink: 0;
  width: 72px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  letter-spacing: 2px;
  color: #0a0a1e;
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ai-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffe033, #ffd700);
  box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
}

.ai-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ai-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(10, 10, 30, 0.3);
  border-top-color: #0a0a1e;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.ai-progress-bar {
  height: 3px;
  background: rgba(255, 215, 0, 0.1);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 4px;
}

.ai-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #f0c000);
  border-radius: 2px;
  transition: width 0.5s ease;
}

.ai-error-inline {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: #ef4444;
  margin-top: 4px;
}

/* Theme Grid — compact horizontal */
.theme-grid {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.theme-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 215, 0, 0.15);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.theme-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
  transform: translateY(-1px);
}

.theme-card.selected {
  border-color: var(--theme-color, #ffd700);
  background: rgba(255, 215, 0, 0.08);
  box-shadow: 0 0 12px rgba(255, 215, 0, 0.1);
}

.theme-icon {
  font-size: 16px;
}

.theme-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 1px;
}

.theme-card.selected .theme-name {
  color: var(--theme-color, #ffd700);
  font-weight: 600;
}

/* Two-column layout */
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* Mood Grid */
.mood-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.mood-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.mood-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.mood-chip.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.12);
  color: #ffd700;
}

.mood-icon {
  font-size: 12px;
}

/* BGM Grid */
.bgm-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bgm-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.bgm-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.bgm-card.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.08);
}

.bgm-icon {
  font-size: 16px;
}

.bgm-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.bgm-card.selected .bgm-label {
  color: #ffd700;
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
  padding: 12px 24px;
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
  padding: 12px 24px;
  font-size: 13px;
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

/* Transitions */
.modal-fade-enter-active,
.modal-fade-enter-active .modal-box {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.modal-fade-leave-active,
.modal-fade-leave-active .modal-box {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .modal-box,
.modal-fade-leave-to .modal-box {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}
</style>
