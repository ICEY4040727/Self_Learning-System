<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <!-- Header -->
        <div class="modal-header">
          <div class="header-icon">
            <svg v-if="character?.type === 'sage'" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
          </div>
          <div class="modal-subtitle">{{ character?.type === 'sage' ? 'EDIT SAGE' : 'EDIT TRAVELER' }}</div>
          <div class="modal-title">{{ character?.name || '编 辑 角 色' }}</div>
          <div class="gold-line"></div>
        </div>

        <!-- Form -->
        <form class="modal-body" @submit.prevent="handleSubmit">
          <!-- Avatar Preview & Upload -->
          <div class="avatar-section">
            <div class="avatar-preview" @click="triggerFileInput">
              <input ref="fileInput" type="file" accept="image/*" style="display: none" @change="handleFileChange" />
              <img v-if="form.avatar" :src="form.avatar" alt="avatar" />
              <div v-else class="avatar-placeholder">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  <circle cx="8.5" cy="8.5" r="1.5"></circle>
                  <polyline points="21 15 16 10 5 21"></polyline>
                </svg>
                <span>上传立绘</span>
              </div>
              <div class="avatar-overlay">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
              </div>
            </div>
            <button v-if="form.avatar" type="button" class="btn-remove-avatar" @click="form.avatar = ''">
              移除图片
            </button>
          </div>

          <!-- Basic Info -->
          <div class="form-section">
            <div class="section-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              基础信息
            </div>

            <div class="field-row">
              <div class="field-group">
                <label class="field-label">角色名称 <span class="required">*</span></label>
                <input v-model="form.name" type="text" class="galgame-input" placeholder="输入角色名称" maxlength="20" required />
              </div>
              <div class="field-group">
                <label class="field-label">称 号</label>
                <input v-model="form.title" type="text" class="galgame-input" placeholder="输入角色称号" maxlength="30" />
              </div>
            </div>

            <div class="field-group">
              <label class="field-label">人物简介</label>
              <textarea v-model="form.description" class="galgame-input" rows="3" placeholder="描述角色的背景和特点..." maxlength="200"></textarea>
            </div>
          </div>

          <!-- Tags (for Traveler) -->
          <div v-if="character?.type === 'traveler'" class="form-section">
            <div class="section-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path>
                <line x1="7" y1="7" x2="7.01" y2="7"></line>
              </svg>
              性格标签
            </div>
            <div class="tag-list">
              <button v-for="tag in travelerTraits" :key="tag" type="button" class="tag-chip" :class="{ selected: form.tags.includes(tag) }" @click="toggleTag(tag)">
                <span class="tag-name">{{ tag }}</span>
              </button>
            </div>
          </div>

          <!-- Persona (for Sage) -->
          <div v-if="character?.type === 'sage'" class="form-section">
            <div class="section-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
              </svg>
              人格设定
            </div>

            <div class="field-group">
              <label class="field-label">人格模板</label>
              <div class="template-grid">
                <button v-for="(tmpl, idx) in sageTemplates" :key="idx" type="button" class="template-card" :class="{ active: form.personality === tmpl.name }" @click="form.personality = tmpl.name">
                  <span class="template-name">{{ tmpl.name }}</span>
                  <span class="template-desc">{{ tmpl.desc }}</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Color Theme -->
          <div class="form-section">
            <div class="section-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="13.5" cy="6.5" r="2.5"></circle>
                <circle cx="17.5" cy="10.5" r="2.5"></circle>
                <circle cx="8.5" cy="7.5" r="2.5"></circle>
                <circle cx="6.5" cy="12.5" r="2.5"></circle>
                <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.555C21.965 6.012 17.461 2 12 2z"></path>
              </svg>
              色彩主题
            </div>
            <div class="color-list">
              <button v-for="(color, idx) in colorOptions" :key="idx" type="button" class="color-btn" :class="{ selected: form.colorIdx === idx }" :style="{ background: color }" @click="form.colorIdx = idx">
                <svg v-if="form.colorIdx === idx" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </button>
            </div>
          </div>

          <!-- Actions -->
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="$emit('close')">取消</button>
            <button type="submit" class="btn-primary" :disabled="!form.name.trim() || saving">
              <span v-if="saving" class="loading-spinner"></span>
              {{ saving ? '保存中...' : '保存修改' }}
            </button>
          </div>
        </form>

        <button class="close-hint" @click="$emit('close')">取消</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'

interface Character {
  id: number
  name: string
  title?: string
  description?: string
  avatar?: string
  type: 'sage' | 'traveler'
  tags?: string[]
  personality?: string
}

interface Props {
  show: boolean
  character?: Character | null
}

interface Emits {
  (e: 'close'): void
  (e: 'update', data: UpdateData): void
}

interface UpdateData {
  id: number
  name: string
  title: string
  description: string
  avatar?: string
  colorIdx: number
  tags: string[]
  personality?: string
  type: 'sage' | 'traveler'
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const fileInput = ref<HTMLInputElement | null>(null)
const saving = ref(false)

const form = reactive({
  name: '',
  title: '',
  description: '',
  avatar: '',
  colorIdx: 0,
  tags: [] as string[],
  personality: ''
})

const sageTemplates = [
  { name: '苏格拉底型', desc: '反问引导，层层递进' },
  { name: '爱因斯坦型', desc: '鼓励假设，实验探索' },
  { name: '亚里士多德型', desc: '百科全书，体系完整' },
  { name: '孙子型', desc: '策略思维，举一反三' }
]

const travelerTraits = ['好奇心强', '逻辑思维', '探索型', '逻辑严谨', '发散思维', '专注认真']

const colorOptions = [
  'rgba(245, 158, 11, 0.6)',
  'rgba(139, 92, 246, 0.6)',
  'rgba(16, 185, 129, 0.6)',
  'rgba(220, 38, 38, 0.6)',
  'rgba(59, 130, 246, 0.6)',
  'rgba(6, 182, 212, 0.6)'
]

watch(() => props.show, (newVal) => {
  if (newVal && props.character) {
    form.name = props.character.name
    form.title = props.character.title || ''
    form.description = props.character.description || ''
    form.avatar = props.character.avatar || ''
    form.tags = [...(props.character.tags || [])]
    form.personality = props.character.personality || ''
  }
})

const toggleTag = (tag: string) => {
  const idx = form.tags.indexOf(tag)
  if (idx === -1) form.tags.push(tag)
  else form.tags.splice(idx, 1)
}

const triggerFileInput = () => fileInput.value?.click()

const handleFileChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (ev) => { form.avatar = ev.target?.result as string }
    reader.readAsDataURL(file)
  }
}

const handleSubmit = async () => {
  if (!form.name.trim() || !props.character) return
  
  saving.value = true
  
  const data: UpdateData = {
    id: props.character.id,
    name: form.name.trim(),
    title: form.title.trim(),
    description: form.description.trim(),
    avatar: form.avatar || undefined,
    colorIdx: form.colorIdx,
    tags: [...form.tags],
    personality: form.personality || undefined,
    type: props.character.type
  }
  
  emit('update', data)
  
  setTimeout(() => {
    saving.value = false
  }, 500)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
}

.modal-box {
  position: relative;
  width: 600px;
  max-width: 92vw;
  max-height: 90vh;
  overflow-y: auto;
  padding: 32px 40px 24px;
  background: rgba(10, 10, 30, 0.98);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 20px;
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
}

.modal-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(255, 215, 0, 0.8), transparent);
  border-radius: 20px 20px 0 0;
}

.modal-header {
  text-align: center;
  margin-bottom: 28px;
}

.header-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.15), rgba(255, 215, 0, 0.05));
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 16px;
  color: #ffd700;
}

.modal-subtitle {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.35);
  margin-bottom: 8px;
}

.modal-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 22px;
  letter-spacing: 6px;
  color: #ffd700;
}

.gold-line {
  width: 100px;
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(255, 215, 0, 0.5), transparent);
  margin: 16px auto 0;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Avatar Section */
.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.avatar-preview {
  width: 120px;
  height: 120px;
  border-radius: 16px;
  border: 2px dashed rgba(255, 215, 0, 0.3);
  overflow: hidden;
  cursor: pointer;
  position: relative;
  transition: all 0.3s ease;
  background: rgba(0, 0, 0, 0.3);
}

.avatar-preview:hover {
  border-color: rgba(255, 215, 0, 0.6);
  transform: scale(1.02);
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.4);
}

.avatar-placeholder span {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
  color: #ffd700;
}

.avatar-preview:hover .avatar-overlay {
  opacity: 1;
}

.btn-remove-avatar {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color 0.2s ease;
}

.btn-remove-avatar:hover {
  color: #f87171;
}

/* Form Sections */
.form-section {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 215, 0, 0.1);
  border-radius: 12px;
  padding: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: #ffd700;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.field-group:last-child {
  margin-bottom: 0;
}

.field-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 1px;
}

.required {
  color: #f87171;
}

.galgame-input {
  width: 100%;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: white;
  outline: none;
  transition: all 0.2s ease;
}

.galgame-input:focus {
  border-color: rgba(255, 215, 0, 0.5);
  box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.1);
}

.galgame-input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

/* Tags */
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag-chip {
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tag-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.tag-chip.selected {
  border-color: rgba(255, 215, 0, 0.6);
  background: rgba(255, 215, 0, 0.15);
}

.tag-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.tag-chip.selected .tag-name {
  color: #ffd700;
}

/* Template Grid */
.template-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.template-card {
  padding: 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.1);
  border-radius: 10px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
}

.template-card:hover {
  border-color: rgba(255, 215, 0, 0.3);
}

.template-card.active {
  border-color: rgba(255, 215, 0, 0.6);
  background: rgba(255, 215, 0, 0.1);
}

.template-name {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: #ffd700;
  margin-bottom: 4px;
}

.template-desc {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

/* Color List */
.color-list {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.color-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s ease;
  color: white;
}

.color-btn:hover {
  transform: scale(1.15);
}

.color-btn.selected {
  border-color: white;
  box-shadow: 0 0 16px rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

/* Actions */
.modal-actions {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}

.btn-primary,
.btn-secondary {
  flex: 1;
  padding: 14px 24px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  letter-spacing: 4px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-primary {
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  color: #0a0a1e;
  font-weight: 600;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffe033, #ffd700);
  box-shadow: 0 6px 24px rgba(255, 215, 0, 0.4);
  transform: translateY(-2px);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.7);
}

.btn-secondary:hover {
  border-color: rgba(255, 255, 255, 0.3);
  color: white;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(0, 0, 0, 0.2);
  border-top-color: #0a0a1e;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.close-hint {
  display: block;
  width: 100%;
  padding: 12px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.3);
  background: transparent;
  border: none;
  cursor: pointer;
  margin-top: 8px;
  transition: color 0.2s ease;
}

.close-hint:hover {
  color: rgba(255, 255, 255, 0.5);
}

/* Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-box,
.modal-fade-leave-active .modal-box {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.modal-fade-enter-from .modal-box,
.modal-fade-leave-to .modal-box {
  transform: scale(0.95) translateY(20px);
  opacity: 0;
}
</style>
