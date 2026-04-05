<template>
  <div class="home-page" :style="sceneStyle">
    <div class="scene-overlay"></div>
    <div class="scene-vignette"></div>

    <div class="home-layout">
      <Transition name="phase" mode="out-in">
        <section v-if="phase === 'menu'" key="menu" class="phase-menu">
          <div class="menu-brand">
            <p class="menu-subtitle">Zhī Yù · Socratic Learning</p>
            <h1>知 遇</h1>
          </div>

          <div class="menu-actions">
            <button class="galgame-btn galgame-menu-item" :disabled="loadingWorlds" @click="enterWorlds">
              {{ loadingWorlds ? '载入世界中…' : '开始学习' }}
            </button>
            <button class="galgame-btn galgame-menu-item" @click="router.push('/archive')">档案管理</button>
            <button class="galgame-btn galgame-menu-item" @click="router.push('/character')">角色设定</button>
            <button class="galgame-btn galgame-menu-item" @click="router.push('/settings')">系统设置</button>
            <button class="galgame-btn galgame-menu-item muted" @click="logout">退出登录</button>
          </div>
        </section>

        <section v-else-if="phase === 'worlds'" key="worlds" class="phase-panel galgame-panel">
          <header class="phase-header">
            <p>WORLD-FIRST FLOW</p>
            <h2>选择世界</h2>
          </header>

          <div v-if="loadingWorlds" class="hint">世界加载中...</div>
          <p v-else-if="worlds.length === 0" class="hint">暂无世界，请先在角色设定中创建。</p>

          <div v-else class="world-grid">
            <button
              v-for="world in worlds"
              :key="world.id"
              class="galgame-world-card world-card"
              @click="selectWorld(world)"
            >
              <strong>{{ world.name }}</strong>
              <span>{{ world.description || '暂无描述' }}</span>
            </button>
          </div>

          <button class="galgame-btn galgame-menu-item back-btn" @click="phase = 'menu'">← 返回主菜单</button>
        </section>

        <section v-else-if="phase === 'memory'" key="memory" class="phase-panel phase-memory galgame-panel">
          <header class="phase-header">
            <p>MEMORY VAULT</p>
            <h2>回忆库 · {{ selectedWorld?.name }}</h2>
          </header>

          <TimelineTree v-if="selectedWorld" :world-id="selectedWorld.id" @branch="branchFromCheckpoint" />

          <div class="actions">
            <button class="galgame-btn galgame-menu-item" :disabled="loadingCourses" @click="enterCourses">
              {{ loadingCourses ? '载入课程中…' : '进入课程选择' }}
            </button>
            <button class="galgame-btn galgame-menu-item back-btn" @click="phase = 'worlds'">← 返回世界列表</button>
          </div>
        </section>

        <section v-else key="courses" class="phase-panel galgame-panel">
          <header class="phase-header">
            <p>COURSE SELECT</p>
            <h2>课程选择 · {{ selectedWorld?.name }}</h2>
          </header>

          <div v-if="loadingCourses" class="hint">课程加载中...</div>
          <p v-else-if="courses.length === 0" class="hint">该世界下暂无课程。</p>

          <div v-else class="course-list">
            <button
              v-for="course in courses"
              :key="course.id"
              class="galgame-world-card world-card"
              @click="startLearning(course.id)"
            >
              <strong>{{ course.name }}</strong>
              <span>{{ course.description || '暂无描述' }}</span>
            </button>
          </div>

          <button class="galgame-btn galgame-menu-item back-btn" @click="phase = 'memory'">← 返回回忆库</button>
        </section>
      </Transition>
    </div>

    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'
import { buildLearningRoute } from '@/utils/navigation'
import TimelineTree from '@/components/TimelineTree.vue'

interface World {
  id: number
  name: string
  description?: string
  scenes?: Record<string, string>
}

interface Course {
  id: number
  name: string
  description?: string
}

interface BranchResponse {
  course_id?: number
  world_id?: number
  session_id?: number | null
}

const router = useRouter()
const authStore = useAuthStore()
const phase = ref<'menu' | 'worlds' | 'memory' | 'courses'>('menu')
const worlds = ref<World[]>([])
const courses = ref<Course[]>([])
const selectedWorld = ref<World | null>(null)
const errorMessage = ref('')
const loadingWorlds = ref(false)
const loadingCourses = ref(false)

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })

const sceneStyle = computed(() => {
  const scenes = selectedWorld.value?.scenes || {}
  const url = scenes.default || Object.values(scenes)[0]
  return url
    ? { backgroundImage: `url(${url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
    : {}
})

const toPositiveInt = (value: unknown): number | undefined => {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

const showError = (error: unknown) => {
  errorMessage.value = parseApiError(error)
  setTimeout(() => (errorMessage.value = ''), 4000)
}

const fetchWorlds = async (): Promise<boolean> => {
  loadingWorlds.value = true
  try {
    const res = await axios.get('/api/worlds', { headers: headers() })
    worlds.value = Array.isArray(res.data) ? res.data : []
    return true
  } catch (error) {
    showError(error)
    return false
  } finally {
    loadingWorlds.value = false
  }
}

const fetchCourses = async (): Promise<boolean> => {
  if (!selectedWorld.value) {
    showError(new Error('请先选择世界'))
    return false
  }

  loadingCourses.value = true
  try {
    const res = await axios.get(`/api/worlds/${selectedWorld.value.id}/courses`, { headers: headers() })
    courses.value = Array.isArray(res.data) ? res.data : []
    return true
  } catch (error) {
    showError(error)
    return false
  } finally {
    loadingCourses.value = false
  }
}

const enterWorlds = async () => {
  const loaded = await fetchWorlds()
  if (loaded) phase.value = 'worlds'
}

const selectWorld = (world: World) => {
  selectedWorld.value = world
  courses.value = []
  phase.value = 'memory'
}

const enterCourses = async () => {
  const loaded = await fetchCourses()
  if (loaded) phase.value = 'courses'
}

const startLearning = (courseId: number) => {
  const worldId = selectedWorld.value?.id
  if (!worldId) {
    showError(new Error('请先选择世界'))
    return
  }
  router.push(buildLearningRoute(courseId, { worldId }))
}

const branchFromCheckpoint = async (checkpoint: { id: number; save_name: string }) => {
  try {
    const branchNameInput = window.prompt('请输入分叉名称（可选）')
    if (branchNameInput === null) return

    const trimmedBranchName = branchNameInput.trim()
    const payload = trimmedBranchName ? { branch_name: trimmedBranchName } : {}
    const res = await axios.post(`/api/checkpoints/${checkpoint.id}/branch`, payload, { headers: headers() })
    const data = res.data as BranchResponse

    const courseId = toPositiveInt(data.course_id)
    if (!courseId) throw new Error('分叉失败：未返回有效课程')

    router.push(buildLearningRoute(courseId, {
      worldId: toPositiveInt(data.world_id) || selectedWorld.value?.id,
      sessionId: toPositiveInt(data.session_id),
    }))
  } catch (error) {
    showError(error)
  }
}

const logout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.home-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: radial-gradient(ellipse at 50% 30%, #1a1a3e 0%, #0a0a1e 70%);
}

.scene-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(10, 10, 30, 0.52), rgba(0, 0, 0, 0.72));
}

.scene-vignette {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, transparent 28%, rgba(0, 0, 0, 0.42) 100%);
}

.home-layout {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
}

.phase-menu {
  width: 100%;
  max-width: 1080px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 32px;
}

.menu-brand h1 {
  color: var(--accent-gold);
  font-size: 52px;
  letter-spacing: 14px;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.28);
}

.menu-subtitle {
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.45);
  letter-spacing: 3px;
}

.menu-actions {
  width: min(320px, 100%);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.phase-panel {
  width: 100%;
  max-width: 1024px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.phase-memory {
  max-width: 1120px;
}

.phase-header p {
  color: rgba(255, 255, 255, 0.46);
  letter-spacing: 3px;
  font-size: 11px;
  margin-bottom: 6px;
}

.phase-header h2 {
  color: var(--accent-gold);
  margin-bottom: 4px;
}

.world-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow-y: auto;
}

.world-card {
  text-align: left;
  width: 100%;
}

.world-card span {
  color: var(--text-secondary);
  font-size: 12px;
}

.actions {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 4px;
}

.back-btn {
  text-align: center;
}

.hint {
  color: var(--text-secondary);
  font-size: 13px;
}

.muted {
  color: #aaa;
}

.error {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
  background: rgba(223, 74, 74, 0.92);
  padding: 8px 14px;
  border-radius: 6px;
}

.phase-enter-active,
.phase-leave-active {
  transition: transform 0.25s ease;
}

.phase-enter-from,
.phase-leave-to {
  transform: translateY(8px);
}

@media (max-width: 900px) {
  .phase-menu {
    flex-direction: column;
    align-items: flex-start;
  }

  .menu-brand h1 {
    font-size: 40px;
    letter-spacing: 10px;
  }

  .menu-actions {
    width: 100%;
    max-width: 420px;
  }
}
</style>
