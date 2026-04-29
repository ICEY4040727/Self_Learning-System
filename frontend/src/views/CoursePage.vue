<template>
  <div class="course-page">
    <!-- Background -->
    <div class="scene-bg" :style="{ backgroundImage: `url(${BG_URL})` }"></div>
    <div class="scene-overlay"></div>

    <!-- Header -->
    <div class="char-header">
      <button class="back-btn" @click="goBack">
        <span>←</span> 返回
      </button>
      <h1 class="header-title">{{ course?.name || '课程主页' }}</h1>
      <div style="width: 80px;"></div>
    </div>

    <!-- Content -->
    <div class="char-content">

    <!-- Loading -->
    <div v-if="loading" class="loading">加载中…</div>

    <!-- Error -->
    <div v-else-if="!course" class="error-state">
      <p>无法加载课程信息</p>
      <button class="start-btn" @click="fetchData" style="margin-top: 16px;">重试</button>
    </div>

    <!-- Course Content -->
    <template v-else>
      <!-- Course Overview -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">课 程 信 息</span>
          <span class="section-sublabel">COURSE OVERVIEW</span>
        </div>
        <div class="section-line"></div>
        <div class="course-header">
          <div class="course-icon">{{ domainIcon }}</div>
          <div class="course-title-area">
            <h2 class="course-name">{{ course.name }}</h2>
            <p v-if="course.description" class="course-desc">{{ course.description }}</p>
            <div class="course-meta">
              <span>{{ domainLabel }}</span>
              <span class="separator">·</span>
              <span>{{ createdAgo }}</span>
            </div>
          </div>
          <button class="start-btn" @click="handleStartLearning">
            开始学习 >
          </button>
        </div>
      </div>

      <!-- Progress -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">学 习 进 度</span>
          <span class="section-sublabel">PROGRESS</span>
        </div>
        <div class="section-line"></div>
        <ProgressBar
          :current-level="course.meta?.current_level || 'none'"
          :target-level="course.meta?.target_level || 'understand'"
          :progress="progress"
          :concept-mastered-count="memoryStats?.concept_mastered"
        />
      </div>

      <!-- Textbooks (Phase 2C) -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">教 材</span>
          <span class="section-sublabel">TEXTBOOKS</span>
        </div>
        <div class="section-line"></div>
        <div class="textbook-area">
          <!-- Upload zone -->
          <div class="textbook-upload" @dragover.prevent @drop.prevent="handleDrop">
            <input
              ref="fileInput"
              type="file"
              accept=".pdf,.txt,.md,.epub"
              style="display:none"
              @change="handleFileSelect"
            />
            <button class="upload-btn" @click="(fileInput as any)?.click()" :disabled="uploading">
              {{ uploading ? `上传中 ${uploadProgress}%` : '[+] 上传教材' }}
            </button>
            <span class="upload-hint">支持 PDF / TXT / MD / EPUB</span>
          </div>
          <!-- Textbook list -->
          <div v-if="textbooks.length > 0" class="textbook-list">
            <div v-for="tb in textbooks" :key="tb.id" class="textbook-item">
              <span class="tb-icon"></span>
              <span class="tb-name">{{ tb.filename }}</span>
              <span class="tb-size">{{ formatSize(tb.file_size) }}</span>
              <button class="tb-delete" @click="handleDeleteTextbook(tb.id)"></button>
            </div>
          </div>
          <div v-else class="empty-state">暂未上传教材</div>
          <!-- Generate course button -->
          <button
            v-if="textbooks.length > 0 && !hasGeneratedContent"
            class="generate-btn"
            :disabled="generating"
            @click="handleGenerateCourse"
          >
            {{ generating ? '生成中…' : '* 基于教材生成课程' }}
          </button>
          <!-- Regenerate (clears previous generated lessons + progress) -->
          <button
            v-if="textbooks.length > 0 && hasGeneratedContent"
            class="generate-btn regenerate-btn"
            :disabled="generating"
            @click="handleRegenerateCourse"
          >
            {{ generating ? '重新生成中…' : '↻ 重新生成（会清空当前课程结构与进度）' }}
          </button>
        </div>
      </div>

      <!-- Sages -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">知 者</span>
          <span class="section-sublabel">SAGES</span>
        </div>
        <div class="section-line"></div>
        <div v-if="sages.length > 0" class="sages-grid">
          <SageRelationCard
            v-for="sage in sages"
            :key="sage.id"
            :sage="sage"
            @select="handleSelectSage"
          />
        </div>
        <div v-else class="empty-state">暂无关联的知者</div>
      </div>

      <!-- Sessions -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">学 习 会 话</span>
          <span class="section-sublabel">SESSIONS</span>
        </div>
        <div class="section-line"></div>
        <div v-if="sessions.length > 0" class="sessions-list">
          <div
            v-for="session in sessions"
            :key="session.id"
            class="session-item"
            @click="handleContinueSession(session)"
          >
            <div class="session-time">{{ formatSessionTime(session) }}</div>
            <div class="session-info">
              <span class="session-stage">{{ session.relationship_stage || '未知' }}</span>
              <span class="session-messages">{{ session.message_count || 0 }} 条消息</span>
            </div>
            <div class="session-arrow">▸</div>
          </div>
        </div>
        <div v-else class="empty-state">暂无会话记录</div>
      </div>

      <!-- Memory Stats -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">学 习 档 案</span>
          <span class="section-sublabel">MEMORY</span>
        </div>
        <div class="section-line"></div>
        <div class="memory-stats">
          <div class="stat-item">
            <span class="stat-value">{{ memoryStats?.student_state || 0 }}</span>
            <span class="stat-label">Sage 了解</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ memoryStats?.concept_mastered || 0 }}</span>
            <span class="stat-label">已掌握</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ memoryStats?.concept_struggle || 0 }}</span>
            <span class="stat-label">薄弱点</span>
          </div>
        </div>
      </div>

      <!-- Learner Profile -->
      <div v-if="learnerProfile" class="section-group">
        <LearnerProfilePanel
          :dimension-scores="learnerProfile.dimension_scores || {}"
          :strengths="learnerProfile.strengths || []"
          :weaknesses="learnerProfile.weaknesses || []"
          :learning-stats="learnerProfile.learning_stats"
          :last-updated="learnerProfile.last_updated"
        />
      </div>
    </template>
    </div>

    <!-- Sage Selection Modal -->
    <div v-if="showSageSelect" class="modal-overlay" @click.self="showSageSelect = false">
      <div class="modal-content">
        <h3>选择知者</h3>
        <div class="sage-select-grid">
          <div
            v-for="sage in sages"
            :key="sage.id"
            class="sage-select-item"
            @click="confirmSageSelect(sage)"
          >
            <div class="sage-avatar-sm">{{ sage.symbol || '' }}</div>
            <div class="sage-name-sm">{{ sage.name }}</div>
          </div>
        </div>
        <button class="cancel-btn" @click="showSageSelect = false">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { courseApi } from '@/api/course'
import ProgressBar from '@/components/course/ProgressBar.vue'
import SageRelationCard from '@/components/course/SageRelationCard.vue'
import LearnerProfilePanel from '@/components/course/LearnerProfilePanel.vue'
import { DOMAIN_ICONS } from '@/constants/courseLevels'
import { getLevelIndex } from '@/constants/courseLevels'
import { PAGE_BACKGROUNDS } from '@/constants/ui'
import { useToast } from '@/composables/useToast'

const BG_URL = PAGE_BACKGROUNDS.coursePage
const toast = useToast()

const route = useRoute()
const router = useRouter()

// State
const loading = ref(true)
const course = ref<any>(null)
const sages = ref<any[]>([])
const sessions = ref<any[]>([])
const memoryStats = ref<any>(null)
const showSageSelect = ref(false)
const selectedSageForStart = ref<any>(null)
const learnerProfile = ref<any>(null)

// Textbook state (Phase 2C)
const textbooks = ref<any[]>([])
const uploading = ref(false)
const uploadProgress = ref(0)
const generating = ref(false)
const hasGeneratedContent = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

// Computed
const worldId = computed(() => Number(route.params.worldId))
const courseId = computed(() => Number(route.params.courseId))

const domainIcon = computed(() => {
  const domain = course.value?.meta?.domain
  return domain ? DOMAIN_ICONS[domain] || '' : ''
})

const domainLabel = computed(() => {
  const domain = course.value?.meta?.domain
  if (!domain) return ''
  return domain.charAt(0).toUpperCase() + domain.slice(1)
})

const createdAgo = computed(() => {
  if (!course.value?.created_at) return ''
  const date = new Date(course.value.created_at)
  const now = new Date()
  const days = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
  if (days === 0) return '今天创建'
  if (days === 1) return '昨天创建'
  return `${days}天前创建`
})

const progress = computed(() => {
  if (!course.value?.meta) return 0
  const { current_level, target_level } = course.value.meta
  
  const currentIndex = getLevelIndex(current_level || 'none', false)
  const targetIndex = getLevelIndex(target_level || 'understand', true)
  
  if (targetIndex === 0) return 100
  const base = currentIndex / targetIndex
  const bonus = (memoryStats.value?.concept_mastered || 0) * 0.08
  return Math.min(100, (base + bonus) * 100)
})

// Methods
const fetchData = async () => {
  loading.value = true
  try {
    const [courseRes, sagesRes, sessionsRes, statsRes] = await Promise.allSettled([
      courseApi.get(courseId.value),
      courseApi.getSages(courseId.value),
      courseApi.getSessions(courseId.value),
      courseApi.getMemoryFacts(courseId.value, true),
    ])

    if (courseRes.status === 'fulfilled') {
      course.value = courseRes.value
    }
    if (sagesRes.status === 'fulfilled') {
      sages.value = sagesRes.value
    }
    if (sessionsRes.status === 'fulfilled') {
      sessions.value = sessionsRes.value
    }
    if (statsRes.status === 'fulfilled') {
      const stats = statsRes.value
      memoryStats.value = {
        student_state: stats.by_type?.student_state || 0,
        concept_mastered: stats.by_type?.concept_mastered || 0,
        concept_struggle: stats.by_type?.concept_struggle || 0,
        preference: stats.by_type?.preference || 0,
        event: stats.by_type?.event || 0,
        total: stats.total || 0,
      }
    }
  } catch (error) {
    console.error('Failed to fetch course data:', error)
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push(`/home/worlds/${worldId.value}`)
}

const handleStartLearning = () => {
  if (sages.value.length === 0) {
    toast.warning('请先添加知者')
    return
  }
  if (sages.value.length === 1) {
    startLearningWithSage(sages.value[0].id)
  } else {
    selectedSageForStart.value = null
    showSageSelect.value = true
  }
}

const handleSelectSage = (sage: any) => {
  startLearningWithSage(sage.id)
}

const confirmSageSelect = (sage: any) => {
  showSageSelect.value = false
  startLearningWithSage(sage.id)
}

const startLearningWithSage = async (sageId: number) => {
  try {
    const result = await courseApi.start(courseId.value, sageId)
    const sessionId = result.session_id
    router.push({
      path: `/home/worlds/${worldId.value}/courses/${courseId.value}`,
      query: { session_id: sessionId }
    })
  } catch (error) {
    console.error('Failed to start session:', error)
    toast.error('启动学习会话失败')
  }
}

const handleContinueSession = (session: any) => {
  router.push({
    path: `/home/worlds/${worldId.value}/courses/${courseId.value}`,
    query: { session_id: session.id }
  })
}

const formatSessionTime = (session: any) => {
  if (!session.started_at) return '未知时间'
  const date = new Date(session.started_at)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(hours / 24)
  
  const timeStr = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  
  if (days === 0) return `今天 ${timeStr}`
  if (days === 1) return `昨天 ${timeStr}`
  if (days < 7) return `${days}天前 ${timeStr}`
  return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

// ── Textbook handlers (Phase 2C) ──────────────────────────────
const fetchTextbooks = async () => {
  try {
    textbooks.value = await courseApi.listTextbooks(courseId.value)
    // Backend writes to course.meta.generated_lessons (not .lessons —
    // the previous check was always false on page reload, hiding the
    // regenerate button after a refresh).
    const lessons = course.value?.meta?.generated_lessons
    hasGeneratedContent.value = Array.isArray(lessons) && lessons.length > 0
  } catch { /* ignore */ }
}

const handleFileSelect = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  await doUpload(file)
}

const handleDrop = async (e: DragEvent) => {
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  await doUpload(file)
}

const doUpload = async (file: File) => {
  uploading.value = true
  uploadProgress.value = 0
  try {
    await courseApi.uploadTextbook(courseId.value, file, (pct) => {
      uploadProgress.value = pct
    })
    toast.success('教材上传成功')
    await fetchTextbooks()
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

const handleDeleteTextbook = async (id: number) => {
  try {
    await courseApi.deleteTextbook(courseId.value, id)
    textbooks.value = textbooks.value.filter((t: any) => t.id !== id)
    toast.success('已删除')
  } catch {
    toast.error('删除失败')
  }
}

const handleGenerateCourse = async () => {
  generating.value = true
  try {
    const result = await courseApi.generateCourse(courseId.value)
    hasGeneratedContent.value = true
    toast.success(`课程已生成：${result.lessons?.length || 0} 个课时`)
    // Refresh course data to show new lessons
    await fetchData()
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

const handleRegenerateCourse = async () => {
  // Two-step confirm: this is destructive (drops generated lessons +
  // teaching progress + costs another LLM call).
  const ok = window.confirm(
    '确定要重新生成课程吗？\n\n' +
    '这将清空：\n' +
    '  • 当前生成的课程概览、章节列表、概念图\n' +
    '  • 当前章节进度（current_lesson_index、completed_lessons）\n\n' +
    '已上传的教材会保留。'
  )
  if (!ok) return

  generating.value = true
  try {
    await courseApi.clearGeneratedContent(courseId.value)
    const result = await courseApi.generateCourse(courseId.value)
    toast.success(`课程已重新生成：${result.lessons?.length || 0} 个课时`)
    await fetchData()
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '重新生成失败')
  } finally {
    generating.value = false
  }
}

const formatSize = (bytes: number) => {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

// Lifecycle
onMounted(async () => {
  await Promise.all([fetchData(), fetchTextbooks()])
  // Fetch learner profile after main data loads
  try {
    const profile = await courseApi.getLearnerProfile(worldId.value)
    if (profile?.dimension_scores && Object.keys(profile.dimension_scores).length > 0) {
      learnerProfile.value = profile
    }
  } catch { /* profile not yet available */ }
})
</script>

<style scoped>
.course-page {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  overflow-y: auto;
  padding-bottom: 48px;
}

.scene-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.5;
  z-index: -2;
}

.scene-overlay {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(10,10,30,0.15) 0%, transparent 60%),
    radial-gradient(ellipse at 30% 55%, rgba(255,215,0,0.05) 0%, transparent 55%),
    linear-gradient(to bottom, rgba(10,10,30,0.25) 0%, rgba(0,0,0,0.45) 100%);
  z-index: -1;
}

.char-header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 32px;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.back-btn:hover {
  color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.header-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 18px;
  color: #ffd700;
  letter-spacing: 6px;
  margin: 0;
}

.char-content {
  position: relative;
  z-index: 1;
  max-width: 900px;
  margin: 0 auto;
  padding: 32px;
}

.section-group {
  margin-bottom: 48px;
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
}

.section-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 18px;
  color: #ffd700;
  letter-spacing: 4px;
}

.section-line {
  width: 100%;
  height: 1px;
  background: linear-gradient(to right, rgba(255, 215, 0, 0.3), transparent);
  margin-bottom: 20px;
}

.loading, .error-state, .empty-state {
  text-align: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.4);
  font-family: "Noto Sans SC", sans-serif;
  letter-spacing: 2px;
}

/* Course Overview */
.course-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 20px 0;
}

.course-icon {
  font-size: 56px;
  flex-shrink: 0;
}

.course-title-area {
  flex: 1;
}

.course-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 22px;
  color: #ffd700;
  letter-spacing: 2px;
  margin: 0 0 8px;
}

.course-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 12px;
}

.course-meta {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  font-family: "Noto Sans SC", sans-serif;
}

.separator {
  margin: 0 8px;
  color: rgba(255, 215, 0, 0.3);
}

.start-btn {
  padding: 12px 28px;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  border: none;
  border-radius: 24px;
  color: #1a1a2e;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(251, 191, 36, 0.4);
}

/* Sages Grid */
.sages-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.sages-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s ease;
}

.session-item:last-child {
  border-bottom: none;
}

.session-item:hover {
  background: rgba(255, 215, 0, 0.05);
  padding-left: 28px;
}

.session-time {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  min-width: 100px;
  font-family: "Noto Sans SC", sans-serif;
}

.session-info {
  flex: 1;
  display: flex;
  gap: 16px;
  font-size: 13px;
}

.session-stage {
  color: #a78bfa;
  font-family: "Noto Sans SC", sans-serif;
}

.session-messages {
  color: rgba(255, 255, 255, 0.4);
  font-family: "Noto Sans SC", sans-serif;
}

.session-arrow {
  color: rgba(255, 215, 0, 0.4);
}

/* Memory Stats */
.memory-section .section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.memory-section .section-header .section-title {
  margin: 0;
}

.view-archive-btn {
  padding: 6px 14px;
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.25);
  border-radius: 6px;
  color: #ffd700;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.view-archive-btn:hover {
  background: rgba(255, 215, 0, 0.15);
  border-color: rgba(255, 215, 0, 0.4);
}

.memory-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 20px 16px;
  border-right: 1px solid rgba(255, 215, 0, 0.1);
}

.stat-item:last-child {
  border-right: none;
}

.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #ffd700;
  font-family: "Noto Sans SC", sans-serif;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 6px;
  font-family: "Noto Sans SC", sans-serif;
  letter-spacing: 1px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: rgba(12, 12, 30, 0.98);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 16px;
  padding: 28px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-content h3 {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 18px;
  color: #ffd700;
  text-align: center;
  margin: 0 0 20px;
  letter-spacing: 3px;
}

.sage-select-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.sage-select-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sage-select-item:hover {
  background: rgba(255, 215, 0, 0.08);
  border-color: rgba(255, 215, 0, 0.4);
}

.sage-avatar-sm {
  font-size: 36px;
}

.sage-name-sm {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

.cancel-btn {
  width: 100%;
  padding: 12px;
  background: transparent;
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  color: rgba(255, 215, 0, 0.6);
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cancel-btn:hover {
  background: rgba(255, 215, 0, 0.1);
  border-color: rgba(255, 215, 0, 0.4);
  color: #ffd700;
}

/* Textbook area (Phase 2C) */
.textbook-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.textbook-upload {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.upload-btn {
  padding: 8px 18px;
  background: rgba(96, 165, 250, 0.12);
  border: 1px solid rgba(96, 165, 250, 0.3);
  border-radius: 8px;
  color: #93c5fd;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.upload-btn:hover:not(:disabled) {
  background: rgba(96, 165, 250, 0.2);
  border-color: rgba(96, 165, 250, 0.5);
}
.upload-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.upload-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
}

.textbook-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.textbook-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 215, 0, 0.08);
  border-radius: 8px;
  font-size: 13px;
}
.tb-icon { font-size: 16px; flex-shrink: 0; }
.tb-name { flex: 1; color: rgba(255, 255, 255, 0.7); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tb-size { font-size: 11px; color: rgba(255, 255, 255, 0.3); }
.tb-delete {
  background: none; border: none; color: rgba(239, 68, 68, 0.5);
  cursor: pointer; font-size: 14px; padding: 2px 6px;
  border-radius: 4px; transition: all 0.2s ease;
}
.tb-delete:hover { color: #ef4444; background: rgba(239, 68, 68, 0.1); }

.generate-btn {
  margin-top: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(96, 165, 250, 0.2));
  border: 1px solid rgba(168, 85, 247, 0.4);
  border-radius: 10px;
  color: #c4b5fd;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.generate-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.3), rgba(96, 165, 250, 0.3));
  border-color: rgba(168, 85, 247, 0.6);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(168, 85, 247, 0.2);
}
.generate-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
