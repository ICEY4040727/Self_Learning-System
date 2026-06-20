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
              :accept="TEXTBOOK_ACCEPT"
              style="display:none"
              @change="handleFileSelect"
            />
            <button class="upload-btn" @click="(fileInput as any)?.click()" :disabled="uploading">
              {{ uploading ? `上传 / 解析中 ${uploadProgress}%` : '[+] 上传教材' }}
            </button>
            <span class="upload-hint">{{ TEXTBOOK_UPLOAD_HINT }}</span>
          </div>
          <!-- Textbook list -->
          <div v-if="textbooks.length > 0" class="textbook-list">
            <div v-for="tb in textbooks" :key="tb.id" class="textbook-item">
              <span class="tb-icon"></span>
              <div class="tb-info">
                <span class="tb-name">{{ tb.filename }}</span>
                <div class="tb-meta">
                  <span v-if="tb.page_count" class="meta-tag">{{ tb.page_count }} 页</span>
                  <span class="meta-tag">{{ formatSize(tb.file_size) }}</span>
                  <span v-if="tb.is_usable" class="meta-tag ok-tag">可用于生成</span>
                  <span v-else-if="tb.status === 'error'" class="meta-tag error-tag">解析失败</span>
                  <span v-else class="meta-tag">处理中</span>
                </div>
                <div v-if="tb.error_message" class="tb-error">{{ tb.error_message }}</div>
              </div>
              <button class="tb-delete" @click="handleDeleteTextbook(tb.id)"></button>
            </div>
          </div>
          <div v-else class="empty-state">暂未上传教材</div>
          <!-- Generate / Regenerate course button -->
          <button
            v-if="textbooks.length > 0"
            class="generate-btn"
            :class="{ 'regenerate-btn': hasGeneratedContent }"
            :disabled="generating || !hasUsableTextbooks"
            @click="hasGeneratedContent ? handleRegenerateCourse() : handleGenerateCourse()"
          >
            <template v-if="generating">
              {{ hasGeneratedContent ? '重新生成中…' : '生成中…' }}
            </template>
            <template v-else-if="!hasUsableTextbooks">
              * 请先上传可用教材
            </template>
            <template v-else>
              {{ hasGeneratedContent ? '* 重新基于教材生成课程' : '* 基于教材生成课程' }}
            </template>
          </button>
        </div>
      </div>

      <!-- Lesson List (Phase 3 Step 3: from LessonPlan table) -->
      <div v-if="lessons.length > 0" class="section-group">
        <div class="section-header">
          <span class="section-label">课 程 章 节</span>
          <span class="section-sublabel">LESSONS ({{ lessons.length }})</span>
        </div>
        <div class="section-line"></div>
        <div class="lesson-list">
          <div
            v-for="(lesson, idx) in lessons"
            :key="lesson.id"
            class="lesson-item"
            :class="{
              'lesson-current': lessonProgress?.current_index === idx,
              'lesson-completed': (lessonProgress?.lessons?.[idx]?._status === 'completed'),
            }"
            @click="handleLessonClick(idx)"
          >
            <div class="lesson-marker">
              <span v-if="lessonProgress?.lessons?.[idx]?._status === 'completed'" class="marker-done">✓</span>
              <span v-else-if="lessonProgress?.current_index === idx" class="marker-current">▶</span>
              <span v-else class="marker-pending">{{ idx + 1 }}</span>
            </div>
            <div class="lesson-info">
              <div class="lesson-title">{{ lesson.title }}</div>
              <div v-if="lesson.description" class="lesson-desc">{{ lesson.description }}</div>
              <div v-if="lesson.concepts?.length" class="lesson-concepts">
                <span v-for="c in lesson.concepts.slice(0, 4)" :key="c" class="concept-tag">{{ c }}</span>
              </div>
            </div>
            <div class="lesson-arrow">▸</div>
          </div>
        </div>
        <!-- Lesson progress bar -->
        <div v-if="lessonProgress" class="lesson-progress-bar">
          <div class="lp-fill" :style="{ width: lessonProgress.progress_pct + '%' }"></div>
          <span class="lp-text">{{ lessonProgress.completed_lessons }}/{{ lessonProgress.total_lessons }} 已完成</span>
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
    <div v-if="showSageSelect" class="modal-overlay" @click.self="closeSageSelect">
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
        <button class="cancel-btn" @click="closeSageSelect">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { courseApi, type CourseTextbook } from '@/courses/api/course'
import ProgressBar from '@/courses/components/course/ProgressBar.vue'
import SageRelationCard from '@/courses/components/course/SageRelationCard.vue'
import LearnerProfilePanel from '@/courses/components/course/LearnerProfilePanel.vue'
import { DOMAIN_ICONS } from '@/courses/constants/courseLevels'
import { getLevelIndex } from '@/courses/constants/courseLevels'
import { PAGE_BACKGROUNDS } from '@/shared/constants/ui'
import { TEXTBOOK_ACCEPT, TEXTBOOK_UPLOAD_HINT } from '@/courses/constants/textbooks'
import { useToast } from '@/shared/composables/useToast'

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
const pendingLessonIndex = ref<number | null>(null)
const learnerProfile = ref<any>(null)

// Textbook state (Phase 2C)
const textbooks = ref<CourseTextbook[]>([])
const uploading = ref(false)
const uploadProgress = ref(0)
const generating = ref(false)
const hasGeneratedContent = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

// Lesson state (Phase 3 Step 3)
const lessons = ref<any[]>([])
const lessonProgress = ref<any>(null)

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

const hasUsableTextbooks = computed(() => textbooks.value.some((tb) => tb.is_usable))

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
    pendingLessonIndex.value = null
    showSageSelect.value = true
  }
}

const handleSelectSage = (sage: any) => {
  startLearningWithSage(sage.id)
}

const closeSageSelect = () => {
  showSageSelect.value = false
  pendingLessonIndex.value = null
}

const confirmSageSelect = (sage: any) => {
  const lessonIndex = pendingLessonIndex.value
  closeSageSelect()
  startLearningWithSage(sage.id, lessonIndex ?? undefined)
}

const startLearningWithSage = async (_sageId: number, lessonIndex?: number) => {
  try {
    // Navigate to Learning page - pass sageId so backend knows which sage to use
    router.push({
      path: `/learning/${courseId.value}`,
      query: {
        worldId: String(worldId.value),
        sageId: String(_sageId),
        ...(lessonIndex !== undefined ? { lesson: String(lessonIndex) } : {}),
      },
    })
  } catch (error) {
    console.error('Failed to start session:', error)
    toast.error('启动学习会话失败')
  }
}

const handleContinueSession = (_session: any) => {
  router.push({
    path: `/learning/${courseId.value}`,
    query: {
      worldId: String(worldId.value),
      // 传 session 的 sage_id，后端可据此匹配已有 session
      ...(_session.sage_character_id ? { sageId: String(_session.sage_character_id) } : {}),
    },
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

// ── Lesson handlers (Phase 3 Step 3) ─────────────────────────
const fetchLessons = async () => {
  try {
    const [lessonsRes, progressRes] = await Promise.allSettled([
      courseApi.listLessons(courseId.value),
      courseApi.getProgress(courseId.value),
    ])
    if (lessonsRes.status === 'fulfilled') {
      lessons.value = lessonsRes.value.lessons || []
      hasGeneratedContent.value = lessons.value.length > 0
    }
    if (progressRes.status === 'fulfilled') {
      lessonProgress.value = progressRes.value
    }
  } catch { /* ignore */ }
}

const handleLessonClick = async (idx: number) => {
  if (sages.value.length === 0) {
    toast.warning('请先添加知者')
    return
  }
  if (sages.value.length === 1) {
    startLearningWithSage(sages.value[0].id, idx)
    return
  }
  pendingLessonIndex.value = idx
  showSageSelect.value = true
}

// ── Textbook handlers (Phase 2C) ──────────────────────────────
const fetchTextbooks = async () => {
  try {
    textbooks.value = await courseApi.listTextbooks(courseId.value)
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
    const item = await courseApi.uploadTextbook(courseId.value, file, (pct) => {
      uploadProgress.value = pct
    })
    await fetchTextbooks()
    if (item.is_usable) {
      toast.success('教材上传并解析成功')
    } else {
      toast.error(`教材已上传，但解析失败：${item.error_message || '请检查文件内容'}`)
    }
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
  if (!hasUsableTextbooks.value) {
    toast.warning('请先上传并解析成功的教材')
    return
  }
  generating.value = true
  try {
    const result = await courseApi.generateCourse(courseId.value)
    hasGeneratedContent.value = true
    toast.success(`课程已生成：${result.lessons?.length || 0} 个课时`)
    // Refresh course data to show new lessons
    await Promise.all([fetchData(), fetchLessons()])
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

const handleRegenerateCourse = async () => {
  if (!hasUsableTextbooks.value) {
    toast.warning('请先上传并解析成功的教材')
    return
  }
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
    await Promise.all([fetchData(), fetchLessons()])
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '重新生成失败')
  } finally {
    generating.value = false
  }
}

const formatSize = (bytes: number | null) => {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

// Lifecycle
onMounted(async () => {
  await Promise.all([fetchData(), fetchTextbooks(), fetchLessons()])
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
.tb-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.tb-name { color: rgba(255, 255, 255, 0.7); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tb-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tb-size { font-size: 11px; color: rgba(255, 255, 255, 0.3); }
.meta-tag {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}
.meta-tag.ok-tag {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}
.meta-tag.error-tag {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}
.tb-error {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(239, 68, 68, 0.75);
  line-height: 1.4;
}
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

.generate-btn.regenerate-btn {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(168, 85, 247, 0.15));
  border-color: rgba(251, 191, 36, 0.4);
  color: #fbbf24;
}
.generate-btn.regenerate-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.25), rgba(168, 85, 247, 0.25));
  border-color: rgba(251, 191, 36, 0.6);
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.2);
}

/* Lesson list (Phase 3 Step 3) */
.lesson-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.lesson-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 215, 0, 0.08);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.lesson-item:hover {
  background: rgba(255, 215, 0, 0.06);
  border-color: rgba(255, 215, 0, 0.2);
  padding-left: 24px;
}
.lesson-item.lesson-current {
  border-color: rgba(255, 215, 0, 0.35);
  background: rgba(255, 215, 0, 0.08);
}
.lesson-item.lesson-completed {
  opacity: 0.65;
}
.lesson-item.lesson-completed .lesson-title {
  text-decoration: line-through;
  color: rgba(255, 255, 255, 0.4);
}

.lesson-marker {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
}
.marker-done {
  color: #4ade80;
  font-size: 16px;
}
.marker-current {
  color: #ffd700;
  font-size: 12px;
  background: rgba(255, 215, 0, 0.15);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.marker-pending {
  color: rgba(255, 255, 255, 0.3);
}

.lesson-info {
  flex: 1;
  min-width: 0;
}
.lesson-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 2px;
}
.lesson-desc {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lesson-concepts {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.concept-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(96, 165, 250, 0.1);
  border: 1px solid rgba(96, 165, 250, 0.2);
  border-radius: 10px;
  color: #93c5fd;
}
.lesson-arrow {
  color: rgba(255, 215, 0, 0.3);
  font-size: 14px;
}

/* Lesson progress bar */
.lesson-progress-bar {
  margin-top: 12px;
  position: relative;
  height: 24px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  overflow: hidden;
}
.lp-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(255, 215, 0, 0.3), rgba(255, 215, 0, 0.6));
  border-radius: 12px;
  transition: width 0.4s ease;
}
.lp-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  font-family: "Noto Sans SC", sans-serif;
  letter-spacing: 1px;
}
</style>

