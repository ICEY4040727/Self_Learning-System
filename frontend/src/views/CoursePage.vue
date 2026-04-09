<template>
  <div class="course-page">
    <!-- Header -->
    <div class="page-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1 class="page-title">课程主页</h1>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">加载中…</div>

    <!-- Content -->
    <div v-else-if="course" class="course-content">
      <!-- Course Overview -->
      <section class="course-overview card">
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
      </section>

      <!-- Motivation Banner -->
      <MotivationBanner
        v-if="course.meta?.motivation"
        :motivation="course.meta.motivation"
        :motivation-detail="course.meta.motivation_detail"
      />

      <!-- Progress Bar -->
      <section class="progress-section card">
        <h3 class="section-title">学习进度</h3>
        <ProgressBar
          :current-level="course.meta?.current_level || 'none'"
          :target-level="course.meta?.target_level || 'understand'"
          :progress="progress"
          :concept-mastered-count="memoryStats?.concept_mastered"
        />
      </section>

      <!-- Sage Relations -->
      <section class="sages-section card">
        <h3 class="section-title">知者</h3>
        <div v-if="sages.length > 0" class="sages-grid">
          <SageRelationCard
            v-for="sage in sages"
            :key="sage.id"
            :sage="sage"
            @select="handleSelectSage"
          />
        </div>
        <div v-else class="empty-state">暂无关联的知者</div>
      </section>

      <!-- Session History -->
      <section class="sessions-section card">
        <h3 class="section-title">历史会话</h3>
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
      </section>

      <!-- Memory Stats -->
      <section class="memory-section card">
        <div class="section-header">
          <h3 class="section-title">学习档案</h3>
          <button class="view-archive-btn" @click="showMemoryDrawer = true">
            查看档案 📋
          </button>
        </div>
        <div class="memory-stats">
          <div class="stat-item">
            <span class="stat-value">{{ memoryStats?.student_state || 0 }}</span>
            <span class="stat-label">Sage 对我的了解</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ memoryStats?.concept_mastered || 0 }}</span>
            <span class="stat-label">已掌握概念</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ memoryStats?.concept_struggle || 0 }}</span>
            <span class="stat-label">薄弱概念</span>
          </div>
        </div>
      </section>
    </div>

    <!-- Error -->
    <div v-else class="error-state">
      <p>无法加载课程信息</p>
      <button @click="fetchData">重试</button>
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
  loading.value = true
  try {
    const [courseRes, sagesRes, sessionsRes, statsRes] = await Promise.allSettled([
      client.get(`/courses/${courseId.value}`),
      client.get(`/courses/${courseId.value}/sages`),
      client.get(`/courses/${courseId.value}/sessions`),
      client.get(`/courses/${courseId.value}/memory-facts?stats_only=true`),
    ])

    if (courseRes.status === 'fulfilled') {
      course.value = courseRes.value.data
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
  min-height: 100vh;
  padding: 16px;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.back-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
}

.loading, .error-state, .empty-state {
  text-align: center;
  padding: 40px;
  color: rgba(255, 255, 255, 0.6);
}

.course-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 800px;
  margin: 0 auto;
}

.card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 12px;
}

/* Course Overview */
.course-overview .course-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.course-icon {
  font-size: 48px;
  flex-shrink: 0;
}

.course-title-area {
  flex: 1;
}

.course-name {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}

.course-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin: 4px 0 8px;
}

.course-meta {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.separator {
  margin: 0 6px;
}

.start-btn {
  padding: 12px 24px;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  border: none;
  border-radius: 24px;
  color: #1a1a2e;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.start-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 20px rgba(251, 191, 36, 0.4);
}

/* Sages Grid */
.sages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
}

/* Sessions List */
.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.session-time {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  min-width: 100px;
}

.session-info {
  flex: 1;
  display: flex;
  gap: 12px;
  font-size: 13px;
}

.session-stage {
  color: #a78bfa;
}

.session-messages {
  color: rgba(255, 255, 255, 0.5);
}

.session-arrow {
  color: rgba(255, 255, 255, 0.3);
}

/* Memory Stats */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header .section-title {
  margin-bottom: 0;
}

.view-archive-btn {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.view-archive-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.memory-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #a78bfa;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 4px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1a2e;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  padding: 24px;
  max-width: 400px;
  width: 90%;
}

.modal-content h3 {
  text-align: center;
  margin-bottom: 20px;
}

.sage-select-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.sage-select-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.sage-select-item:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: #fbbf24;
}

.sage-avatar-sm {
  font-size: 32px;
}

.sage-name-sm {
  font-size: 14px;
}

.cancel-btn {
  width: 100%;
  padding: 12px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
}

.cancel-btn:hover {
  background: rgba(255, 255, 255, 0.05);
}
</style>
