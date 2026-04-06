<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <div class="modal-header">
          <div class="modal-subtitle">{{ isSage ? 'NEW SAGE' : 'NEW TRAVELER' }}</div>
          <div class="modal-title">{{ isSage ? '创 建 新 知 者' : '创 建 新 旅 者' }}</div>
          <div class="gold-line"></div>
        </div>

        <form class="modal-body" @submit.prevent="handleCreate">
          <div class="field-group">
            <label class="field-label">角 色 类 型</label>
            <div class="type-toggle">
              <button type="button" class="type-btn" :class="{ active: isSage }" @click="isSage = true">
                <div class="type-icon" :style="{ background: '#f59e0b' }">☉</div>
                <span class="type-name">知者</span>
              </button>
              <button type="button" class="type-btn" :class="{ active: !isSage }" @click="isSage = false">
                <div class="type-icon" :style="{ background: '#3b82f6' }">✦</div>
                <span class="type-name">旅者</span>
              </button>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">称 号 / 身 份 <span class="required">*</span></label>
            <input v-model="form.title" type="text" class="galgame-input" placeholder="为角色命名……" maxlength="30" required />
          </div>

          <div class="field-group">
            <label class="field-label">人 物 简 介</label>
            <textarea v-model="form.description" class="galgame-input" rows="2" placeholder="描述这个角色的特点……" maxlength="200"></textarea>
          </div>

          <div class="field-group">
            <label class="field-label">MBTI 人 格 类 型</label>
            <div class="tag-list">
              <button v-for="mbti in mbtiTypes" :key="mbti" type="button" class="tag-chip" :class="{ selected: form.tags.includes(mbti) }" @click="toggleTag(mbti)">
                <span class="tag-name">{{ mbti }}</span>
              </button>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">色 彩 主 题</label>
            <div class="color-list">
              <button v-for="(color, idx) in colorOptions" :key="idx" type="button" class="color-btn" :class="{ selected: form.colorIdx === idx }" :style="{ background: color }" @click="form.colorIdx = idx"></button>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">头 像 / 立 绘</label>
            <div class="upload-area" @click="triggerFileInput">
              <input ref="fileInput" type="file" accept="image/*" style="display: none" @change="handleFileChange" />
              <div v-if="form.imageUrl" class="upload-preview">
                <img :src="form.imageUrl" alt="preview" />
                <button type="button" class="remove-btn" @click.stop="form.imageUrl = ''">×</button>
              </div>
              <div v-else class="upload-placeholder">
                <span class="upload-icon">+</span>
                <span class="upload-text">上传头像或立绘</span>
              </div>
            </div>
          </div>

          <button type="submit" class="submit-btn" :disabled="!form.title.trim()">创 建</button>
        </form>

        <button class="close-hint" @click="$emit('close')">取消</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'

interface Props { show: boolean; defaultType?: 'sage' | 'traveler' }
interface Emits { (e: 'close'): void; (e: 'create', data: { type: 'sage' | 'traveler'; title: string; description: string; tags: string[]; colorIdx: number; imageUrl?: string }): void }

const props = withDefaults(defineProps<Props>(), { defaultType: 'sage' })
const emit = defineEmits<Emits>()

const isSage = ref(props.defaultType === 'sage')
const fileInput = ref<HTMLInputElement | null>(null)

const form = reactive({ title: '', description: '', tags: [] as string[], colorIdx: 0, imageUrl: '' })

const mbtiTypes = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP', 'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP']

const colorOptions = [
  'rgba(245, 158, 11, 0.5)', 'rgba(139, 92, 246, 0.5)', 'rgba(16, 185, 129, 0.5)',
  'rgba(220, 38, 38, 0.5)', 'rgba(59, 130, 246, 0.5)', 'rgba(6, 182, 212, 0.5)',
]

watch(() => props.show, (newVal) => {
  if (newVal) { form.title = ''; form.description = ''; form.tags = []; form.colorIdx = 0; form.imageUrl = ''; isSage.value = props.defaultType === 'sage' }
})

const toggleTag = (tag: string) => { const idx = form.tags.indexOf(tag); if (idx === -1) form.tags.push(tag); else form.tags.splice(idx, 1) }
const triggerFileInput = () => fileInput.value?.click()
const handleFileChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) { const reader = new FileReader(); reader.onload = (ev) => { form.imageUrl = ev.target?.result as string }; reader.readAsDataURL(file) }
}
const handleCreate = () => { if (!form.title.trim()) return; emit('create', { type: isSage.value ? 'sage' : 'traveler', title: form.title.trim(), description: form.description.trim(), tags: form.tags, colorIdx: form.colorIdx, imageUrl: form.imageUrl || undefined }) }
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(4px); }
.modal-box { position: relative; width: 560px; max-width: 92vw; max-height: 90vh; overflow-y: visible; padding: 28px 40px 24px; background: rgba(8, 8, 25, 0.09); border: 1px solid rgba(255, 215, 0, 0.15); border-top: none; backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 12px; }
.modal-box::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(to right, transparent 0%, rgba(255, 215, 0, 0.6) 20%, rgba(255, 215, 0, 0.9) 50%, rgba(255, 215, 0, 0.6) 80%, transparent 100%); border-radius: 12px 12px 0 0; }
.modal-header { text-align: center; margin-bottom: 24px; }
.modal-subtitle { font-family: "Noto Sans SC", sans-serif; font-size: 10px; letter-spacing: 4px; color: rgba(255, 255, 255, 0.25); margin-bottom: 8px; }
.modal-title { font-family: "Noto Sans SC", sans-serif; font-size: 18px; letter-spacing: 6px; color: #ffd700; }
.gold-line { width: 120px; height: 1px; background: linear-gradient(to right, transparent, rgba(255, 215, 0, 0.4), transparent); margin: 12px auto 0; }
.modal-body { display: flex; flex-direction: column; }
.modal-body .galgame-input { background: rgba(0, 0, 0, 0.40) !important; border: 2px solid rgba(255, 215, 0, 0.40) !important; font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif !important; font-size: 14px; padding: 12px 14px; color: white; }
.modal-body .galgame-input::placeholder { color: rgba(255, 255, 255, 0.25); }
.field-group { display: flex; flex-direction: column; gap: 8px; padding-bottom: 24px; }
.field-label { font-family: "Noto Sans SC", sans-serif; color: rgba(255, 255, 255, 0.55); font-size: 12px; letter-spacing: 4px; }
.required { color: #ef4444; }
.type-toggle { display: flex; gap: 12px; }
.type-btn { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 14px 20px; background: rgba(8, 8, 28, 0.8); border: 1px solid rgba(255, 215, 0, 0.15); border-radius: 10px; cursor: pointer; transition: all 0.25s ease; }
.type-btn:hover { border-color: rgba(255, 215, 0, 0.4); transform: translateY(-2px); }
.type-btn.active { border-color: rgba(255, 215, 0, 0.5); background: rgba(255, 215, 0, 0.08); }
.type-icon { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; color: white; }
.type-name { font-family: "Noto Sans SC", sans-serif; font-size: 13px; color: rgba(255, 255, 255, 0.7); letter-spacing: 2px; }
.type-btn.active .type-name { color: #ffd700; }
.tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
.tag-chip { padding: 6px 12px; background: rgba(8, 8, 28, 0.8); border: 1px solid rgba(255, 215, 0, 0.15); border-radius: 10px; cursor: pointer; transition: all 0.25s ease; }
.tag-chip:hover { border-color: rgba(255, 215, 0, 0.4); }
.tag-chip.selected { border-color: rgba(255, 215, 0, 0.5); background: rgba(255, 215, 0, 0.1); }
.tag-name { font-family: "Noto Sans SC", sans-serif; font-size: 11px; color: rgba(255, 255, 255, 0.7); letter-spacing: 1px; }
.tag-chip.selected .tag-name { color: #ffd700; }
.color-list { display: flex; gap: 12px; }
.color-btn { width: 40px; height: 40px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; transition: all 0.25s ease; }
.color-btn:hover { transform: scale(1.15); }
.color-btn.selected { border-color: white; box-shadow: 0 0 12px rgba(255, 255, 255, 0.4); }
.upload-area { width: 100%; height: 100px; background: rgba(8, 8, 28, 0.8); border: 1px solid rgba(255, 215, 0, 0.15); border-radius: 10px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.25s ease; }
.upload-area:hover { border-color: rgba(255, 215, 0, 0.4); transform: translateY(-2px); }
.upload-placeholder { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.upload-icon { font-size: 24px; color: rgba(255, 215, 0, 0.4); }
.upload-text { font-family: "Noto Sans SC", sans-serif; font-size: 12px; color: rgba(255, 255, 255, 0.4); letter-spacing: 2px; }
.upload-preview { position: relative; width: 80px; height: 80px; }
.upload-preview img { width: 100%; height: 100%; object-fit: cover; border-radius: 8px; }
.remove-btn { position: absolute; top: -8px; right: -8px; width: 20px; height: 20px; border-radius: 50%; background: rgba(220, 38, 38, 0.9); color: white; border: none; cursor: pointer; font-size: 14px; line-height: 1; }
.submit-btn { font-family: "Noto Sans SC", sans-serif; width: 100%; padding: 14px 24px; font-size: 14px; letter-spacing: 6px; font-weight: 600; color: #0a0a1e; background: linear-gradient(135deg, #ffd700, #f0c000); border: none; border-radius: 8px; cursor: pointer; transition: all 0.3s ease; margin-top: 8px; }
.submit-btn:hover:not(:disabled) { background: linear-gradient(135deg, #ffe033, #ffd700); box-shadow: 0 4px 20px rgba(255, 215, 0, 0.35); transform: translateY(-1px); }
.submit-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.close-hint { font-family: "Noto Sans SC", sans-serif; width: 100%; padding: 10px; font-size: 12px; letter-spacing: 4px; color: rgba(255, 255, 255, 0.3); background: transparent; border: none; cursor: pointer; margin-top: 10px; transition: color 0.2s ease; }
.close-hint:hover { color: rgba(255, 255, 255, 0.5); }
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.25s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
.modal-fade-enter-active .modal-box, .modal-fade-leave-active .modal-box { transition: transform 0.25s ease, opacity 0.25s ease; }
.modal-fade-enter-from .modal-box, .modal-fade-leave-to .modal-box { transform: scale(0.95) translateY(10px); opacity: 0; }
</style>
