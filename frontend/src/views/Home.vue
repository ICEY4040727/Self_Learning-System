<template>
  <div class="main-menu-page">
    <!-- Scene background with v-motion -->
    <Transition name="bg-fade" mode="out-in">
      <div
        :key="bgUrl"
        class="scene-bg"
        :style="{ backgroundImage: `url(${bgUrl})` }"
      ></div>
    </Transition>
    
    <div class="scene-gradient"></div>
    <div class="scene-gradient-radial"></div>
    <ParticleBackground :count="22" :gold-ratio="0.65" />

    <!-- ═══════════════ MAIN MENU ═══════════════ -->
    <Transition name="phase-fade" mode="out-in">
      <div v-if="phase === 'main'" key="main" class="menu-container">
        <!-- Title area with v-motion -->
        <div 
          class="title-area"
          v-motion
          :initial="{ opacity: 0, y: -30 }"
          :enter="{ opacity: 1, y: 0 }"
          :transition="{ delay: 200, duration: 800 }"
        >
          <h1 class="breathe-glow font-ui title-v2">知 遇</h1>
          <div class="font-ui subtitle-v2">Zhī Yù · Socratic Learning</div>
          <div class="gold-divider"></div>
        </div>

        <!-- Menu nav with v-motion stagger -->
        <nav 
          class="menu-nav"
          v-motion
          :initial="{ opacity: 0 }"
          :enter="{ opacity: 1 }"
          :transition="{ delay: 500, duration: 600 }"
        >
          <div
            v-for="(item, i) in MENU_ITEMS"
            :key="item.label"
            v-motion
            :initial="{ opacity: 0, x: -30 }"
            :enter="{ opacity: 1, x: 0 }"
            :transition="{ delay: 500 + i * 0.1, duration: 500 }"
          >
            <div class="galgame-menu-item" @click="item.action">{{ item.label }}</div>
          </div>
        </nav>
      </div>

      <!-- ═══════════════ CHARACTER MANAGE ═══════════════ -->
      <div v-else-if="phase === 'character'" key="character" class="char-manage-container">
        <button class="back-button galgame-hud-btn" @click="phase = 'main'">
          <ArrowLeft :size="14" /> 返回
        </button>

        <div class="char-content galgame-scrollbar">
          <!-- Section header with v-motion -->
          <div 
            class="section-header text-center"
            v-motion
            :initial="{ opacity: 0, y: -20 }"
            :enter="{ opacity: 1, y: 0 }"
          >
            <div class="font-ui section-label">管理学习伙伴</div>
            <div class="font-ui section-title">角 色 档 案</div>
            <div class="gold-divider mx-auto" style="width: 140px; margin-top: 12px;"></div>
          </div>

          <!-- Sage section -->
          <CharSection
            label="知  者"
            label-en="SAGES"
            :accent-color="'#ffd700'"
            :characters="sageCharacters"
            :show-delete="true"
          />

          <!-- Traveler section -->
          <CharSection
            label="旅  者"
            label-en="TRAVELERS"
            :accent-color="'#60a5fa'"
            :characters="travelerCharacters"
            :show-delete="false"
            :style="{ marginTop: 32 }"
          />

          <div class="font-ui hint-text">
            自定义知者可在创建新世界时选用 · 旅者代表你在学习旅程中的身份
          </div>
        </div>
      </div>

      <!-- ═══════════════ WORLD SELECTION ═══════════════ -->
      <div v-else-if="phase === 'worlds'" key="worlds" class="worlds-container">
        <button class="back-button galgame-hud-btn" @click="phase = 'main'">
          <ArrowLeft :size="14" /> 返回
        </button>

        <!-- Section header with v-motion -->
        <div 
          class="section-header text-center"
          v-motion
          :initial="{ opacity: 0, y: -20 }"
          :enter="{ opacity: 1, y: 0 }"
        >
          <div class="font-ui section-label">选择你的学习世界</div>
          <div class="font-ui section-title">世 界 选 择</div>
        </div>

        <div v-if="loading" class="loading-text">加载中…</div>
        <div v-else class="world-grid">
          <div
            v-for="(world, i) in worlds"
            :key="world.id"
            class="world-card"
            v-motion
            :initial="{ opacity: 0, y: 30 }"
            :enter="{ opacity: 1, y: 0 }"
            :transition="{ delay: i * 0.12, duration: 500 }"
            @click="selectWorld(world)"
          >
            <div class="world-card-image" :style="getWorldBgStyle(world)"></div>
            <div class="world-card-sages">
              <div
                v-for="sage in (world.sages || [])"
                :key="sage.id"
                class="sage-avatar"
                :style="{ background: sage.color, borderColor: 'rgba(255,215,0,0.4)' }"
              >
                {{ sage.symbol }}
              </div>
            </div>
            <div class="world-card-stage">
              <span class="stage-badge">{{ world.stageLabel || '初识' }}</span>
            </div>
            <div class="world-card-body">
              <div class="font-ui world-name">{{ world.name }}</div>
              <p class="font-ui world-desc">{{ world.description }}</p>
              <div class="font-ui world-meta">
                <span>📖 {{ world.courses?.length || 0 }} 门课程</span>
              </div>
            </div>
          </div>

          <!-- Create world card -->
          <div
            class="world-card world-card-create"
            v-motion
            :initial="{ opacity: 0, y: 30 }"
            :enter="{ opacity: 1, y: 0 }"
            :transition="{ delay: worlds.length * 0.12 + 0.1, duration: 500 }"
            @click="showCreateWorld = true"
          >
            <div class="create-content">
              <div class="create-icon">
                <Plus :size="20" />
              </div>
              <div class="font-ui create-text">创 建 新 世 界</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════ COURSE SELECTION ═══════════════ -->
      <div v-else-if="phase === 'courses'" key="courses" class="courses-container">
        <button class="back-button galgame-hud-btn" @click="phase = 'worlds'">
          <ArrowLeft :size="14" /> 返回
        </button>

        <!-- Sage sprite with v-motion -->
        <div 
          v-if="activeSage" 
          class="sage-sprite-wrapper"
          v-motion
          :initial="{ opacity: 0, x: -60 }"
          :enter="{ opacity: 1, x: 0 }"
          :transition="{ delay: 200, duration: 600 }"
        >
          <div class="sage-sprite" :style="getSageStyle(activeSage)">
            <div class="sage-symbol">{{ activeSage.symbol }}</div>
            <div class="font-ui sage-name">{{ activeSage.name }}</div>
            <div class="font-ui sage-title">{{ activeSage.title }}</div>
          </div>
        </div>

        <!-- Dialog box with v-motion -->
        <div 
          class="dialog-wrapper"
          v-motion
          :initial="{ opacity: 0, y: 40 }"
          :enter="{ opacity: 1, y: 0 }"
          :transition="{ delay: 400, duration: 500 }"
        >
          <div class="relative">
            <div class="galgame-name-tag font-ui name-tag-parallelogram" :style="nameTagStyle">
              {{ activeSage?.name || '知者' }}
            </div>
            <div class="galgame-dialog dialog-content">
              <p class="font-dialogue dialog-text">
                「{{ selectedWorld?.name }}欢迎你，旅者。今天想学什么呢？」
              </p>
              <div class="choice-list">
                <button
                  v-for="(course, i) in courses"
                  :key="course.id"
                  class="galgame-choice"
                  :style="{ animationName: 'choiceStagger', animationDuration: '0.3s', animationTimingFunction: 'ease-out', animationDelay: `${0.6 + i * 0.08}s`, animationFillMode: 'both' }"
                  @click="startLearning(course.id)"
                >
                  <span class="choice-arrow">▸</span>
                  <span>{{ course.icon || '📚' }} {{ course.name }}</span>
                  <span class="choice-desc">{{ course.description?.slice(0, 20) }}…</span>
                  <span v-if="course.progress && course.progress > 0" class="choice-progress">{{ Math.round(course.progress * 100) }}%</span>
                </button>
                <button class="galgame-choice add-course-btn" @click="showAddCourse = true">
                  <span class="choice-arrow blue">▸</span>
                  <span>＋ 添加新课程</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════ MEMORY VAULT ═══════════════ -->
      <div v-else-if="phase === 'memory'" key="memory" class="memory-container">
        <button class="back-button galgame-hud-btn" @click="phase = 'courses'">
          <ArrowLeft :size="14" /> 返回
        </button>

        <!-- Section header with v-motion -->
        <div 
          class="section-header text-center"
          v-motion
          :initial="{ opacity: 0, y: -20 }"
          :enter="{ opacity: 1, y: 0 }"
        >
          <div class="font-ui section-label">{{ selectedWorld?.name }} · {{ selectedCourse?.name }}</div>
          <div class="font-ui section-title">回 忆 库</div>
        </div>

        <div class="memory-grid">
          <!-- New journey card -->
          <button 
            class="memory-card memory-card-new"
            v-motion
            :initial="{ opacity: 0, y: 20 }"
            :enter="{ opacity: 1, y: 0 }"
            :transition="{ delay: 100, duration: 500 }"
            @click="startNewJourney"
          >
            <div class="new-journey-content">
              <Play :size="22" class="play-icon" />
              <div class="font-ui">新的旅程</div>
            </div>
          </button>

          <!-- Checkpoint cards -->
          <button
            v-for="(cp, i) in checkpoints"
            :key="cp.id"
            class="memory-card"
            v-motion
            :initial="{ opacity: 0, y: 20 }"
            :enter="{ opacity: 1, y: 0 }"
            :transition="{ delay: 100 + (i + 1) * 0.1, duration: 500 }"
            @click="loadCheckpoint(cp)"
          >
            <div class="checkpoint-card" :style="getCheckpointBg(selectedWorld)">
              <div class="checkpoint-info">
                <div class="font-ui cp-name">{{ cp.save_name }}</div>
                <div class="font-ui cp-date">{{ cp.date }}</div>
                <div class="font-ui cp-meta">{{ cp.stage || '初识' }} · {{ cp.masteryPercent || 0 }}%</div>
                <div class="font-ui cp-preview">{{ cp.previewText }}</div>
              </div>
            </div>
          </button>
        </div>
      </div>
    </Transition>

    <p v-if="errorMessage" class="error-toast font-ui">{{ errorMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Plus, Play } from 'lucide-vue-next'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'
import ParticleBackground from '@/components/ParticleBackground.vue'

const router = useRouter()
const authStore = useAuthStore()

type Phase = 'main' | 'character' | 'worlds' | 'courses' | 'memory'
const phase = ref<Phase>('main')
const worlds = ref<World[]>([])
const courses = ref<Course[]>([])
const checkpoints = ref<Checkpoint[]>([])
const selectedWorld = ref<World | null>(null)
const selectedCourse = ref<Course | null>(null)
const errorMessage = ref('')
const loading = ref(false)
const showCreateWorld = ref(false)
const showAddCourse = ref(false)

interface Sage { id: number; name: string; title: string; symbol: string; color: string; accentColor: string }
interface World {
  id: number; name: string; description?: string;
  sceneUrl?: string; scenes?: Record<string, string>;
  sages?: Sage[]; courses?: Course[];
  stageLabel?: string; relationship?: { stage: string };
}
interface Course { id: number; name: string; description?: string; icon?: string; progress?: number; worldId?: number }
interface Checkpoint { id: number; save_name: string; date?: string; stage?: string; masteryPercent?: number; previewText?: string }

const logout = () => { authStore.logout(); router.push('/login') }

const MENU_ITEMS = [
  { label: '开 始 学 习', action: () => { phase.value = 'worlds' } },
  { label: '角 色 管 理', action: () => { phase.value = 'character' } },
  { label: '档 案 管 理', action: () => router.push('/archive') },
  { label: '系 统 设 置', action: () => router.push('/settings') },
  { label: '退 出 登 录', action: logout },
]

// Mock character data (in real app, fetch from API)
const sageCharacters = ref([
  { id: 1, name: '苏格拉底', title: '哲学之父', symbol: '☉', color: '#f59e0b', accentColor: '#fbbf24', description: '古希腊哲学家，启发式对话的奠基人', type: 'sage' as const },
  { id: 2, name: '柏拉图', title: '理念论者', symbol: '◈', color: '#8b5cf6', accentColor: '#a78bfa', description: '苏格拉底的学生，理想国的作者', type: 'sage' as const },
])
const travelerCharacters = ref([
  { id: 101, name: '旅者', title: '求知者', symbol: '✦', color: '#3b82f6', accentColor: '#60a5fa', description: '在学习旅程中不断探索的你', type: 'traveler' as const },
])

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })

const bgUrl = computed(() =>
  selectedWorld.value?.sceneUrl ||
  selectedWorld.value?.scenes?.background ||
  worlds.value[0]?.sceneUrl ||
  worlds.value[0]?.scenes?.background ||
  'https://images.unsplash.com/photo-1629639057315-410edca4fa89?w=1920&q=80'
)

const activeSage = computed(() => selectedWorld.value?.sages?.[0])

const nameTagStyle = {
  top: '-34px',
  left: '20px',
  padding: '4px 22px 4px 14px',
  fontSize: '14px',
  fontWeight: 600,
  color: '#0a0a1e',
  letterSpacing: '3px',
}

const showError = (error: unknown) => {
  errorMessage.value = parseApiError(error)
  setTimeout(() => (errorMessage.value = ''), 4000)
}

const getWorldBgStyle = (world: World) => {
  const url = world.sceneUrl || world.scenes?.background
  return url
    ? { backgroundImage: `url(${url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
    : { background: 'linear-gradient(135deg, #1e3a5f, #4c1d95)' }
}

const getSageStyle = (sage: Sage) => ({
  width: '160px',
  height: '280px',
  background: `linear-gradient(175deg, ${sage.color}ee 0%, ${sage.color}99 40%, #0a0a1e 100%)`,
  borderRadius: '8px 8px 0 0',
  border: '1px solid rgba(255,215,0,0.25)',
  display: 'flex',
  flexDirection: 'column' as const,
  alignItems: 'center',
  justifyContent: 'flex-end',
  paddingBottom: '12px',
  boxShadow: `0 0 30px ${sage.accentColor}30`,
  position: 'relative' as const,
  overflow: 'hidden' as const,
})

const getCheckpointBg = (world: World | null) => {
  const color = world?.sages?.[0]?.color || '#1a1a2e'
  return { background: `linear-gradient(135deg, ${color} 0%, #0a0a1e 100%)` }
}

const fetchWorlds = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/worlds', { headers: headers() })
    worlds.value = res.data
  } catch (error) {
    showError(error)
  } finally {
    loading.value = false
  }
}

const fetchCourses = async () => {
  if (!selectedWorld.value) return
  try {
    const res = await axios.get(`/api/worlds/${selectedWorld.value.id}/courses`, { headers: headers() })
    courses.value = res.data
  } catch (error) {
    showError(error)
  }
}

const fetchCheckpoints = async () => {
  if (!selectedWorld.value) return
  try {
    const res = await axios.get(`/api/worlds/${selectedWorld.value.id}/checkpoints`, { headers: headers() })
    checkpoints.value = res.data
  } catch {
    checkpoints.value = []
  }
}

const selectWorld = async (world: World) => {
  selectedWorld.value = world
  await fetchCourses()
  await fetchCheckpoints()
  if (checkpoints.value.length > 0) {
    phase.value = 'memory'
  } else {
    phase.value = 'courses'
  }
}

const startLearning = (courseId: number) => {
  selectedCourse.value = courses.value.find(c => c.id === courseId) || null
  router.push({
    path: `/learning/${courseId}`,
    query: { worldId: String(selectedWorld.value?.id || '') }
  })
}

const loadCheckpoint = (cp: Checkpoint) => {
  router.push({
    path: '/learning',
    query: {
      worldId: String(selectedWorld.value?.id),
      courseId: String(selectedCourse.value?.id),
      checkpointId: String(cp.id),
    },
  })
}

const startNewJourney = () => {
  if (selectedCourse.value) startLearning(selectedCourse.value.id)
}

onMounted(async () => { await fetchWorlds() })
</script>

<script lang="ts">
// CharSection component placeholder
</script>

<style scoped>
.main-menu-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #0a0a1e;
}

.scene-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.15;
  transition: opacity 1.2s ease;
}

.scene-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(10,10,30,0.55) 0%, rgba(0,0,0,0.72) 100%);
}

.scene-gradient-radial {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 0%, rgba(10,10,30,0.3) 0%, transparent 60%);
}

/* Menu Container */
.menu-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.title-area {
  text-align: center;
  margin-bottom: 64px;
}

.title-v2 {
  font-size: 32px;
  letter-spacing: 10px;
  color: #ffd700;
  margin-bottom: 10px;
}

.subtitle-v2 {
  font-size: 13px;
  letter-spacing: 4px;
  color: rgba(255,255,255,0.4);
}

.gold-divider {
  width: 180px;
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(255,215,0,0.4), transparent);
  margin: 14px auto 0;
}

.menu-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Character Manage */
.char-manage-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 72px;
  overflow-y: auto;
}

.char-content {
  width: 100%;
  max-width: 900px;
  padding: 0 32px 32px;
  overflow-y: auto;
}

.section-header {
  margin-bottom: 32px;
}

.section-label {
  color: rgba(255,255,255,0.35);
  font-size: 12px;
  letter-spacing: 4px;
  margin-bottom: 8px;
}

.section-title {
  color: #ffd700;
  font-size: 22px;
  letter-spacing: 6px;
}

.hint-text {
  text-align: center;
  margin-top: 32px;
  color: rgba(255,255,255,0.16);
  font-size: 11px;
  letter-spacing: 2px;
}

/* Worlds Container */
.worlds-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 48px;
  overflow-y: auto;
}

.loading-text {
  color: rgba(255,255,255,0.5);
  text-align: center;
  margin-top: 60px;
}

.world-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
  max-width: 860px;
  width: 100%;
  padding: 0 32px;
}

.world-card {
  cursor: pointer;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 215, 0, 0.15);
  background: rgba(8,8,28,0.97);
  transition: all 0.3s ease;
  position: relative;
}

.world-card:hover {
  border-color: rgba(255, 215, 0, 0.55);
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(255, 215, 0, 0.15);
}

.world-card-image {
  height: 130px;
  position: relative;
}

.world-card-image::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 30%, rgba(8,8,28,0.95) 100%);
}

.world-card-sages {
  position: absolute;
  top: 8px;
  left: 12px;
  display: flex;
  gap: 6px;
  z-index: 2;
}

.sage-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: rgba(255,255,255,0.9);
  font-weight: 600;
}

.world-card-stage {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
}

.stage-badge {
  background: rgba(0,0,0,0.7);
  border: 1px solid rgba(255,215,0,0.3);
  border-radius: 4px;
  padding: 2px 7px;
  font-size: 10px;
  color: #ffd700;
  font-family: 'Noto Sans SC', sans-serif;
}

.world-card-body {
  padding: 12px 14px 14px;
}

.world-name {
  font-size: 15px;
  letter-spacing: 2px;
  color: #ffd700;
  margin-bottom: 5px;
}

.world-desc {
  font-size: 11px;
  line-height: 1.6;
  color: rgba(255,255,255,0.45);
  margin-bottom: 8px;
}

.world-meta {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
}

.world-card-create {
  min-height: 234px;
  background: rgba(255,255,255,0.02);
  display: flex;
  align-items: center;
  justify-content: center;
}

.create-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.create-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px dashed rgba(255,215,0,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,215,0,0.4);
}

.create-text {
  color: rgba(255,215,0,0.35);
  font-size: 12px;
  letter-spacing: 2px;
}

/* Courses Container */
.courses-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  padding-bottom: 220px;
}

.sage-sprite-wrapper {
  position: absolute;
  bottom: calc(230px + 44px);
  left: 8%;
}

.sage-sprite {
  position: relative;
}

.sage-symbol {
  position: absolute;
  top: 20%;
  left: 50%;
  transform: translateX(-50%);
  font-size: 70px;
  color: rgba(255,215,0,0.4);
  font-family: serif;
  font-weight: 700;
  opacity: 0.82;
  user-select: none;
  line-height: 1;
}

.sage-name {
  color: #ffd700;
  font-size: 14px;
  letter-spacing: 2px;
  font-weight: 500;
  position: relative;
  z-index: 1;
}

.sage-title {
  color: rgba(255,255,255,0.4);
  font-size: 11px;
  letter-spacing: 1px;
  margin-top: 3px;
  position: relative;
  z-index: 1;
}

.dialog-wrapper {
  position: absolute;
  bottom: 12px;
  left: 16px;
  right: 16px;
}

.name-tag-parallelogram {
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 100%, 0 100%);
}

.dialog-content {
  padding: 16px 28px 18px;
}

.dialog-text {
  font-size: 18px;
  line-height: 1.85;
  color: #f0f0ff;
  margin-bottom: 14px;
}

.choice-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.choice-arrow {
  color: #ffd700;
  font-size: 11px;
}

.choice-arrow.blue {
  color: #60a5fa;
}

.choice-desc {
  color: rgba(255,255,255,0.3);
  font-size: 12px;
  margin-left: auto;
}

.choice-progress {
  color: #4adf6a;
  font-size: 11px;
  white-space: nowrap;
  margin-left: 8px;
}

.add-course-btn {
  color: rgba(96,165,250,0.85);
}

/* Memory Container */
.memory-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 48px;
}

.memory-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 700px;
  width: 100%;
  padding: 0 32px;
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

.cp-preview {
  color: rgba(255,255,255,0.3);
  font-size: 10px;
  margin-top: 1px;
}

/* Back Button */
.back-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 13px;
  padding: 6px 14px;
  cursor: pointer;
  margin-bottom: 24px;
}

/* Error Toast */
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
  letter-spacing: 1px;
}

/* Transitions */
.bg-fade-enter-from, .bg-fade-leave-to { opacity: 0; }
.bg-fade-enter-active, .bg-fade-leave-active { transition: opacity 1.2s ease; }

.phase-fade-enter-from { opacity: 0; }
.phase-fade-enter-active { transition: opacity 0.5s ease; }
.phase-fade-leave-to { opacity: 0; }
.phase-fade-leave-active { transition: opacity 0.4s ease; }
</style>
