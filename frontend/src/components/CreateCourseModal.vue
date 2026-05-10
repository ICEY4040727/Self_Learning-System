<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="currentStep < 3 ? $emit('close') : undefined">
      <div class="modal-box">
        <!-- Header -->
        <div class="modal-header">
          <div class="modal-subtitle">NEW COURSE</div>
          <div class="modal-title">创 建 课 程</div>
          <div class="gold-line"></div>

          <!-- Step Indicator -->
          <div class="step-indicator">
            <div
              v-for="step in 3"
              :key="step"
              class="step-dot"
              :class="{ active: currentStep === step, completed: currentStep > step }"
            >
              <span v-if="currentStep > step">[v]</span>
              <span v-else>{{ step }}</span>
            </div>
          </div>
          <div class="step-label">
            <span v-if="currentStep === 1">选择学习材料</span>
            <span v-else-if="currentStep === 2">设定学习目标</span>
            <span v-else>AI 生成课程</span>
          </div>
        </div>

        <!-- Step 1: Course Name + Domain + Textbook Selection -->
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

          <div class="field-group">
            <label class="field-label">教 材 (可 选)</label>
            <p class="field-hint">选择已有教材或上传新教材，AI 将基于教材生成课程大纲</p>

            <!-- Textbook selection from bookshelf -->
            <div v-if="bookshelfItems.length > 0" class="textbook-list">
              <div
                v-for="item in bookshelfItems"
                :key="item.id"
                class="textbook-item"
                :class="{ selected: selectedBookIds.includes(item.id) }"
                @click="toggleBook(item.id)"
              >
                <span class="textbook-name">{{ item.title || item.filename }}</span>
                <span class="textbook-size">{{ formatSize(item.file_size) }}</span>
              </div>
            </div>
            <div v-else class="textbook-empty">暂无教材，可直接上传</div>

            <!-- Upload area -->
            <div class="upload-area" @click="triggerUpload" @dragover.prevent @drop.prevent="handleDrop">
              <input ref="fileInput" type="file" hidden accept=".pdf,.epub,.txt,.md" @change="handleFileSelect" />
              <div v-if="uploading" class="upload-progress">
                <div class="progress-bar"><div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div></div>
                <span>{{ uploadProgress }}%</span>
              </div>
              <div v-else class="upload-hint">+ 点击或拖拽上传教材 (PDF / EPUB / TXT)</div>
            </div>
          </div>

          <button type="submit" class="submit-btn" :disabled="!form.name.trim() || !form.domain">
            下 一 步
          </button>
        </form>

        <!-- Step 2: Learning Preferences (all in one step) -->
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

          <div class="btn-row">
            <button type="button" class="back-btn" @click="currentStep = 1">上一步</button>
            <button type="button" class="submit-btn" :disabled="creating" @click="handleCreateAndGenerate">
              {{ creating ? '创建中…' : '创建并生成课程' }}
            </button>
          </div>
        </div>

        <!-- Step 3: AI Generation Progress -->
        <div v-else-if="currentStep === 3" class="modal-body step-content">
          <div class="generation-section">
            <!-- Course Created -->
            <div class="gen-step" :class="genStatus >= 1 ? 'done' : ''">
              <span class="gen-icon">{{ genStatus >= 1 ? '✓' : '...' }}</span>
              <span class="gen-text">课程已创建</span>
            </div>

            <!-- Linking textbooks -->
            <div v-if="selectedBookIds.length > 0" class="gen-step" :class="genStatus >= 2 ? 'done' : genStatus >= 1 ? 'active' : ''">
              <span class="gen-icon">{{ genStatus >= 2 ? '✓' : genStatus >= 1 ? '◎' : '...' }}</span>
              <span class="gen-text">{{ genStatus >= 2 ? '教材已关联' : '正在关联教材…' }}</span>
            </div>

            <!-- AI Generating -->
            <div class="gen-step" :class="genStatus >= 3 && !genError ? 'done' : genStatus >= 2 ? 'active' : ''">
              <span class="gen-icon">{{ genStatus >= 3 && !genError ? '✓' : genStatus >= 2 ? '◎' : '...' }}</span>
              <span class="gen-text">{{ genStatus >= 3 && !genError ? '课程大纲已生成' : genStatus >= 2 ? aiStage || 'AI 正在生成课程大纲…' : '等待生成' }}</span>
            </div>

            <!-- AI Progress Bar -->
            <div v-if="genStatus >= 2 && genStatus < 3 && !genError" class="ai-progress-section">
              <div class="ai-progress-bar">
                <div class="ai-progress-fill" :style="{ width: Math.round(aiProgress) + '%' }"></div>
              </div>
              <span class="ai-progress-pct">{{ Math.round(aiProgress) }}%</span>
            </div>

            <!-- Generation result preview -->
            <div v-if="generationResult" class="gen-result">
              <div class="gen-result-title">✦ 课程大纲预览</div>
              <div v-if="generationResult.overview" class="gen-overview">{{ generationResult.overview }}</div>
              <div v-if="generationResult.lessons?.length" class="gen-lessons">
                <div v-for="(lesson, i) in generationResult.lessons" :key="i" class="gen-lesson-item">
                  <span class="lesson-order">{{ lesson.order || i + 1 }}</span>
                  <span class="lesson-title">{{ lesson.title }}</span>
                </div>
              </div>
            </div>

            <!-- Error state -->
            <div v-if="genError" class="gen-error">
              <p>⚠ {{ genError }}</p>
              <p class="gen-error-hint">课程已创建，你可以稍后在课程页面重新生成。</p>
            </div>
          </div>

          <div class="btn-row">
            <button
              type="button"
              class="submit-btn"
              :disabled="genStatus < 3"
              @click="handleFinish"
            >
              <span v-if="genStatus < 3" class="btn-waiting">AI 生成中，请稍候…</span>
              <span v-else-if="genError">完成</span>
              <span v-else>进入课程</span>
            </button>
          </div>
        </div>

        <!-- Close hint -->
        <button v-if="currentStep < 3" class="close-hint" @click="$emit('close')">取消</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  COURSE_DOMAINS,
  CURRENT_LEVELS,
  TARGET_LEVELS,
  MOTIVATIONS,
  PACES,
  buildMetaPayload,
} from '@/constants/courseDomains'
import { worldApi } from '@/api/world'
import { courseApi } from '@/api/course'
import { bookshelfApi, type BookshelfItem } from '@/api/bookshelf'

interface Props {
  show: boolean
  worldId: number
}

interface Emits {
  (e: 'close'): void
  (e: 'created', courseId: number): void
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
})

// Textbook state
const bookshelfItems = ref<BookshelfItem[]>([])
const selectedBookIds = ref<number[]>([])
const uploading = ref(false)
const uploadProgress = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)

// Generation state
const genStatus = ref(0) // 0: not started, 1: course created, 2: textbooks linked, 3: AI done
const genError = ref<string | null>(null)
const generationResult = ref<{ overview?: string; lessons?: any[] } | null>(null)
const createdCourseId = ref<number | null>(null)
const aiProgress = ref(0) // 0-100 fake progress
const aiStage = ref('') // current stage text
let aiTimer: ReturnType<typeof setInterval> | null = null

const AI_STAGES = [
  '正在解析教材内容…',
  '分析知识结构与重点…',
  '规划课程大纲…',
  'AI 正在生成课程章节…',
  '编排学习路径…',
  '优化课程内容…',
  '即将完成…',
]

function startAiProgress() {
  aiProgress.value = 0
  aiStage.value = AI_STAGES[0]
  let stageIdx = 0
  const totalDuration = 90000 // 90s total fake timeline
  const interval = 300 // update every 300ms
  const increment = (interval / totalDuration) * 85 // go to ~85% max

  aiTimer = setInterval(() => {
    if (aiProgress.value < 85) {
      // Slow down as it gets higher (easing)
      const remaining = 85 - aiProgress.value
      const step = Math.max(0.2, increment * (remaining / 85))
      aiProgress.value = Math.min(85, aiProgress.value + step)

      // Update stage based on progress
      const newStageIdx = Math.min(Math.floor(aiProgress.value / (85 / AI_STAGES.length)), AI_STAGES.length - 1)
      if (newStageIdx !== stageIdx) {
        stageIdx = newStageIdx
        aiStage.value = AI_STAGES[stageIdx]
      }
    }
  }, interval)
}

function stopAiProgress(success: boolean) {
  if (aiTimer) {
    clearInterval(aiTimer)
    aiTimer = null
  }
  if (success) {
    aiProgress.value = 100
    aiStage.value = '生成完成！'
  }
}

// Load bookshelf items
async function loadBookshelf() {
  try {
    bookshelfItems.value = await bookshelfApi.list()
  } catch {
    bookshelfItems.value = []
  }
}

function toggleBook(id: number) {
  const idx = selectedBookIds.value.indexOf(id)
  if (idx >= 0) {
    selectedBookIds.value.splice(idx, 1)
  } else {
    selectedBookIds.value.push(id)
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) await uploadFile(file)
  target.value = ''
}

async function handleDrop(e: DragEvent) {
  const file = e.dataTransfer?.files?.[0]
  if (file) await uploadFile(file)
}

async function uploadFile(file: File) {
  uploading.value = true
  uploadProgress.value = 0
  try {
    const item = await bookshelfApi.upload(file, (pct) => { uploadProgress.value = pct })
    bookshelfItems.value.unshift(item)
    selectedBookIds.value.push(item.id)
  } catch (err: any) {
    console.error('Upload failed:', err)
  } finally {
    uploading.value = false
  }
}

function formatSize(bytes: number | null): string {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function goToStep2() {
  if (form.value.name.trim() && form.value.domain) {
    currentStep.value = 2
  }
}

async function handleCreateAndGenerate() {
  if (!form.value.name.trim()) return
  creating.value = true
  genError.value = null
  genStatus.value = 0

  try {
    // Step A: Create the course via API
    const meta = buildMetaPayload({
      domain: form.value.domain,
      currentLevel: form.value.currentLevel,
      targetLevel: form.value.targetLevel,
      motivation: form.value.motivation,
      pace: form.value.pace,
    })

    const course = await worldApi.createCourse(props.worldId, {
      name: form.value.name.trim(),
      description: '',
      target_level: form.value.targetLevel || 'understand',
      meta,
    })

    createdCourseId.value = course.id
    currentStep.value = 3
    genStatus.value = 1

    // Step B: Link textbooks if any selected
    if (selectedBookIds.value.length > 0) {
      try {
        await bookshelfApi.batchLinkToCourse(course.id, selectedBookIds.value)
      } catch (err) {
        console.error('Failed to link textbooks:', err)
        // Non-fatal, continue
      }
      genStatus.value = 2
    } else {
      genStatus.value = 2
    }

    // Step C: Generate course content via AI
    startAiProgress()
    try {
      const result = await courseApi.generateCourse(course.id)
      stopAiProgress(true)
      generationResult.value = result
      genStatus.value = 3
    } catch (err: any) {
      stopAiProgress(false)
      console.error('Course generation failed:', err)
      genError.value = err?.response?.data?.detail || err?.message || 'AI 生成失败'
      genStatus.value = 3 // Mark as "done" even on error so user can proceed
    }
  } catch (err: any) {
    genError.value = err?.response?.data?.detail || err?.message || '创建课程失败'
  } finally {
    creating.value = false
  }
}

function handleFinish() {
  if (createdCourseId.value) {
    emit('created', createdCourseId.value)
  }
  emit('close')
}

// Reset on open
watch(() => props.show, (newVal) => {
  if (newVal) {
    currentStep.value = 1
    creating.value = false
    form.value = {
      name: '',
      domain: '',
      currentLevel: '',
      targetLevel: '',
      motivation: '',
      pace: 'normal',
    }
    selectedBookIds.value = []
    genStatus.value = 0
    genError.value = null
    generationResult.value = null
    createdCourseId.value = null
    loadBookshelf()
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

.field-hint {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  margin: 0;
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

/* Textbook List */
.textbook-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 150px;
  overflow-y: auto;
}

.textbook-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.textbook-item:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.textbook-item.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.textbook-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 70%;
}

.textbook-size {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
}

.textbook-empty {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
  padding: 10px;
}

/* Upload Area */
.upload-area {
  margin-top: 8px;
  padding: 16px;
  border: 2px dashed rgba(255, 215, 0, 0.2);
  border-radius: 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-area:hover {
  border-color: rgba(255, 215, 0, 0.5);
  background: rgba(255, 215, 0, 0.03);
}

.upload-hint {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.upload-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
  color: rgba(255, 215, 0, 0.7);
  font-size: 12px;
}

.progress-bar {
  width: 120px;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #ffd700;
  transition: width 0.3s ease;
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

/* Generation Section */
.generation-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 12px 0;
}

.gen-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
}

.gen-step.done {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.05);
}

.gen-step.active {
  border-color: rgba(255, 215, 0, 0.3);
  background: rgba(255, 215, 0, 0.05);
}

.gen-icon {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.3);
  min-width: 24px;
  text-align: center;
}

.gen-step.done .gen-icon {
  color: #10b981;
}

.gen-step.active .gen-icon {
  color: #ffd700;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.gen-text {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.gen-step.done .gen-text {
  color: rgba(16, 185, 129, 0.9);
}

.gen-step.active .gen-text {
  color: #ffd700;
}

/* Generation Result */
.gen-result {
  margin-top: 8px;
  padding: 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 10px;
}

.gen-result-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 215, 0, 0.7);
  letter-spacing: 2px;
  margin-bottom: 10px;
}

.gen-overview {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.6;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.gen-lessons {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gen-lesson-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}

.lesson-order {
  font-size: 11px;
  color: rgba(255, 215, 0, 0.5);
  min-width: 20px;
  text-align: center;
}

.lesson-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

/* AI Progress Bar */
.ai-progress-section {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
}

.ai-progress-bar {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.ai-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(255, 215, 0, 0.6), #ffd700);
  border-radius: 3px;
  transition: width 0.3s ease;
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.3);
}

.ai-progress-pct {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 215, 0, 0.7);
  min-width: 32px;
  text-align: right;
}

/* Error State */
.gen-error {
  padding: 12px 14px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
}

.gen-error p {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(239, 68, 68, 0.8);
  margin: 0;
}

.gen-error-hint {
  margin-top: 6px !important;
  font-size: 11px !important;
  color: rgba(255, 255, 255, 0.3) !important;
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
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-waiting {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  animation: pulse 1.5s infinite;
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