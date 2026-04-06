<template>
  <div class="world-detail-page">
    <!-- Dynamic background based on world -->
    <div class="scene-bg" :style="getWorldBgStyle(selectedWorld)"></div>
    <div class="scene-overlay"></div>

    <button class="back-button galgame-hud-btn" @click="$router.push('/home/worlds')">
      <ArrowLeft :size="14" /> 返回世界
    </button>

    <!-- World header -->
    <div 
      v-if="selectedWorld"
      class="world-header"
      v-motion
      :initial="{ opacity: 0, y: -20 }"
      :enter="{ opacity: 1, y: 0 }"
    >
      <div class="sage-avatar-large" :style="{ background: selectedWorld.sages?.[0]?.color }">
        {{ selectedWorld.sages?.[0]?.symbol || '?' }}
      </div>
      <div class="world-info">
        <div class="font-ui world-name">{{ selectedWorld.name }}</div>
        <div class="font-ui world-desc">{{ selectedWorld.description }}</div>
      </div>
    </div>

    <!-- Courses section -->
    <div class="courses-section">
      <div class="section-header text-center">
        <div class="font-ui section-label">{{ selectedWorld?.name }}</div>
        <div class="font-ui section-title">课 程 选 择</div>
      </div>

      <div v-if="loading" class="loading-text">加载中…</div>
      <div v-else class="courses-grid">
        <div
          v-for="(course, i) in courses"
          :key="course.id"
          class="course-card"
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :enter="{ opacity: 1, y: 0 }"
          :transition="{ delay: i * 0.1, duration: 400 }"
          @click="selectCourse(course)"
        >
          <div class="course-icon">{{ course.icon || '📚' }}</div>
          <div class="course-info">
            <div class="font-ui course-name">{{ course.name }}</div>
            <div class="font-ui course-desc">{{ course.description }}</div>
            <div v-if="course.progress && course.progress > 0" class="course-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: `${course.progress * 100}%` }"></div>
              </div>
              <span class="progress-text">{{ Math.round(course.progress * 100) }}%</span>
            </div>
          </div>
          <div class="course-arrow">▸</div>
        </div>
      </div>
    </div>

    <!-- Memory section (checkpoints) -->
    <div v-if="selectedCourse" class="memory-section">
      <div class="section-header text-center">
        <div class="font-ui section-label">{{ selectedCourse.name }} · 回忆库</div>
        <div class="font-ui section-title">回 忆 选 择</div>
      </div>

      <div v-if="checkpointsLoading" class="loading-text">加载回忆…</div>
      <div v-else class="memory-grid">
        <!-- New journey -->
        <button 
          class="memory-card memory-card-new"
          @click="startLearning(selectedCourse.id)"
        >
          <div class="new-journey-content">
            <Play :size="22" class="play-icon" />
            <div class="font-ui">新的旅程</div>
          </div>
        </button>

        <!-- Existing checkpoints -->
        <button
          v-for="cp in checkpoints"
          :key="cp.id"
          class="memory-card"
          @click="loadCheckpoint(cp)"
        >
          <div class="checkpoint-card" :style="getCheckpointBg()">
            <div class="checkpoint-info">
              <div class="font-ui cp-name">{{ cp.save_name }}</div>
              <div class="font-ui cp-date">{{ cp.date }}</div>
              <div class="font-ui cp-meta">{{ cp.stage || '初识' }} · {{ cp.masteryPercent || 0 }}%</div>
            </div>
          </div>
        </button>
      </div>
    </div>

    <p v-if="errorMessage" class="error-toast font-ui">{{ errorMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Play } from 'lucide-vue-next'
import client from '@/api/client'

import { parseApiError } from '@/utils/error'

const route = useRoute()
const router = useRouter()

interface Sage { id: number; name: string; title: string; symbol: string; color: string; accentColor: string }
interface World {
  id: number; user_id: number; name: string; description?: string
  scenes?: { background?: string }; sages?: Sage[]; courses?: Course[]; stageLabel?: string
}
interface Course { id: number; name: string; description?: string; icon?: string; progress?: number }
interface Checkpoint { id: number; save_name: string; date?: string; stage?: string; masteryPercent?: number }

const worldId = computed(() => Number(route.params.worldId))

const selectedWorld = ref<World | null>(null)
const courses = ref<Course[]>([])
const selectedCourse = ref<Course | null>(null)
const checkpoints = ref<Checkpoint[]>([])
const errorMessage = ref('')
const loading = ref(false)
const checkpointsLoading = ref(false)


const getWorldBgStyle = (world: World | null) => {
  if (!world) return {}
  const url = world.scenes?.background
  return url
    ? { backgroundImage: `url(${url})` }
    : { background: 'linear-gradient(135deg, #1e3a5f, #4c1d95)' }
}

const getCheckpointBg = () => {
  const color = selectedWorld.value?.sages?.[0]?.color || '#1a1a2e'
  return { background: `linear-gradient(135deg, ${color} 0%, #0a0a1e 100%)` }
}

const showError = (error: unknown) => {
  errorMessage.value = parseApiError(error)
  setTimeout(() => (errorMessage.value = ''), 4000)
}

const fetchWorld = async () => {
  try {
    const { data } = await client.get(`/worlds/${worldId.value}`)
    selectedWorld.value = data
  } catch (error) {
    showError(error)
  }
}

const fetchCourses = async () => {
  loading.value = true
  try {
    const { data } = await client.get(`/worlds/${worldId.value}/courses`)
    courses.value = data
  } catch (error) {
    courses.value = []
    showError(error)
  } finally {
    loading.value = false
  }
}

const fetchCheckpoints = async (courseId: number) => {
  checkpointsLoading.value = true
  try {
    const { data } = await client.get(`/courses/${courseId}/checkpoints`)
    checkpoints.value = data
  } catch {
    checkpoints.value = []
  } finally {
    checkpointsLoading.value = false
  }
}

const selectCourse = async (course: Course) => {
  selectedCourse.value = course
  await fetchCheckpoints(course.id)
}

const startLearning = (courseId: number) => {
  router.push({
    path: `/home/worlds/${worldId.value}/courses/${courseId}`,
    query: { from: 'new' }
  })
}

const loadCheckpoint = (cp: Checkpoint) => {
  router.push({
    path: `/home/worlds/${worldId.value}/courses/${selectedCourse.value?.id}`,
    query: { checkpointId: String(cp.id) }
  })
}

onMounted(async () => {
  await fetchWorld()
  await fetchCourses()
})
</script>

<style scoped>
.world-detail-page {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  overflow-y: auto;
  background: #0a0a1e;
  padding: 48px 32px;
}

.scene-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.35;
  transition: background-image 0.8s ease;
}

.scene-overlay {
  position: fixed;
  inset: 0;
  background: 
    radial-gradient(ellipse at 50% 0%, rgba(10,10,30,0.3) 0%, transparent 60%),
    linear-gradient(to bottom, rgba(10,10,30,0.4) 0%, rgba(0,0,0,0.6) 100%);
  z-index: 0;
}

.back-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 13px;
  padding: 6px 14px;
  cursor: pointer;
  position: relative;
  z-index: 1;
}

.world-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 40px;
  position: relative;
  z-index: 1;
}

.sage-avatar-large {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  border: 2px solid rgba(255,215,0,0.4);
}

.world-info {
  flex: 1;
}

.world-name {
  font-size: 24px;
  letter-spacing: 4px;
  color: #ffd700;
  margin-bottom: 6px;
}

.world-desc {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  line-height: 1.6;
}

.courses-section,
.memory-section {
  position: relative;
  z-index: 1;
  margin-bottom: 48px;
}

.section-header {
  margin-bottom: 24px;
}

.section-label {
  color: rgba(255,255,255,0.35);
  font-size: 12px;
  letter-spacing: 4px;
  margin-bottom: 8px;
}

.section-title {
  color: #ffd700;
  font-size: 20px;
  letter-spacing: 6px;
}

.loading-text {
  color: rgba(255,255,255,0.5);
  text-align: center;
  margin-top: 32px;
}

.courses-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 600px;
}

.course-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: rgba(8,8,28,0.9);
  border: 1px solid rgba(255,215,0,0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.course-card:hover {
  border-color: rgba(255,215,0,0.5);
  transform: translateX(8px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

.course-icon {
  font-size: 32px;
}

.course-info {
  flex: 1;
}

.course-name {
  font-size: 16px;
  color: #ffd700;
  margin-bottom: 4px;
}

.course-desc {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
}

.course-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: rgba(255,255,255,0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #4adf6a);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 11px;
  color: #4adf6a;
}

.course-arrow {
  color: rgba(255,215,0,0.4);
  font-size: 18px;
}

.memory-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  max-width: 700px;
}

.memory-card {
  aspect-ratio: 16/10;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: none;
  padding: 0;
  background: none;
  text-align: left;
}

.memory-card-new {
  background: rgba(255,215,0,0.04);
  border: 1px dashed rgba(255,215,0,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.new-journey-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.play-icon {
  color: rgba(255,215,0,0.6);
}

.new-journey-content .font-ui {
  color: rgba(255,215,0,0.6);
  font-size: 12px;
  letter-spacing: 2px;
}

.checkpoint-card {
  height: 100%;
  position: relative;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  border-radius: 8px;
}

.checkpoint-info {
  background: rgba(0,0,0,0.7);
  border-radius: 6px;
  padding: 6px 8px;
}

.cp-name {
  color: #ffd700;
  font-size: 11px;
}

.cp-date {
  color: rgba(255,255,255,0.4);
  font-size: 10px;
  margin-top: 2px;
}

.cp-meta {
  color: rgba(255,255,255,0.55);
  font-size: 10px;
  margin-top: 1px;
}

.error-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(223, 74, 74, 0.9);
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  z-index: 9999;
}
</style>
