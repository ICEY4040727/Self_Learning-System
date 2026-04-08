<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <!-- Step 1: 选择模式 -->
        <div v-if="currentStep === 1" class="step-content">
          <div class="modal-header">
            <div class="modal-subtitle">{{ isSage ? 'NEW SAGE' : 'NEW TRAVELER' }}</div>
            <div class="modal-title">{{ isSage ? '创 建 新 知 者' : '创 建 新 旅 者' }}</div>
            <div class="gold-line"></div>
          </div>

          <div class="step-indicator">
            <span class="step-dot active">1</span>
            <span class="step-line"></span>
            <span class="step-dot">2</span>
            <span class="step-line"></span>
            <span class="step-dot">3</span>
          </div>

          <h3 class="step-title">选择创建方式</h3>
          <p class="step-desc">你想如何定义这位知者的人格？</p>

          <div class="mode-cards">
            <div class="mode-card" :class="{ active: createMode === 'quick' }" @click="createMode = 'quick'">
              <div class="mode-icon">⚡</div>
              <div class="mode-title">快速开始</div>
              <div class="mode-desc">从预设模板开始，然后微调细节</div>
            </div>
            <div class="mode-card" :class="{ active: createMode === 'ai' }" @click="createMode = 'ai'">
              <div class="mode-icon">✨</div>
              <div class="mode-title">AI 智能创建</div>
              <div class="mode-desc">通过问答让 AI 为你设计独特人格</div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="$emit('close')">取消</button>
            <button class="btn-primary" @click="nextStep">下一步 →</button>
          </div>
        </div>

        <!-- Step 2: 人格定义 -->
        <div v-else-if="currentStep === 2" class="step-content">
          <div class="modal-header">
            <div class="modal-subtitle">{{ isSage ? 'PERSONA DEFINITION' : 'BASIC INFO' }}</div>
            <div class="modal-title">{{ createMode === 'quick' ? '选择人格模板' : 'AI 智能创建' }}</div>
            <div class="gold-line"></div>
          </div>

          <div class="step-indicator">
            <span class="step-dot" :class="{ active: currentStep >= 1, done: currentStep > 1 }">✓</span>
            <span class="step-line"></span>
            <span class="step-dot active">2</span>
            <span class="step-line"></span>
            <span class="step-dot">3</span>
          </div>

          <!-- 快速模式：模板选择 -->
          <div v-if="createMode === 'quick' && isSage" class="template-section">
            <h3 class="step-title">选择一个人格模板作为起点</h3>
            <div class="template-list">
              <div v-for="(tmpl, idx) in sageTemplates" :key="idx" 
                   class="template-item" 
                   :class="{ active: selectedTemplate === idx }"
                   @click="selectedTemplate = idx">
                <div class="template-radio">
                  <span v-if="selectedTemplate === idx" class="radio-dot"></span>
                </div>
                <div class="template-content">
                  <div class="template-name">{{ tmpl.name }}</div>
                  <div class="template-desc">{{ tmpl.desc }}</div>
                </div>
              </div>
            </div>

            <div class="slider-section">
              <h4 class="slider-title">微调模板</h4>
              <div class="slider-row">
                <span class="slider-label">严谨</span>
                <input type="range" min="0" max="100" v-model="templateAdjustments.strictness" class="slider" />
                <span class="slider-label">温和</span>
              </div>
              <div class="slider-row">
                <span class="slider-label">快速</span>
                <input type="range" min="0" max="100" v-model="templateAdjustments.pace" class="slider" />
                <span class="slider-label">细致</span>
              </div>
              <div class="slider-row">
                <span class="slider-label">严格</span>
                <input type="range" min="0" max="100" v-model="templateAdjustments.feedback" class="slider" />
                <span class="slider-label">鼓励</span>
              </div>
            </div>
          </div>

          <!-- AI 模式：问答 -->
          <div v-else-if="createMode === 'ai' && isSage" class="ai-section">
            <h3 class="step-title">回答几个问题，让 AI 帮你设计人格</h3>
            
            <div class="qa-item">
              <label class="qa-label">Q1: 这个角色最擅长什么领域？</label>
              <div class="qa-options">
                <button v-for="domain in domains" :key="domain" 
                        class="qa-chip" 
                        :class="{ active: aiAnswers.domain === domain }"
                        @click="aiAnswers.domain = domain">
                  {{ domain }}
                </button>
              </div>
            </div>

            <div class="qa-item">
              <label class="qa-label">Q2: 描述一下这个角色的教学风格？</label>
              <div class="qa-options">
                <button v-for="style in teachingStyles" :key="style.value" 
                        class="qa-chip" 
                        :class="{ active: aiAnswers.teachingStyle === style.value }"
                        @click="aiAnswers.teachingStyle = style.value">
                  {{ style.label }}
                </button>
              </div>
            </div>

            <div class="qa-item">
              <label class="qa-label">Q3: 学生遇到困难时，这个角色会怎么做？</label>
              <textarea v-model="aiAnswers.helpApproach" class="qa-textarea" 
                        placeholder="描述你的想法..." rows="2"></textarea>
            </div>

            <div class="qa-item">
              <label class="qa-label">Q4: 你希望这个角色给学生的感觉是？</label>
              <div class="qa-options">
                <button v-for="feel in feelings" :key="feel" 
                        class="qa-chip" 
                        :class="{ active: aiAnswers.feeling === feel }"
                        @click="aiAnswers.feeling = feel">
                  {{ feel }}
                </button>
              </div>
            </div>

            <button v-if="!aiGenerated" class="btn-generate" @click="generatePersona">
              ✨ 让 AI 生成人格
            </button>

            <!-- AI 生成结果预览 -->
            <div v-if="aiGenerated" class="ai-preview">
              <div class="ai-preview-header">
                <span>✨ AI 生成结果</span>
                <button class="btn-regenerate" @click="regeneratePersona">重新生成</button>
              </div>
              <div class="ai-result">
                <div class="ai-result-item">
                  <span class="ai-result-label">角色定位</span>
                  <span class="ai-result-value">{{ generatedPersona?.name_suggestion }}</span>
                </div>
                <div class="ai-result-item">
                  <span class="ai-result-label">特质</span>
                  <div class="trait-tags">
                    <span v-for="trait in generatedPersona?.traits" :key="trait" class="trait-tag">{{ trait }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 旅者模式 -->
          <div v-else class="traveler-section">
            <h3 class="step-title">为你的旅者设置基本信息</h3>
            <div class="field-group">
              <label class="field-label">性格标签</label>
              <div class="tag-list">
                <button v-for="tag in travelerTraits" :key="tag" 
                        type="button" 
                        class="tag-chip" 
                        :class="{ selected: form.tags.includes(tag) }" 
                        @click="toggleTag(tag)">
                  <span class="tag-name">{{ tag }}</span>
                </button>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="prevStep">← 上一步</button>
            <button class="btn-primary" @click="nextStep">下一步 →</button>
          </div>
        </div>

        <!-- Step 3: 角色信息 -->
        <div v-else-if="currentStep === 3" class="step-content">
          <div class="modal-header">
            <div class="modal-subtitle">FINAL STEP</div>
            <div class="modal-title">完善角色信息</div>
            <div class="gold-line"></div>
          </div>

          <div class="step-indicator">
            <span class="step-dot done">✓</span>
            <span class="step-line"></span>
            <span class="step-dot done">✓</span>
            <span class="step-line"></span>
            <span class="step-dot active">3</span>
          </div>

          <div class="field-group">
            <label class="field-label">角 色 名 称 <span class="required">*</span></label>
            <input v-model="form.name" type="text" class="galgame-input" placeholder="为角色命名……" maxlength="20" required />
          </div>

          <div class="field-group">
            <label class="field-label">称 号</label>
            <input v-model="form.title" type="text" class="galgame-input" placeholder="角色的称号或身份……" maxlength="30" />
          </div>

          <div class="field-group">
            <label class="field-label">人 物 简 介</label>
            <textarea v-model="form.description" class="galgame-input" rows="3" placeholder="描述这个角色的背景和特点……" maxlength="200"></textarea>
          </div>

          <div class="field-group">
            <label class="field-label">立 绘 上 传</label>
            <div class="upload-area" @click="triggerFileInput">
              <input ref="fileInput" type="file" accept="image/*" style="display: none" @change="handleFileChange" />
              <div v-if="form.avatar" class="upload-preview">
                <img :src="form.avatar" alt="preview" />
                <button type="button" class="remove-btn" @click.stop="form.avatar = ''">×</button>
              </div>
              <div v-else class="upload-placeholder">
                <span class="upload-icon">+</span>
                <span class="upload-text">点击上传立绘</span>
              </div>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label">色 彩 主 题</label>
            <div class="color-list">
              <button v-for="(color, idx) in colorOptions" :key="idx" type="button" 
                      class="color-btn" 
                      :class="{ selected: form.colorIdx === idx }" 
                      :style="{ background: color }" 
                      @click="form.colorIdx = idx"></button>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="prevStep">← 上一步</button>
            <button class="btn-primary" :disabled="!form.name.trim()" @click="handleSubmit">
              {{ isEdit ? '保存修改' : '完 成' }}
            </button>
          </div>
        </div>

        <button class="close-hint" @click="$emit('close')">取消</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'

interface Props {
  show: boolean
  defaultType?: 'sage' | 'traveler'
  editCharacter?: {
    id: number
    name: string
    title?: string
    description?: string
    avatar?: string
    type: 'sage' | 'traveler'
    personality?: string
    tags?: string[]
  } | null
}

interface Emits {
  (e: 'close'): void
  (e: 'create', data: CreateData): void
  (e: 'update', data: CreateData): void
}

interface CreateData {
  type: 'sage' | 'traveler'
  name: string
  title: string
  description: string
  avatar?: string
  colorIdx: number
  tags: string[]
  personality?: string
  systemPromptTemplate?: string
  traits?: string[]
}

const props = withDefaults(defineProps<Props>(), { defaultType: 'sage' })
const emit = defineEmits<Emits>()

const isEdit = computed(() => !!props.editCharacter)
const isSage = computed(() => props.editCharacter?.type ?? props.defaultType === 'sage')

const currentStep = ref(1)
const createMode = ref<'quick' | 'ai'>('quick')
const selectedTemplate = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)

// AI 生成相关
const aiAnswers = reactive({
  domain: '',
  teachingStyle: '',
  helpApproach: '',
  feeling: ''
})
const aiGenerated = ref(false)
const generatedPersona = ref<{ name_suggestion: string; traits: string[] } | null>(null)

// 模板调整
const templateAdjustments = reactive({
  strictness: 50,
  pace: 50,
  feedback: 50
})

// 表单数据
const form = reactive({
  name: '',
  title: '',
  description: '',
  avatar: '',
  colorIdx: 0,
  tags: [] as string[]
})

// 预设模板
const sageTemplates = [
  { name: '苏格拉底型', desc: '擅长通过反问引导思考，层层递进，适合哲学讨论' },
  { name: '爱因斯坦型', desc: '鼓励大胆假设和实验，适合科学探索' },
  { name: '亚里士多德型', desc: '百科全书式讲解，体系完整，适合系统学习' },
  { name: '孙子型', desc: '策略性思考，引导举一反三，适合方法论学习' }
]

// AI 选项
const domains = ['数学逻辑', '物理科学', '哲学思辨', '编程技术', '文学艺术', '历史人文']
const teachingStyles = [
  { value: 'rigorous', label: '严谨型' },
  { value: 'heuristic', label: '启发型' },
  { value: 'humorous', label: '幽默型' },
  { value: 'practical', label: '实战型' }
]
const feelings = ['慈祥导师', '朋友伙伴', '严格教练', '智慧老者']

// 旅者特质
const travelerTraits = ['好奇心强', '逻辑思维', '探索型', '逻辑严谨', '发散思维', '专注认真']

const colorOptions = [
  'rgba(245, 158, 11, 0.5)', 'rgba(139, 92, 246, 0.5)', 'rgba(16, 185, 129, 0.5)',
  'rgba(220, 38, 38, 0.5)', 'rgba(59, 130, 246, 0.5)', 'rgba(6, 182, 212, 0.5)'
]

// 监听显示状态
watch(() => props.show, (newVal) => {
  if (newVal) {
    // 重置状态
    currentStep.value = 1
    createMode.value = 'quick'
    selectedTemplate.value = 0
    aiGenerated.value = false
    generatedPersona.value = null
    templateAdjustments.strictness = 50
    templateAdjustments.pace = 50
    templateAdjustments.feedback = 50
    
    // 如果是编辑模式，填充数据
    if (props.editCharacter) {
      form.name = props.editCharacter.name
      form.title = props.editCharacter.title || ''
      form.description = props.editCharacter.description || ''
      form.avatar = props.editCharacter.avatar || ''
      form.tags = props.editCharacter.tags || []
    } else {
      form.name = ''
      form.title = ''
      form.description = ''
      form.avatar = ''
      form.tags = []
      form.colorIdx = 0
    }
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

const nextStep = () => {
  if (currentStep.value < 3) currentStep.value++
}

const prevStep = () => {
  if (currentStep.value > 1) currentStep.value--
}

const generatePersona = async () => {
  // 模拟 AI 生成
  const traitsPool = [
    ['耐心', '引导型', '启发式提问'],
    ['严谨', '逻辑强', '重视基础'],
    ['幽默', '类比大师', '鼓励型'],
    ['严格', '高标准', '推动深入'],
    ['温和', '理解学生', '循序渐进']
  ]
  
  generatedPersona.value = {
    name_suggestion: `AI-${Date.now().toString(36)}`,
    traits: traitsPool[Math.floor(Math.random() * traitsPool.length)]
  }
  aiGenerated.value = true
}

const regeneratePersona = () => {
  aiGenerated.value = false
  generatePersona()
}

const handleSubmit = () => {
  if (!form.name.trim()) return
  
  const data: CreateData = {
    type: isSage.value ? 'sage' : 'traveler',
    name: form.name.trim(),
    title: form.title.trim(),
    description: form.description.trim(),
    avatar: form.avatar || undefined,
    colorIdx: form.colorIdx,
    tags: [...form.tags]
  }
  
  if (isSage.value) {
    // 合并性格标签
    if (selectedTemplate.value >= 0) {
      data.personality = sageTemplates[selectedTemplate.value].name
    }
    data.tags = [...form.tags]
    if (generatedPersona.value) {
      data.traits = generatedPersona.value.traits
    }
  }
  
  if (isEdit.value) {
    emit('update', data)
  } else {
    emit('create', data)
  }
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
  width: 580px;
  max-width: 92vw;
  max-height: 90vh;
  overflow-y: auto;
  padding: 32px 40px 24px;
  background: rgba(8, 8, 25, 0.96);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-top: none;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
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

.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid rgba(255, 215, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  transition: all 0.3s ease;
}

.step-dot.active {
  background: rgba(255, 215, 0, 0.2);
  border-color: #ffd700;
  color: #ffd700;
}

.step-dot.done {
  background: rgba(255, 215, 0, 0.4);
  border-color: #ffd700;
  color: #ffd700;
}

.step-line {
  width: 40px;
  height: 2px;
  background: rgba(255, 215, 0, 0.2);
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
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
  margin-bottom: 24px;
}

.step-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 模式选择卡片 */
.mode-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.mode-card {
  flex: 1;
  padding: 24px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 215, 0, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.mode-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
  transform: translateY(-2px);
}

.mode-card.active {
  border-color: rgba(255, 215, 0, 0.6);
  background: rgba(255, 215, 0, 0.08);
}

.mode-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.mode-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: #ffd700;
  margin-bottom: 8px;
}

.mode-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

/* 模板列表 */
.template-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.template-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.1);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.template-item:hover {
  border-color: rgba(255, 215, 0, 0.3);
}

.template-item.active {
  border-color: rgba(255, 215, 0, 0.5);
  background: rgba(255, 215, 0, 0.05);
}

.template-radio {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  align-self: center;
}

.template-item.active .template-radio {
  border-color: #ffd700;
}

.radio-dot {
  width: 10px;
  height: 10px;
  background: #ffd700;
  border-radius: 50%;
}

.template-content {
  flex: 1;
}

.template-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: #ffd700;
  margin-bottom: 4px;
}

.template-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

/* 滑块 */
.slider-section {
  margin-bottom: 24px;
}

.slider-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 16px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.slider-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  width: 36px;
}

.slider-label:last-child {
  text-align: right;
}

.slider {
  flex: 1;
  height: 4px;
  -webkit-appearance: none;
  background: rgba(255, 215, 0, 0.2);
  border-radius: 2px;
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #ffd700;
  border-radius: 50%;
  cursor: pointer;
}

/* AI 问答 */
.qa-item {
  margin-bottom: 20px;
}

.qa-label {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 10px;
}

.qa-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.qa-chip {
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 20px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;
}

.qa-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.qa-chip.active {
  border-color: rgba(255, 215, 0, 0.6);
  background: rgba(255, 215, 0, 0.15);
  color: #ffd700;
}

.qa-textarea {
  width: 100%;
  padding: 12px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 215, 0, 0.25);
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: white;
  resize: none;
  outline: none;
}

.qa-textarea:focus {
  border-color: rgba(255, 215, 0, 0.5);
}

.qa-textarea::placeholder {
  color: rgba(255, 255, 255, 0.3);
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
  margin-top: 16px;
}

.btn-generate:hover {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.3), rgba(255, 215, 0, 0.2));
}

.ai-preview {
  margin-top: 20px;
  padding: 16px;
  background: rgba(255, 215, 0, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 10px;
}

.ai-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: #ffd700;
}

.btn-regenerate {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 4px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
}

.ai-result-item {
  margin-bottom: 12px;
}

.ai-result-item:last-child {
  margin-bottom: 0;
}

.ai-result-label {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 6px;
}

.ai-result-value {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: #ffd700;
}

.trait-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.trait-tag {
  padding: 4px 10px;
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 12px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: #ffd700;
}

/* 通用表单项 */
.field-group {
  margin-bottom: 20px;
}

.field-label {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  letter-spacing: 3px;
  margin-bottom: 10px;
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
  transition: border-color 0.2s ease;
}

.galgame-input:focus {
  border-color: rgba(255, 215, 0, 0.7);
}

.galgame-input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-chip {
  padding: 6px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tag-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.tag-chip.selected {
  border-color: rgba(255, 215, 0, 0.5);
  background: rgba(255, 215, 0, 0.1);
}

.tag-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.tag-chip.selected .tag-name {
  color: #ffd700;
}

.color-list {
  display: flex;
  gap: 12px;
}

.color-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.25s ease;
}

.color-btn:hover {
  transform: scale(1.15);
}

.color-btn.selected {
  border-color: white;
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.4);
}

.upload-area {
  width: 100%;
  height: 100px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s ease;
}

.upload-area:hover {
  border-color: rgba(255, 215, 0, 0.4);
  transform: translateY(-2px);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  font-size: 24px;
  color: rgba(255, 215, 0, 0.4);
}

.upload-text {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 2px;
}

.upload-preview {
  position: relative;
  width: 80px;
  height: 80px;
}

.upload-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

.remove-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(220, 38, 38, 0.9);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}

/* 底部按钮 */
.modal-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 24px;
}

.btn-primary,
.btn-secondary {
  flex: 1;
  padding: 14px 24px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  letter-spacing: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  color: #0a0a1e;
  font-weight: 600;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffe033, #ffd700);
  box-shadow: 0 4px 20px rgba(255, 215, 0, 0.35);
}

.btn-primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  border: 1px solid rgba(255, 215, 0, 0.3);
  color: rgba(255, 255, 255, 0.7);
}

.btn-secondary:hover {
  border-color: rgba(255, 215, 0, 0.5);
  color: #ffd700;
}

.close-hint {
  display: block;
  width: 100%;
  padding: 10px;
  font-family: "Noto Sans SC", sans-serif;
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

/* 过渡动画 */
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
