<template>
  <div class="worlds-page">
    <div class="scene-bg" :style="{ backgroundImage: `url(${homeBg})` }"></div>
    <div class="scene-overlay"></div>

    <button class="back-button galgame-hud-btn" @click="$router.push('/home')">
      <ArrowLeft :size="14" /> 返回
    </button>

    <!-- Section header -->
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

    <p v-if="errorMessage" class="error-toast font-ui">{{ errorMessage }}</p>

    <!-- Create World Modal -->
    <CreateWorldModal
      :show="showCreateWorld"
      @close="showCreateWorld = false"
      @create="handleCreateWorld"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Plus } from 'lucide-vue-next'
import client from '@/api/client'

import homeBg from '@/assets/home-bg.png'
import { parseApiError } from '@/utils/error'
import CreateWorldModal from '@/components/CreateWorldModal.vue'

const router = useRouter()

interface Sage { id: number; name: string; title: string; symbol: string; color: string; accentColor: string }
interface World {
  id: number
  user_id: number
  name: string
  description?: string
  scenes?: { background?: string; [key: string]: any }
  sages?: Sage[]
  courses?: Course[]
  stageLabel?: string
  relationship?: { stage?: string; [key: string]: any }
}
interface Course { id: number; name: string; description?: string; icon?: string; progress?: number; worldId?: number }

const worlds = ref<World[]>([])
const errorMessage = ref('')
const loading = ref(false)
const showCreateWorld = ref(false)


const getWorldBgStyle = (world: World) => {
  const url = world.scenes?.background
  return url
    ? { backgroundImage: `url(${url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
    : { background: 'linear-gradient(135deg, #1e3a5f, #4c1d95)' }
}

const showError = (error: unknown) => {
  errorMessage.value = parseApiError(error)
  setTimeout(() => (errorMessage.value = ''), 4000)
}

// Mock world for UI preview (when API is unavailable)
const MOCK_WORLDS: World[] = [
  {
    id: 1,
    user_id: 1,
    name: '幕府学堂',
    description: '战国烽火中的智慧殿堂，以古代兵法洞察现代战略与领导力',
    scenes: { background: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=400' },
    sages: [
      { id: 1, name: '孙子', title: '兵圣', symbol: '兵', color: '#dc2626', accentColor: '#f87171' }
    ],
    courses: [
      { id: 1, name: '孙子兵法', description: '知己知彼，百战不殆' }
    ],
    stageLabel: '初识',
  }
]

const fetchWorlds = async () => {
  loading.value = true
  try {
    const { data } = await client.get('worlds')
    worlds.value = data.map((world: any) => ({
      ...world,
      sages: world.sages || [],
      courses: world.courses || [],
      stageLabel: world.stageLabel || '初识',
    }))
    if (worlds.value.length === 0) {
      worlds.value = MOCK_WORLDS
    }
  } catch (error) {
    worlds.value = MOCK_WORLDS
    console.warn('API unavailable, using mock data for preview')
  } finally {
    loading.value = false
  }
}

const selectWorld = (world: World) => {
  router.push(`/home/worlds/${world.id}`)
}

const handleCreateWorld = async (data: { name: string; description: string; scenes: Record<string, any> }) => {
  try {
    const { data: newWorld } = await client.post('/worlds', {
      name: data.name,
      description: data.description,
      scenes: data.scenes,
    })
    worlds.value = [...worlds.value, { ...newWorld, sages: [], courses: [], stageLabel: '初识' }]
    showCreateWorld.value = false
    // 跳转到世界详情页，引导添加成员
    router.push(`/home/worlds/${newWorld.id}`)
  } catch (error) {
    showError(error)
  }
}

onMounted(async () => { await fetchWorlds() })
</script>

<style scoped>
.worlds-page {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  overflow-y: auto;
  background: #0a0a1e;
  padding-top: 48px;
  padding-bottom: 48px;
}

.scene-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.60;
}

.scene-overlay {
  position: fixed;
  inset: 0;
  background: 
    radial-gradient(ellipse at 50% 0%, rgba(10,10,30,0.15) 0%, transparent 60%),
    radial-gradient(ellipse at 30% 55%, rgba(255,215,0,0.05) 0%, transparent 55%),
    radial-gradient(ellipse at 70% 35%, rgba(96,165,250,0.04) 0%, transparent 55%),
    linear-gradient(to bottom, rgba(10,10,30,0.25) 0%, rgba(0,0,0,0.45) 100%);
  z-index: 0;
}

.section-header {
  text-align: center;
  position: relative;
  z-index: 1;
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
  margin: 0 auto;
  padding: 0 32px;
  position: relative;
  z-index: 1;
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

.back-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: 'Noto Sans SC', sans-serif;
  font-size: 13px;
  padding: 6px 14px;
  cursor: pointer;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
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
  letter-spacing: 1px;
}
</style>
