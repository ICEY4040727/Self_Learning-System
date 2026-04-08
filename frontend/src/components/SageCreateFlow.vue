<template>
  <div class="sage-flow">
    <!-- Step Indicator -->
    <div class="step-indicator">
      <div v-for="step in 5" :key="step" class="step-item">
        <div 
          class="step-dot"
          :class="{ active: currentStep === step, completed: currentStep > step }"
        >
          <span v-if="currentStep > step">✓</span>
          <span v-else>{{ step }}</span>
        </div>
        <span class="step-name">{{ stepNames[step - 1] }}</span>
      </div>
    </div>

    <!-- Step 1: Inspiration Source -->
    <div v-if="currentStep === 1" class="step-content">
      <h3 class="step-title">选择灵感来源</h3>
      <p class="step-desc">你想如何定义这位知者？</p>
      
      <div class="inspiration-cards">
        <div 
          v-for="option in inspirationOptions" 
          :key="option.type"
          class="inspiration-card"
          :class="{ active: selectedInspiration === option.type }"
          @click="selectInspiration(option.type)"
        >
          <span class="card-icon">{{ option.icon }}</span>
          <span class="card-title">{{ option.title }}</span>
          <span class="card-desc">{{ option.desc }}</span>
        </div>
      </div>

      <!-- Template Selection (Quick) -->
      <div v-if="selectedInspiration === 'template'" class="template-section">
        <h4 class="section-title">选择人格模板</h4>
        <div class="template-grid">
          <div 
            v-for="tmpl in SAGE_TEMPLATES" 
            :key="tmpl.key"
            class="template-card"
            :class="{ selected: selectedTemplate === tmpl.key }"
            @click="selectedTemplate = tmpl.key"
          >
            <span class="tmpl-icon" :style="{ color: tmpl.color }">{{ tmpl.icon }}</span>
            <span class="tmpl-name">{{ tmpl.name }}</span>
            <span class="tmpl-desc">{{ tmpl.desc }}</span>
          </div>
        </div>
      </div>

      <!-- AI Generate (Character Inspired) -->
      <div v-else-if="selectedInspiration === 'ai'" class="ai-section">
        <div class="field-group">
          <label class="field-label">描述你想要的老师特质</label>
          <textarea 
            v-model="aiPrompt" 
            class="galgame-input"
            rows="3"
            placeholder="例如：像一位温和但坚持原则的图书管理员，有点神经质但很博学的研究员……"
          ></textarea>
        </div>
        <button 
          v-if="!aiGenerated" 
          class="btn-generate" 
          :disabled="!aiPrompt.trim() || generating"
          @click="callPersonaGenerate"
        >
          {{ generating ? '生成中…' : '✨ 让 AI 生成' }}
        </button>
        <div v-if="aiGenerated && aiResult" class="ai-result">
          <div class="result-header">
            <span>✨ AI 生成结果</span>
            <button class="btn-retry" @click="callPersonaGenerate">重新生成</button>
          </div>
          <div class="result-content">
            <div class="result-item">
              <span class="result-label">角色名</span>
              <span class="result-value">{{ aiResult.name_suggestion }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">性格</span>
              <span class="result-value">{{ aiResult.personality }}</span>
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
            <span v-if="form.colorKey === c.key">✓</span>
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
        <div class="style-tags">
          <button 
            v-for="style in SPEECH_STYLES" 
            :key="style"
            type="button"
            class="style-chip"
            :class="{ selected: form.speechStyles.includes(style) }"
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
          placeholder="曾在……研究……，因为……来到这个世界。"
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
    </div>

    <!-- Step 5: Preview -->
    <div v-else-if="currentStep === 5" class="step-content">
      <h3 class="step-title">预览与完成</h3>

      <div class="preview-card">
        <div class="preview-avatar" :style="{ background: selectedColor?.color }">
          {{ getTemplate()?.icon || '📖' }}
        </div>
        <div class="preview-info">
          <div class="preview-name">{{ form.name || '未命名知者' }}</div>
          <div v-if="form.title" class="preview-title">{{ form.title }}</div>
        </div>
      </div>

      <div class="preview-greeting">
        <div class="greeting-label">初次见面台词</div>
        <div class="greeting-text">"{{ getGreeting() }}"</div>
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
    </div>

    <!-- Navigation -->
    <div class="nav-buttons">
      <button v-if="currentStep > 1" class="btn-back" @click="currentStep--">
        ← 上一步
      </button>
      <button 
        v-if="currentStep < 5" 
        class="btn-next" 
        :disabled="currentStep === 1 && !selectedInspiration"
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
        {{ submitting ? '创建中…' : '让 TA 进入你的世界 →' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { SAGE_TEMPLATES, CHARACTER_COLORS, TRAIT_SLIDERS, SPEECH_STYLES } from '@/constants/characterPresets'

interface Emits {
  (e: 'create', data: any): void
}

const emit = defineEmits<Emits>()

const currentStep = ref(1)
const stepNames = ['灵感', '外观', '性格', '背景', '预览']

const selectedInspiration = ref<'template' | 'ai' | 'custom' | null>(null)
const selectedTemplate = ref('')
const aiPrompt = ref('')
const aiGenerated = ref(false)
const aiResult = ref<any>(null)
const generating = ref(false)
const submitting = ref(false)

const inspirationOptions = [
  { type: 'template' as const, icon: '🎲', title: '从模板开始', desc: '选择一个预设人格，快速上手' },
  { type: 'ai' as const, icon: '🎬', title: 'AI 智能生成', desc: '描述你的想法，AI 帮你设计' },
  { type: 'custom' as const, icon: '✍️', title: '完全自定义', desc: '从零开始塑造角色' },
]

const form = reactive({
  name: '',
  title: '',
  background: '',
  personality: '',
  colorKey: 'gold',
  traits: {
    strictness: 3,
    pace: 5,
    questioning: 7,
    warmth: 6,
    humor: 4,
  } as Record<string, number>,
  speechStyles: [] as string[],
})

const selectedColor = computed(() => 
  CHARACTER_COLORS.find(c => c.key === form.colorKey)
)

const getTemplate = () => 
  SAGE_TEMPLATES.find(t => t.key === selectedTemplate.value)

const getGreeting = () => {
  if (aiResult.value?.greeting) return aiResult.value.greeting
  if (selectedTemplate.value) {
    const tmpl = getTemplate()
    return tmpl?.greeting || '让我们开始学习吧。'
  }
  return '你好，我是你的学习伙伴。'
}

const selectInspiration = (type: 'template' | 'ai' | 'custom') => {
  selectedInspiration.value = type
  if (type === 'template' && !selectedTemplate.value) {
    selectedTemplate.value = SAGE_TEMPLATES[0].key
  }
}

const toggleSpeechStyle = (style: string) => {
  const idx = form.speechStyles.indexOf(style)
  if (idx === -1) {
    form.speechStyles.push(style)
  } else {
    form.speechStyles.splice(idx, 1)
  }
}

const callPersonaGenerate = async () => {
  if (!aiPrompt.value.trim()) return
  
  generating.value = true
  try {
    // TODO: 调用 API /persona/generate
    // 暂时模拟
    await new Promise(resolve => setTimeout(resolve, 1000))
    aiResult.value = {
      name_suggestion: '星渊顾问',
      personality: '博学多识，善于用比喻解释复杂概念',
      greeting: '知识的海洋无边无际，愿与你一同探索。',
      traits: { strictness: 4, pace: 5, questioning: 6, warmth: 7, humor: 3 },
    }
    aiGenerated.value = true
    
    // 填充表单
    if (aiResult.value.name_suggestion) form.name = aiResult.value.name_suggestion
    if (aiResult.value.traits) {
      Object.assign(form.traits, aiResult.value.traits)
    }
  } finally {
    generating.value = false
  }
}

const handleSubmit = async () => {
  if (!form.name.trim()) return
  
  submitting.value = true
  try {
    emit('create', {
      type: 'sage',
      name: form.name.trim(),
      title: form.title.trim(),
      background: form.background.trim(),
      personality: form.personality.trim(),
      colorKey: form.colorKey,
      traits: { ...form.traits },
      speechStyles: [...form.speechStyles],
      template_name: selectedTemplate.value || 'custom',
      greeting: getGreeting(),
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
