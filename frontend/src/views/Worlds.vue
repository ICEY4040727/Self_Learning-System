<template>
  <div class="worlds-page">
    <div class="scene-bg" :style="{ backgroundImage: `url(${homeBg})` }"></div>
    <div class="scene-overlay"></div>

    <!-- Header -->
    <div class="char-header">
      <button class="back-btn" @click="$router.push('/home')">
        <span>←</span> 返回
      </button>
      <h1 class="header-title">世 界 选 择</h1>
      <div style="width: 80px;"></div>
    </div>

    <!-- Content -->
    <div class="char-content">
      <div v-if="loading" class="loading-text">加载中…</div>
      <div v-else>
        <!-- Worlds List -->
        <div class="section-group">
          <div class="section-header">
            <span class="section-label">我 的 世 界</span>
            <span class="section-sublabel">MY WORLDS</span>
          </div>
          <div class="section-line"></div>
          <div class="worlds-list">
            <div
              v-for="world in worlds"
              :key="world.id"
              class="world-item"
              @click="selectWorld(world)"
            >
              <div class="world-info">
                <div class="world-name">{{ world.name }}</div>
                <div class="world-meta">
                  <span>{{ world.courses?.length || 0 }} 门课程</span>
                  <span class="separator">·</span>
                  <span>{{ world.sages?.length || 0 }} 位知者</span>
                </div>
              </div>
              <div class="world-arrow">▸</div>
            </div>
            <!-- Create world -->
            <div class="world-item world-item-create" @click="showCreateWorld = true">
              <div class="world-info">
                <div class="world-name">创建新世界</div>
                <div class="world-meta">添加一个新的学习空间</div>
              </div>
              <div class="world-add-icon">+</div>
            </div>
          </div>
        </div>
      </div>

          </div>

    <!-- Create World Modal -->
    <CreateWorldModal
      :show="showCreateWorld"
      @close="showCreateWorld = false"
      @create="handleCreateWorld"
    />
  </div>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
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
const loading = ref(false)
const showCreateWorld = ref(false)

const toast = useToast()

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
      worlds.value = []
    }
  } catch (error) {
    worlds.value = []
    toast.error(parseApiError(error))
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
    router.push(`/home/worlds/${newWorld.id}`)
  } catch (error) {
    toast.error(parseApiError(error))
  }
}

onMounted(async () => { await fetchWorlds() })
</script>

<style scoped>
.worlds-page {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  background: #0a0a1e;
  overflow-y: auto;
  padding-bottom: 48px;
}

.scene-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.6;
}

.scene-overlay {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(10,10,30,0.15) 0%, transparent 60%),
    radial-gradient(ellipse at 30% 55%, rgba(255,215,0,0.05) 0%, transparent 55%),
    linear-gradient(to bottom, rgba(10,10,30,0.25) 0%, rgba(0,0,0,0.45) 100%);
  z-index: 0;
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

.section-sublabel {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
  letter-spacing: 3px;
}

.section-line {
  width: 100%;
  height: 1px;
  background: linear-gradient(to right, rgba(255, 215, 0, 0.3), transparent);
  margin-bottom: 20px;
}

.loading-text {
  color: rgba(255,255,255,0.5);
  text-align: center;
  padding: 60px 0;
  font-family: "Noto Sans SC", sans-serif;
  letter-spacing: 2px;
}

/* Worlds List */
.worlds-list {
  display: flex;
  flex-direction: column;
}

.world-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s ease;
}

.world-item:last-child {
  border-bottom: none;
}

.world-item:hover {
  background: rgba(255, 215, 0, 0.05);
  padding-left: 32px;
}

.world-item-create:hover {
  padding-left: 24px;
}

.world-info {
  flex: 1;
}

.world-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 6px;
  letter-spacing: 1px;
}

.world-meta {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  font-family: "Noto Sans SC", sans-serif;
}

.separator {
  margin: 0 8px;
  color: rgba(255, 215, 0, 0.3);
}

.world-arrow {
  font-size: 18px;
  color: rgba(255, 215, 0, 0.4);
}

.world-add-icon {
  font-size: 28px;
  color: rgba(255, 215, 0, 0.3);
}

.world-item-create:hover .world-add-icon {
  color: rgba(255, 215, 0, 0.6);
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
  font-family: "Noto Sans SC", sans-serif;
}
</style>
