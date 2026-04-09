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
            开始学习 ▶
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
            <div class="sage-avatar-sm">{{ sage.symbol || '☉' }}</div>
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
import client from '@/api/client'
import ProgressBar from '@/components/course/ProgressBar.vue'
import MotivationBanner from '@/components/course/MotivationBanner.vue'
import SageRelationCard from '@/components/course/SageRelationCard.vue'
import { DOMAIN_ICONS } from '@/constants/courseLevels'
import { getLevelIndex } from '@/constants/courseLevels'
import charBg from '@/assets/char-bg.jpg'

const BG_URL = charBg

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

// Computed
const worldId = computed(() => Number(route.params.worldId))
const courseId = computed(() => Number(route.params.courseId))

const domainIcon = computed(() => {
  const domain = course.value?.meta?.domain
  return domain ? DOMAIN_ICONS[domain] || '📚' : '📚'
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
  console.log('[CoursePage DEBUG] fetchData called, courseId:', courseId.value)
  loading.value = true
  try {
    const [courseRes, sagesRes, sessionsRes, statsRes] = await Promise.allSettled([
      client.get(`/courses/${courseId.value}`),
      client.get(`/courses/${courseId.value}/sages`),
      client.get(`/courses/${courseId.value}/sessions`),
      client.get(`/courses/${courseId.value}/memory-facts?stats_only=true`),
    ])

    console.log('[CoursePage DEBUG] courseRes:', courseRes.status, courseRes.reason?.message || 'ok')
    console.log('[CoursePage DEBUG] sagesRes:', sagesRes.status, sagesRes.reason?.message || 'ok')
    console.log('[CoursePage DEBUG] sessionsRes:', sessionsRes.status, sessionsRes.reason?.message || 'ok')
    console.log('[CoursePage DEBUG] statsRes:', statsRes.status, statsRes.reason?.message || 'ok')

    if (courseRes.status === 'fulfilled') {
      course.value = courseRes.value.data
      console.log('[CoursePage DEBUG] course.value set:', course.value)
    }
    if (sagesRes.status === 'fulfilled') {
      sages.value = sagesRes.value.data
    }
    if (sessionsRes.status === 'fulfilled') {
      sessions.value = sessionsRes.value.data
    }
    if (statsRes.status === 'fulfilled') {
      const stats = statsRes.value.data
      // Transform stats by_type to flat object
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
    alert('请先添加知者')
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
    const res = await client.post(`/courses/${courseId.value}/start`, {
      sage_id: sageId,
    })
    const sessionId = res.data.session_id
    router.push({
      path: `/home/worlds/${worldId.value}/courses/${courseId.value}`,
      query: { session_id: sessionId }
    })
  } catch (error) {
    console.error('Failed to start session:', error)
    alert('启动学习会话失败')
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

// Lifecycle
onMounted(() => {
  fetchData()
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
</style>
