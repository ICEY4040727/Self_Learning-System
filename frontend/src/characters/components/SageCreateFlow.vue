<template>
  <div class="sage-flow">
    <!-- Step Indicator -->
    <div class="step-indicator">
      <div v-for="step in 5" :key="step" class="step-item">
        <div 
          class="step-dot"
          :class="{ active: currentStep === step, completed: currentStep > step }"
        >
          <span v-if="currentStep > step">[v]</span>
          <span v-else>{{ step }}</span>
        </div>
        <span class="step-name">{{ stepNames[step - 1] }}</span>
      </div>
    </div>

    <!-- Step 1: Inspiration Prompt -->
    <div v-if="currentStep === 1" class="step-content">
      <h3 class="step-title">描述你想要的知者</h3>
      <p class="step-desc">写一点灵感，AI 会先生成字段；后面每一步都可以继续微调。</p>

      <div class="ai-section">
        <div class="field-group">
          <label class="field-label">角色灵感</label>
          <textarea
            v-model="aiPrompt"
            class="galgame-input"
            rows="4"
            placeholder="例如：一位温和但坚持原则的图书管理员，善于用追问帮助我把问题拆清楚……"
          ></textarea>
        </div>
        <button
          class="btn-generate"
          :disabled="!aiPrompt.trim() || generating"
          @click="callPersonaGenerate"
        >
          {{ generating ? '生成中…' : '* AI 生成字段' }}
        </button>
        <div v-if="generateError" class="generate-error">{{ generateError }}</div>

        <div v-if="aiResult" class="ai-result">
          <div class="result-header">
            <span>* 已回填到后续表单</span>
            <button class="btn-retry" :disabled="generating" @click="callPersonaGenerate">重新生成</button>
          </div>
          <div class="result-content">
            <div class="result-item">
              <span class="result-label">角色名</span>
              <span class="result-value">{{ aiResult.name_suggestion }}</span>
            </div>
            <div class="result-item" v-if="aiResult.title_suggestion">
              <span class="result-label">头衔</span>
              <span class="result-value">{{ aiResult.title_suggestion }}</span>
            </div>
            <div class="result-item" v-if="aiResult.personality">
              <span class="result-label">性格</span>
              <span class="result-value">{{ aiResult.personality }}</span>
            </div>
            <div class="result-item" v-if="aiResult.speech_style">
              <span class="result-label">话风</span>
              <span class="result-value">{{ aiResult.speech_style }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 2: Appearance -->
    <div v-else-if="currentStep === 2" class="step-content">
      <h3 class="step-title">外观与名片</h3>
      
      <div class="field-group">
        <label class="field-label">知 者 名 称 <span class="required">*</span></label>
        <input 
          v-model="form.name" 
          type="text" 
          class="galgame-input" 
          placeholder="为知者命名……" 
          maxlength="20" 
        />
      </div>

      <div class="field-group">
        <label class="field-label">称 号</label>
        <input 
          v-model="form.title" 
          type="text" 
          class="galgame-input" 
          placeholder="例如：雾港学院首席研究员" 
          maxlength="30" 
        />
      </div>

      <div class="field-group">
        <label class="field-label">主 题 色 彩</label>
        <div class="color-grid">
          <button 
            v-for="c in CHARACTER_COLORS" 
            :key="c.key"
            type="button"
            class="color-btn"
            :class="{ selected: form.colorKey === c.key }"
            :style="{ background: c.color }"
            @click="form.colorKey = c.key"
          >
            <span v-if="form.colorKey === c.key">[v]</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Step 3: Personality Sliders -->
    <div v-else-if="currentStep === 3" class="step-content">
      <h3 class="step-title">性格与教学风格</h3>
      <p class="step-desc">调整滑块来定义知者的行为方式</p>

      <div class="sliders">
        <div v-for="slider in TRAIT_SLIDERS" :key="slider.key" class="slider-item">
          <div class="slider-header">
            <span class="slider-label left">{{ slider.leftLabel }}</span>
            <span class="slider-title">{{ slider.label }}</span>
            <span class="slider-label right">{{ slider.rightLabel }}</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="10" 
            :value="form.traits[slider.key]" 
            class="trait-slider"
            @input="(e) => form.traits[slider.key] = parseInt((e.target as HTMLInputElement).value)"
          />
          <div class="slider-examples">
            <span class="example left">{{ slider.leftExample }}</span>
            <span class="example right">{{ slider.rightExample }}</span>
          </div>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label">说 话 风 格</label>
        <textarea
          v-model="form.speechStyle"
          class="galgame-input"
          rows="2"
          placeholder="例如：偏文白，常用比喻，先追问再解释。"
          maxlength="120"
        ></textarea>
        <div class="style-tags">
          <button 
            v-for="style in SPEECH_STYLES" 
            :key="style"
            type="button"
            class="style-chip"
            :class="{ selected: hasSpeechStyle(style) }"
            @click="toggleSpeechStyle(style)"
          >
            {{ style }}
          </button>
        </div>
      </div>
    </div>

    <!-- Step 4: Background Story -->
    <div v-else-if="currentStep === 4" class="step-content">
      <h3 class="step-title">背景故事</h3>
      <p class="step-desc">（可跳过）描述知者的过往经历</p>

      <div class="field-group">
        <label class="field-label">背 景</label>
        <textarea 
          v-model="form.background" 
          class="galgame-input" 
          rows="4"
          placeholder="曾长期研究……，逐渐形成了……的学习引导方式。"
          maxlength="200"
        ></textarea>
        <div class="char-count">{{ form.background.length }}/200</div>
      </div>

      <div class="field-group">
        <label class="field-label">人 格 特 征</label>
        <textarea 
          v-model="form.personality" 
          class="galgame-input" 
          rows="3"
          placeholder="这位知者的性格特点是……"
          maxlength="120"
        ></textarea>
        <div class="char-count">{{ form.personality.length }}/120</div>
      </div>

      <div class="field-group">
        <label class="field-label">初 次 见 面 台 词</label>
        <input
          v-model="form.greeting"
          type="text"
          class="galgame-input"
          placeholder="例如：先告诉我，你现在最想弄清楚的问题是什么？"
          maxlength="60"
        />
      </div>

      <div class="llm-section">
        <h4 class="section-title">LLM Config</h4>
        <div class="field-grid">
          <div class="field-group">
            <label class="field-label">Provider</label>
            <select v-model="form.llm.provider" class="galgame-input">
              <option v-for="p in llmProviderOptions" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div class="field-group">
            <label class="field-label">Model</label>
            <input v-model="form.llm.model" type="text" class="galgame-input" placeholder="gpt-4o-mini" />
          </div>
        </div>
        <div class="field-group">
          <label class="field-label">Base URL</label>
          <input v-model="form.llm.base_url" type="text" class="galgame-input" placeholder="https://api.openai.com/v1" />
        </div>
        <div class="field-grid">
          <div class="field-group">
            <label class="field-label">Temperature <span>{{ form.llm.temperature.toFixed(1) }}</span></label>
            <input v-model.number="form.llm.temperature" type="range" min="0" max="2" step="0.1" class="trait-slider" />
          </div>
          <div class="field-group">
            <label class="field-label">Max Tokens <span>{{ form.llm.max_tokens }}</span></label>
            <input v-model.number="form.llm.max_tokens" type="range" min="128" max="8192" step="128" class="trait-slider" />
          </div>
        </div>
      </div>
    </div>

    <!-- Step 5: Preview -->
    <div v-else-if="currentStep === 5" class="step-content">
      <h3 class="step-title">预览与完成</h3>

      <div class="preview-card">
        <div class="preview-avatar" :style="{ background: selectedColor?.color }">
          {{ form.name?.charAt(0) || '知' }}
        </div>
        <div class="preview-info">
          <div class="preview-name">{{ form.name || '未命名知者' }}</div>
          <div v-if="form.title" class="preview-title">{{ form.title }}</div>
        </div>
      </div>

      <div class="preview-greeting">
        <div class="greeting-label">初次见面台词</div>
        <div class="greeting-text">"{{ form.greeting || '你好，我是你的学习伙伴。' }}"</div>
      </div>

      <div class="preview-traits">
        <div class="traits-label">性格特点</div>
        <div class="traits-grid">
          <div v-for="slider in TRAIT_SLIDERS" :key="slider.key" class="trait-preview">
            <span class="trait-name">{{ slider.label }}</span>
            <span class="trait-value">{{ form.traits[slider.key] }}/10</span>
          </div>
        </div>
      </div>
      <div class="preview-traits">
        <div class="traits-label">LLM Config</div>
        <div class="traits-grid">
          <div class="trait-preview">
            <span class="trait-name">Provider</span>
            <span class="trait-value">{{ form.llm.provider }}</span>
          </div>
          <div class="trait-preview">
            <span class="trait-name">Model</span>
            <span class="trait-value">{{ form.llm.model || 'fallback' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <div class="nav-buttons">
      <button v-if="currentStep > 1" class="btn-back" @click="currentStep--">
        ← 上一步
      </button>
      <button 
        v-if="currentStep < 5" 
        class="btn-next" 
        @click="currentStep++"
      >
        下一步 →
      </button>
      <button 
        v-else 
        class="btn-submit"
        :disabled="!form.name.trim() || submitting"
        @click="handleSubmit"
      >
        {{ submitting ? '创建中…' : '创建知者 →' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import client from '@/shared/api/client'
import { CHARACTER_COLORS, TRAIT_SLIDERS, SPEECH_STYLES } from '@/characters/constants/characterPresets'

interface PersonaGenerateResult {
  name_suggestion?: string
  title_suggestion?: string
  background?: string
  personality?: string
  speech_style?: string
  traits?: Record<string, number>
  system_prompt_template?: string
  greeting?: string
  warnings?: string[]
}

interface Emits {
  (e: 'create', data: Record<string, any>): void
}

const emit = defineEmits<Emits>()

const currentStep = ref(1)
const stepNames = ['灵感', '外观', '性格', '背景', '预览']
const aiPrompt = ref('')
const aiResult = ref<PersonaGenerateResult | null>(null)
const generating = ref(false)
const generateError = ref('')
const submitting = ref(false)

const defaultTraits = () => ({
  strictness: 3,
  pace: 5,
  questioning: 7,
  warmth: 6,
  humor: 4,
})

const form = reactive({
  name: '',
  title: '',
  background: '',
  personality: '',
  greeting: '',
  systemPromptTemplate: '',
  colorKey: 'gold',
  traits: defaultTraits() as Record<string, number>,
  speechStyle: '',
  llm: {
    provider: 'claude',
    model: '',
    base_url: '',
    temperature: 0.7,
    max_tokens: 2048,
  },
})

const llmProviderOptions = ['claude', 'openai', 'deepseek', 'local', 'custom']

const selectedColor = computed(() =>
  CHARACTER_COLORS.find(c => c.key === form.colorKey),
)

const splitSpeechStyle = () =>
  form.speechStyle
    .split(/[、,，]/)
    .map(item => item.trim())
    .filter(Boolean)

const hasSpeechStyle = (style: string) =>
  splitSpeechStyle().includes(style)

const toggleSpeechStyle = (style: string) => {
  const current = splitSpeechStyle()
  const idx = current.indexOf(style)
  if (idx === -1) {
    current.push(style)
  } else {
    current.splice(idx, 1)
  }
  form.speechStyle = current.join('、')
}

const applyPersonaResult = (result: PersonaGenerateResult) => {
  if (result.name_suggestion) form.name = result.name_suggestion
  if (result.title_suggestion) form.title = result.title_suggestion
  if (result.background) form.background = result.background
  if (result.personality) form.personality = result.personality
  if (result.greeting) form.greeting = result.greeting
  if (result.system_prompt_template) form.systemPromptTemplate = result.system_prompt_template
  if (result.speech_style) form.speechStyle = result.speech_style
  if (result.traits) Object.assign(form.traits, result.traits)
}

const callPersonaGenerate = async () => {
  if (!aiPrompt.value.trim()) return

  generating.value = true
  generateError.value = ''
  try {
    const { data } = await client.post('/persona/generate', {
      description: aiPrompt.value.trim(),
      inspiration_type: 'freeform',
    })
    aiResult.value = data as PersonaGenerateResult
    applyPersonaResult(aiResult.value)
  } catch (error) {
    const detail = (error as any)?.response?.data?.detail
    generateError.value = typeof detail === 'string'
      ? detail
      : 'AI 生成失败，请检查设置后重试。'
  } finally {
    generating.value = false
  }
}

const handleSubmit = async () => {
  if (!form.name.trim()) return

  submitting.value = true
  try {
    const selectedTags = splitSpeechStyle().filter(style => SPEECH_STYLES.includes(style))
    emit('create', {
      type: 'sage',
      name: form.name.trim(),
      title: form.title.trim() || undefined,
      background: form.background.trim() || undefined,
      personality: form.personality.trim() || undefined,
      greeting: form.greeting.trim() || undefined,
      speech_style: form.speechStyle.trim() || undefined,
      tags: selectedTags,
      template_name: 'custom',
      traits: { ...form.traits },
      system_prompt_template: form.systemPromptTemplate.trim() || undefined,
      sprites: selectedColor.value ? { color: selectedColor.value.color } : undefined,
      llm_settings: {
        provider: form.llm.provider || undefined,
        model: form.llm.model || undefined,
        base_url: form.llm.base_url || undefined,
        temperature: form.llm.temperature,
        max_tokens: form.llm.max_tokens,
      },
    })
  } finally {
    submitting.value = false
  }
}

</script>

<style scoped>
.sage-flow {
  padding: 16px 0;
}

/* Step Indicator */
.step-indicator {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
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

.step-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

/* Step Content */
.step-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 16px;
  color: #ffd700;
  text-align: center;
  margin-bottom: 8px;
}

.step-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
  margin-bottom: 20px;
}

/* Inspiration Cards */
.inspiration-cards {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.inspiration-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 215, 0, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  text-align: center;
}

.inspiration-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
  transform: translateY(-2px);
}

.inspiration-card.active {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.08);
}

.card-icon {
  font-size: 28px;
}

.card-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: #ffd700;
}

.card-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

/* Template Section */
.template-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.template-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 10px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.template-card:hover {
  border-color: rgba(255, 215, 0, 0.3);
}

.template-card.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.tmpl-icon {
  font-size: 24px;
}

.tmpl-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: #ffd700;
}

.tmpl-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

/* AI Section */
.ai-section {
  margin-top: 16px;
}

.btn-generate {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(255, 215, 0, 0.1));
  border: 1px solid rgba(255, 215, 0, 0.4);
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: #ffd700;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-generate:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.3), rgba(255, 215, 0, 0.2));
}

.btn-generate:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.generate-error {
  margin-top: 10px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  line-height: 1.5;
  color: #fca5a5;
}

.ai-result {
  margin-top: 16px;
  padding: 14px;
  background: rgba(255, 215, 0, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 10px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: #ffd700;
}

.btn-retry {
  padding: 4px 10px;
  background: transparent;
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 4px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
}

.result-item {
  margin-bottom: 10px;
}

.result-label {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 4px;
}

.result-value {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: #ffd700;
}

/* Form Elements */
.field-group {
  margin-bottom: 18px;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.llm-section {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 215, 0, 0.14);
}

.field-label {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  color: rgba(255, 255, 255, 0.55);
  font-size: 11px;
  letter-spacing: 3px;
  margin-bottom: 8px;
}

.required {
  color: #ef4444;
}

.galgame-input {
  width: 100%;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.4);
  border: 2px solid rgba(255, 215, 0, 0.4);
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: white;
  outline: none;
}

.galgame-input:focus {
  border-color: rgba(255, 215, 0, 0.7);
}

.galgame-input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

.char-count {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
  text-align: right;
  margin-top: 4px;
}

/* Color Grid */
.color-grid {
  display: flex;
  gap: 10px;
}

.color-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: white;
  transition: all 0.2s ease;
}

.color-btn.selected {
  border-color: white;
  transform: scale(1.1);
}

/* Trait Sliders */
.sliders {
  margin-bottom: 20px;
}

.slider-item {
  margin-bottom: 20px;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.slider-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.slider-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
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
  width: 18px;
  height: 18px;
  background: #ffd700;
  border-radius: 50%;
  cursor: pointer;
}

.slider-examples {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
}

.example {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
  max-width: 45%;
}

/* Speech Styles */
.style-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.style-chip {
  padding: 6px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 16px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;
}

.style-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.style-chip.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.15);
  color: #ffd700;
}

/* Preview Card */
.preview-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 12px;
  margin-bottom: 16px;
}

.preview-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.preview-info {
  flex: 1;
}

.preview-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 16px;
  color: #ffd700;
  letter-spacing: 2px;
}

.preview-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 4px;
}

/* Preview Greeting */
.preview-greeting {
  padding: 14px;
  background: rgba(255, 215, 0, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  margin-bottom: 16px;
}

.greeting-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 6px;
}

.greeting-text {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  font-style: italic;
}

/* Preview Traits */
.preview-traits {
  margin-bottom: 20px;
}

.traits-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 10px;
}

.traits-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.trait-preview {
  display: flex;
  justify-content: space-between;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
}

.trait-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.trait-value {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: #ffd700;
}

/* Navigation Buttons */
.nav-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.btn-back {
  flex: 1;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-back:hover {
  color: rgba(255, 255, 255, 0.8);
  border-color: rgba(255, 215, 0, 0.4);
}

.btn-next {
  flex: 2;
  padding: 12px;
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #0a0a1e;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-next:hover:not(:disabled) {
  box-shadow: 0 4px 20px rgba(255, 215, 0, 0.3);
}

.btn-next:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-submit {
  flex: 2;
  padding: 14px;
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #0a0a1e;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-submit:hover:not(:disabled) {
  box-shadow: 0 4px 20px rgba(255, 215, 0, 0.35);
}

.btn-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
