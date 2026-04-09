<template>
  <div class="archive-page">
    <!-- Background -->
    <div class="bg-image" :style="{ backgroundImage: `url(${BG_URL})` }"></div>
    <div class="bg-gradient"></div>
    <ParticleBackground :count="16" :gold-ratio="0.5" />

    <!-- Header -->
    <div class="archive-header font-ui">
      <button class="galgame-hud-btn" @click="router.push('/home')">
        <span>←</span> 返回
      </button>
      <span class="header-title">档 案 管 理</span>
      <div style="width:80px;"></div>
    </div>

    <!-- Content -->
    <div class="archive-content galgame-scrollbar">
      <!-- World selector -->
      <div class="world-selector font-ui">
        <span class="selector-label">当前世界：</span>
        <div class="world-dropdown" @click="showWorldDropdown = !showWorldDropdown">
          <span>{{ selectedWorldName }} ▾</span>
        </div>
      </div>

      <div class="grid-layout">
        <!-- Emotion Trajectory -->
        <div class="panel full-width">
          <div class="panel-header">
            <div class="header-left">
              <span class="icon">📈</span>
              <span class="panel-title">情感轨迹</span>
            </div>
            <span class="header-sub font-ui">{{ selectedWorldName }} · {{ selectedCourseName }}</span>
          </div>
          <div v-if="emotionData.length === 0" class="empty-placeholder">
            暂无情感记录
          </div>
          <EmotionTrajectory v-else :course-id="selectedSessionId || undefined" />
        </div>

        <!-- Emotion Distribution -->
        <div class="panel">
          <div class="panel-header">
            <div class="header-left">
              <span class="panel-title">情感分布</span>
            </div>
          </div>
          <div v-if="emotionData.length === 0" class="empty-placeholder">
            暂无数据
          </div>
          <div v-else class="pie-chart-container">
            <div class="pie-chart">
              <svg viewBox="0 0 100 100">
                <circle
                  v-for="(segment, i) in pieSegments"
                  :key="i"
                  cx="50"
                  cy="50"
                  r="30"
                  fill="none"
                  :stroke="segment.color"
                  stroke-width="20"
                  :stroke-dasharray="segment.dashArray"
                  :stroke-dashoffset="segment.offset"
                  transform="rotate(-90 50 50)"
                />
              </svg>
            </div>
            <div class="pie-legend">
              <div v-for="item in emotionPieData" :key="item.type" class="legend-row">
                <span class="legend-dot" :style="{ background: item.color }"></span>
                <span class="legend-name">{{ item.type }}</span>
                <span class="legend-value" :style="{ color: item.color }">{{ item.percent }}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Relationship Status -->
        <div class="panel">
          <div class="panel-header">
            <div class="header-left">
              <span class="panel-title">关系状态</span>
            </div>
          </div>
          <div class="relationship-content">
            <div class="current-stage">
              <span class="stage-label font-ui">当前阶段</span>
              <span class="stage-name font-ui">{{ currentStage }}</span>
            </div>
            <div v-for="(value, dim) in relationshipDimensions" :key="dim" class="dimension-item">
              <div class="dimension-header">
                <span class="dimension-name">{{ dimensionLabels[dim] || dim }}</span>
                <span class="dimension-value">{{ Math.round(value * 100) }}%</span>
              </div>
              <div class="dimension-bar">
                <div class="dimension-fill" :style="{ width: `${value * 100}%` }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Concept Mastery -->
        <div class="panel full-width">
          <div class="panel-header">
            <div class="header-left">
              <span class="icon">📚</span>
              <span class="panel-title">学习进度</span>
            </div>
            <span class="header-sub font-ui">{{ selectedCourseName }}</span>
          </div>
          <div v-if="progressList.length === 0" class="empty-placeholder">
            暂无进度数据
          </div>
          <div v-else class="progress-list">
            <div v-for="item in progressList" :key="item.id" class="progress-row">
              <div class="progress-name font-ui">{{ item.topic }}</div>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: `${item.mastery_level * 100}%`, background: getProgressColor(item.mastery_level) }"
                ></div>
              </div>
              <div class="progress-value font-ui" :style="{ color: getProgressColor(item.mastery_level) }">
                {{ Math.round(item.mastery_level * 100) }}%
              </div>
              <div class="progress-review font-ui">复习:{{ item.next_review }}</div>
            </div>
          </div>
        </div>

        <!-- Learning Diary -->
        <div class="panel full-width">
          <div class="panel-header">
            <div class="header-left">
              <span class="icon">✏️</span>
              <span class="panel-title">学习日记</span>
            </div>
            <button class="galgame-hud-btn diary-btn" @click="diaryOpen = !diaryOpen">
              <span>✏️</span> 写日记
            </button>
          </div>

          <Transition name="diary-slide">
            <div v-if="diaryOpen" class="diary-form">
              <textarea
                v-model="diaryContent"
                class="galgame-input w-full p-3 font-dialogue"
                placeholder="记下今天的学习感悟……"
                rows="3"
              ></textarea>
              <div class="form-actions">
                <button class="galgame-send-btn" @click="submitDiary">保存</button>
              </div>
            </div>
          </Transition>

          <div v-if="diaries.length === 0" class="empty-placeholder">
            暂无日记
          </div>
          <div v-else class="diary-list">
            <div v-for="entry in diaries" :key="entry.id" class="diary-entry">
              <div class="entry-header font-ui">
                <span class="entry-icon">📅</span>
                <span class="entry-date">{{ formatDate(entry.date) }}</span>
                <span class="entry-emotion">{{ entry.emotion }}</span>
              </div>
              <p class="entry-content font-dialogue">{{ entry.content }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '@/api/client'
import { parseApiError } from '@/utils/error'
import EmotionTrajectory from '@/components/EmotionTrajectory.vue'
import ParticleBackground from '@/components/ParticleBackground.vue'

const router = useRouter()

const BG_URL = 'https://images.unsplash.com/photo-1675371708731-50d9c04eb530?w=1920&q=80'

interface Diary { id: number; course_id: number; date: string; content: string; reflection?: string; emotion?: string }
interface Progress { id: number; topic: string; mastery_level: number; next_review?: string }
interface Session { id: number; started_at: string; course_name: string }
interface Course { id: number; name: string }
interface World { id: number; name: string }

const diaries = ref<Diary[]>([])
const progressList = ref<Progress[]>([])
const sessions = ref<Session[]>([])
const courses = ref<Course[]>([])
const worlds = ref<World[]>([])
const emotionData = ref<any[]>([])
const selectedSessionId = ref<number | null>(null)
const selectedWorldId = ref<number | null>(null)

const diaryOpen = ref(false)
const diaryContent = ref('')
const showWorldDropdown = ref(false)


const selectedWorldName = computed(() => worlds.value.find(w => w.id === selectedWorldId.value)?.name || '雅典学院')
const selectedCourseName = computed(() => '哲学导论')

const currentStage = ref('相知')
const relationshipDimensions = ref({ trust: 0.75, familiarity: 0.6, respect: 0.8, comfort: 0.65 })
const dimensionLabels: Record<string, string> = { trust: '信任', familiarity: '默契', respect: '敬意', comfort: '舒适' }

const emotionCounts = computed(() => {
  const counts: Record<string, number> = {}
  emotionData.value.forEach(d => {
    counts[d.emotion_type] = (counts[d.emotion_type] || 0) + 1
  })
  return counts
})

const EMOTION_COLORS: Record<string, string> = {
  '好奇': '#60a5fa',
  '兴奋': '#ffd700',
  '困惑': '#f97316',
  '满足': '#4adf6a',
  '中性': '#94a3b8',
}

const emotionPieData = computed(() => {
  const total = emotionData.value.length
  if (total === 0) return []
  let cumulative = 0
  return Object.entries(emotionCounts.value).map(([type, count]) => {
    const percent = Math.round((count / total) * 100)
    const item = { type, count, percent, color: EMOTION_COLORS[type] || '#94a3b8', cumulative }
    cumulative += percent
    return item
  })
})

const pieSegments = computed(() => {
  const circumference = 2 * Math.PI * 30
  return emotionPieData.value.map(item => ({
    color: item.color,
    dashArray: `${(item.percent / 100) * circumference} ${circumference}`,
    offset: 0
  }))
})

const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString('zh-CN')

const getProgressColor = (level: number) => {
  if (level >= 0.65) return '#4adf6a'
  if (level >= 0.4) return '#ffd700'
  return '#f97316'
}

const fetchDiaries = async () => {
  try {
    const { data } = await client.get('learning_diary', )
    diaries.value = data
  } catch {}
}

const fetchProgress = async () => {
  try {
    const { data } = await client.get('progress', )
    progressList.value = data
  } catch {}
}

const fetchSessions = async () => {
  try {
    const { data } = await client.get('sessions', )
    sessions.value = data
    if (data.length > 0) {
      selectedSessionId.value = data[0].id
      await fetchEmotionTrajectory()
    }
  } catch {}
}

const fetchEmotionTrajectory = async () => {
  if (!selectedSessionId.value) return
  try {
    const { data } = await client.get(`/sessions/${selectedSessionId.value}/emotion_trajectory`)
    emotionData.value = data
  } catch {}
}

const fetchCourses = async () => {
  try {
    const { data } = await client.get('courses')
    courses.value = data
  } catch {}
}

const fetchWorlds = async () => {
  try {
    const { data } = await client.get('worlds', )
    worlds.value = data
    if (data.length > 0) selectedWorldId.value = data[0].id
  } catch {}
}

const submitDiary = async () => {
  if (!diaryContent.value.trim()) return
  try {
    await client.post('learning_diary', {
      content: diaryContent.value.trim(),
      date: new Date().toISOString(),
    }, )
    diaryContent.value = ''
    diaryOpen.value = false
    await fetchDiaries()
  } catch (e) {
    console.error(parseApiError(e))
  }
}

onMounted(async () => {
  await Promise.all([fetchDiaries(), fetchProgress(), fetchSessions(), fetchCourses(), fetchWorlds()])
})
</script>

<style scoped>
.archive-page {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  overflow-y: auto;
  padding-bottom: 48px;
}

.bg-image {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.08;
  z-index: -2;
}

.bg-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(10,10,30,0.95) 0%, rgba(10,10,30,0.98) 100%);
  z-index: -1;
}

.archive-header {
  position: relative;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255,215,0,0.1);
  z-index: 10;
}

.archive-header button {
  font-size: 13px;
  padding: 6px 14px;
}

.header-title {
  color: #ffd700;
  font-size: 16px;
  letter-spacing: 4px;
}

.archive-content {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  padding-top: 68px;
  padding-bottom: 24px;
  padding-left: 24px;
  padding-right: 24px;
}

.world-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  font-size: 13px;
}

.selector-label {
  color: rgba(255,255,255,0.35);
}

.world-dropdown {
  background: rgba(255,215,0,0.1);
  border: 1px solid rgba(255,215,0,0.3);
  border-radius: 6px;
  padding: 4px 12px;
  color: #ffd700;
  cursor: pointer;
}

.grid-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.panel {
  background: rgba(8, 8, 28, 0.8);
  border: 1px solid rgba(255,215,0,0.12);
  border-radius: 14px;
  padding: 18px 20px;
}

.panel.full-width {
  grid-column: 1 / -1;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon {
  font-size: 16px;
}

.panel-title {
  color: #ffd700;
  font-size: 14px;
  letter-spacing: 2px;
}

.header-sub {
  color: rgba(255,255,255,0.3);
  font-size: 11px;
}

.empty-placeholder {
  color: rgba(255,255,255,0.3);
  text-align: center;
  padding: 40px 0;
  font-size: 13px;
}

/* Pie Chart */
.pie-chart-container {
  display: flex;
  align-items: center;
  gap: 24px;
}

.pie-chart {
  width: 140px;
  height: 140px;
  flex-shrink: 0;
}

.pie-chart svg {
  width: 100%;
  height: 100%;
}

.pie-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-name {
  color: rgba(255,255,255,0.6);
}

.legend-value {
  margin-left: auto;
  font-weight: 600;
}

/* Relationship */
.relationship-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.current-stage {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.stage-label {
  color: rgba(255,255,255,0.5);
  font-size: 12px;
}

.stage-name {
  color: #ffd700;
  font-size: 14px;
  letter-spacing: 2px;
}

.dimension-item {
  margin-bottom: 12px;
}

.dimension-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.dimension-name {
  color: rgba(255,255,255,0.45);
  font-size: 12px;
}

.dimension-value {
  color: rgba(255,255,255,0.35);
  font-size: 12px;
}

.dimension-bar {
  height: 5px;
  border-radius: 3px;
  background: rgba(255,255,255,0.08);
  overflow: hidden;
}

.dimension-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #a78bfa);
  border-radius: 3px;
  transition: width 0.8s ease;
}

/* Progress */
.progress-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.progress-name {
  width: 120px;
  color: rgba(255,255,255,0.65);
  font-size: 13px;
  flex-shrink: 0;
}

.progress-bar {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: rgba(255,255,255,0.08);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s ease;
}

.progress-value {
  width: 40px;
  text-align: right;
  font-size: 12px;
  flex-shrink: 0;
}

.progress-review {
  width: 60px;
  color: rgba(255,255,255,0.3);
  font-size: 11px;
  flex-shrink: 0;
}

/* Diary */
.diary-btn {
  font-size: 12px;
  padding: 5px 12px;
}

.diary-form {
  margin-bottom: 16px;
}

.diary-form textarea {
  font-size: 15px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.diary-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.diary-entry {
  padding: 12px 14px;
  background: rgba(255,255,255,0.03);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.06);
}

.entry-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.entry-icon {
  color: #ffd700;
}

.entry-date {
  color: #ffd700;
  font-size: 12px;
}

.entry-emotion {
  background: rgba(255,215,0,0.1);
  border: 1px solid rgba(255,215,0,0.2);
  border-radius: 4px;
  padding: 1px 7px;
  font-size: 11px;
  color: rgba(255,215,0,0.7);
}

.entry-content {
  color: rgba(240,240,255,0.7);
  font-size: 14px;
  line-height: 1.75;
}

/* Transitions */
.diary-slide-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.diary-slide-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.diary-slide-leave-to {
  opacity: 0;
}
</style>
