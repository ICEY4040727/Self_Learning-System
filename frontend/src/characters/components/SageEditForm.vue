<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="edit-modal">
      <!-- Header -->
      <div class="edit-header">
        <div class="edit-subtitle">{{ isSage ? 'EDIT SAGE' : 'EDIT TRAVELER' }}</div>
        <div class="edit-title">{{ isSage ? '编 辑 知 者' : '编 辑 旅 者' }}</div>
        <div class="gold-line"></div>
      </div>

      <!-- Form -->
      <div class="edit-body">
        <!-- Name -->
        <div class="form-group">
          <label>名字</label>
          <input v-model="form.name" type="text" placeholder="角色名字" />
        </div>

        <!-- Title -->
        <div class="form-group">
          <label>头衔</label>
          <input v-model="form.title" type="text" placeholder="如：雾港学院首席研究员" />
        </div>

        <!-- Background -->
        <div class="form-group">
          <label>背景故事</label>
          <textarea v-model="form.background" placeholder="角色的背景故事…" rows="3"></textarea>
        </div>

        <!-- Personality -->
        <div class="form-group">
          <label>性格描述</label>
          <textarea v-model="form.personality" placeholder="角色的性格特点…" rows="2"></textarea>
        </div>

        <!-- Speech Style -->
        <div class="form-group">
          <label>说话风格</label>
          <textarea v-model="form.speech_style" placeholder="角色的说话方式…" rows="2"></textarea>
        </div>

        <!-- Tags -->
        <div class="form-group">
          <label>标签</label>
          <div class="tags-input-area">
            <div class="tags-display">
              <span v-for="(tag, i) in form.tags" :key="i" class="tag-item">
                {{ tag }}
                <button class="tag-remove" @click="removeTag(i)">✕</button>
              </span>
            </div>
            <div class="tag-input-row">
              <input
                v-model="newTag"
                type="text"
                placeholder="添加标签后回车"
                @keydown.enter.prevent="addTag"
              />
            </div>
          </div>
        </div>

        <!-- Traits (5-dimension) -->
        <div v-if="isSage && form.traits" class="form-group">
          <label>性格参数</label>
          <div class="traits-grid">
            <div v-for="(label, key) in traitLabels" :key="key" class="trait-row">
              <span class="trait-name">{{ label }}</span>
              <input
                type="range"
                :min="1"
                :max="10"
                :value="form.traits[key] ?? 5"
                @input="updateTrait(key, ($event.target as HTMLInputElement).value)"
                class="trait-slider"
              />
              <span class="trait-value">{{ form.traits[key] ?? 5 }}</span>
            </div>
          </div>
        </div>
        <div v-if="isSage" class="form-group">
          <label>LLM 配置</label>
          <div class="field-grid">
            <div class="form-group">
              <label>Provider</label>
              <select v-model="form.llm.provider">
                <option v-for="p in llmProviderOptions" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Model</label>
              <input v-model="form.llm.model" type="text" placeholder="gpt-4o-mini" />
            </div>
          </div>
          <div class="form-group">
            <label>Base URL</label>
            <input v-model="form.llm.base_url" type="text" placeholder="https://api.openai.com/v1" />
          </div>
          <div class="field-grid">
            <div class="form-group">
              <label>Temperature <span>{{ form.llm.temperature.toFixed(1) }}</span></label>
              <input v-model.number="form.llm.temperature" type="range" min="0" max="2" step="0.1" />
            </div>
            <div class="form-group">
              <label>Max Tokens <span>{{ form.llm.max_tokens }}</span></label>
              <input v-model.number="form.llm.max_tokens" type="range" min="128" max="8192" step="128" />
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="edit-footer">
        <button class="btn-cancel" @click="$emit('close')">取消</button>
        <button class="btn-save" :disabled="!form.name.trim() || saving" @click="handleSave">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { characterApi } from '@/shared/api/character'

interface CharacterFull {
  id: number
  name: string
  type: string
  title?: string
  background?: string
  personality?: string
  speech_style?: string
  tags?: string[]
  traits?: Record<string, number>
  llm_settings?: {
    provider?: string
    model?: string
    base_url?: string
    temperature?: number
    max_tokens?: number
  }
}

const props = defineProps<{
  show: boolean
  character: CharacterFull | null
}>()

const emit = defineEmits<{
  close: []
  saved: [character: any]
}>()

const traitLabels: Record<string, string> = {
  strictness: '严厉',
  pace: '节奏',
  questioning: '追问',
  warmth: '温暖',
  humor: '幽默',
}

const isSage = ref(true)
const saving = ref(false)
const newTag = ref('')

const form = reactive({
  name: '',
  title: '',
  background: '',
  personality: '',
  speech_style: '',
  tags: [] as string[],
  traits: {} as Record<string, number>,
  llm: {
    provider: 'claude',
    model: '',
    base_url: '',
    temperature: 0.7,
    max_tokens: 2048,
  },
})

const llmProviderOptions = ['claude', 'openai', 'deepseek', 'local', 'custom']

watch([() => props.show, () => props.character], async ([showVal, charVal]) => {
  if (showVal && charVal?.id) {
    isSage.value = (charVal as any).type === 'sage'
    // Fetch fresh data from API
    try {
      const full = await characterApi.get(charVal.id)
      console.log('[SageEditForm] API response:', full)
      form.name = full.name || ''
      form.title = (full as any).title || ''
      form.background = full.background || ''
      form.personality = full.personality || ''
      form.speech_style = full.speech_style || ''
      form.tags = [...(full.tags || [])]
      form.traits = { ...(full as any).traits || {} }
      form.llm.provider = full.llm_settings?.provider || 'claude'
      form.llm.model = full.llm_settings?.model || ''
      form.llm.base_url = full.llm_settings?.base_url || ''
      form.llm.temperature = full.llm_settings?.temperature ?? 0.7
      form.llm.max_tokens = full.llm_settings?.max_tokens ?? 2048
    } catch (err) {
      console.error('[SageEditForm] API fetch failed, using prop data:', err)
      form.name = charVal.name || ''
      form.title = (charVal as any).title || ''
      form.background = (charVal as any).background || ''
      form.personality = (charVal as any).personality || ''
      form.speech_style = (charVal as any).speech_style || ''
      form.tags = [...((charVal as any).tags || [])]
      form.traits = { ...((charVal as any).traits || {}) }
      form.llm.provider = (charVal as any).llm_settings?.provider || 'claude'
      form.llm.model = (charVal as any).llm_settings?.model || ''
      form.llm.base_url = (charVal as any).llm_settings?.base_url || ''
      form.llm.temperature = (charVal as any).llm_settings?.temperature ?? 0.7
      form.llm.max_tokens = (charVal as any).llm_settings?.max_tokens ?? 2048
    }
  }
}, { flush: 'post' })

const addTag = () => {
  const tag = newTag.value.trim()
  if (tag && !form.tags.includes(tag)) {
    form.tags.push(tag)
    newTag.value = ''
  }
}

const removeTag = (index: number) => {
  form.tags.splice(index, 1)
}

const updateTrait = (key: string, value: string) => {
  form.traits[key] = parseInt(value, 10)
}

const handleSave = async () => {
  if (!props.character?.id || !form.name.trim()) return
  saving.value = true
  try {
    const payload: Record<string, any> = {
      name: form.name.trim(),
      type: props.character.type,
      title: form.title || undefined,
      background: form.background || undefined,
      personality: form.personality || undefined,
      speech_style: form.speech_style || undefined,
      tags: form.tags,
    }
    if (isSage.value && Object.keys(form.traits).length > 0) {
      payload.traits = form.traits
    }
    if (isSage.value) {
      payload.llm_settings = {
        provider: form.llm.provider || undefined,
        model: form.llm.model || undefined,
        base_url: form.llm.base_url || undefined,
        temperature: form.llm.temperature,
        max_tokens: form.llm.max_tokens,
      }
    }
    const updated = await characterApi.update(props.character.id, payload)
    emit('saved', updated)
  } catch (err) {
    console.error('Failed to save character:', err)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.edit-modal {
  width: 560px;
  max-width: 92vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background: rgba(8, 8, 25, 0.98);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

/* Header */
.edit-header {
  text-align: center;
  padding: 24px 24px 16px;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
}

.edit-subtitle {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 215, 0, 0.5);
  letter-spacing: 4px;
  margin-bottom: 4px;
}

.edit-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 20px;
  color: #ffd700;
  letter-spacing: 6px;
}

.gold-line {
  width: 60px;
  height: 2px;
  background: linear-gradient(90deg, transparent, #ffd700, transparent);
  margin: 12px auto 0;
}

/* Body */
.edit-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 28px;
}

.form-group {
  margin-bottom: 18px;
}

.form-group label {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 215, 0, 0.7);
  letter-spacing: 2px;
  margin-bottom: 6px;
}

.form-group input[type="text"],
.form-group textarea {
  width: 100%;
  padding: 10px 14px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-group input[type="text"]:focus,
.form-group textarea:focus {
  border-color: rgba(255, 215, 0, 0.5);
}

.form-group textarea {
  resize: vertical;
  min-height: 60px;
  line-height: 1.6;
}

/* Tags */
.tags-input-area {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 8px 12px;
}

.tags-display {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 215, 0, 0.8);
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.2);
  padding: 3px 10px;
  border-radius: 12px;
}

.tag-remove {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  font-size: 10px;
  cursor: pointer;
  padding: 0 2px;
}

.tag-remove:hover {
  color: #ef4444;
}

.tag-input-row input {
  width: 100%;
  padding: 4px 0;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: #fff;
  background: transparent;
  border: none;
  outline: none;
}

/* Traits */
.traits-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.trait-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.trait-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  width: 40px;
  flex-shrink: 0;
}

.trait-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  outline: none;
}

.trait-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ffd700;
  cursor: pointer;
  border: 2px solid rgba(0, 0, 0, 0.3);
}

.trait-value {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 215, 0, 0.8);
  width: 24px;
  text-align: right;
  flex-shrink: 0;
}

/* Footer */
.edit-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 28px;
  border-top: 1px solid rgba(255, 215, 0, 0.1);
}

.btn-cancel {
  padding: 10px 20px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 2px;
}

.btn-cancel:hover {
  border-color: rgba(255, 255, 255, 0.4);
  color: #fff;
}

.btn-save {
  padding: 10px 24px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: #0a0a1e;
  background: rgba(255, 215, 0, 0.9);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
  letter-spacing: 2px;
}

.btn-save:hover:not(:disabled) {
  background: #ffd700;
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
