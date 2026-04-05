<template>
  <div class="home-page" :style="sceneStyle">
    <div class="mask"></div>
    <div class="content">
      <Transition name="fade" mode="out-in">
        <section v-if="phase === 'menu'" key="menu" class="panel galgame-panel">
          <h1>苏格拉底学习系统</h1>
          <button class="galgame-btn galgame-menu-item" @click="enterWorlds">开始学习</button>
          <button class="galgame-btn galgame-menu-item" @click="router.push('/archive')">档案管理</button>
          <button class="galgame-btn galgame-menu-item" @click="router.push('/character')">角色设定</button>
          <button class="galgame-btn galgame-menu-item" @click="router.push('/settings')">系统设置</button>
          <button class="galgame-btn galgame-menu-item muted" @click="logout">退出登录</button>
        </section>

        <section v-else-if="phase === 'worlds'" key="worlds" class="panel galgame-panel">
          <h2>选择世界</h2>
          <div class="list">
            <button v-for="world in worlds" :key="world.id" class="item galgame-world-card" @click="selectWorld(world)">
              <strong>{{ world.name }}</strong>
              <span>{{ world.description || '暂无描述' }}</span>
            </button>
          </div>
          <button class="back galgame-btn galgame-menu-item" @click="phase = 'menu'">← 返回</button>
        </section>

        <section v-else-if="phase === 'memory'" key="memory" class="panel wide galgame-panel">
          <h2>回忆库 · {{ selectedWorld?.name }}</h2>
          <TimelineTree v-if="selectedWorld" :world-id="selectedWorld.id" @branch="branchFromCheckpoint" />
          <div class="actions">
            <button class="galgame-btn galgame-menu-item" @click="enterCourses">进入课程选择</button>
            <button class="back galgame-btn galgame-menu-item" @click="phase = 'worlds'">← 返回世界列表</button>
          </div>
        </section>

        <section v-else key="courses" class="panel galgame-panel">
          <h2>课程选择 · {{ selectedWorld?.name }}</h2>
          <div class="list">
            <button v-for="course in courses" :key="course.id" class="item galgame-world-card" @click="startLearning(course.id)">
              <strong>{{ course.name }}</strong>
              <span>{{ course.description || '暂无描述' }}</span>
            </button>
          </div>
          <button class="back galgame-btn galgame-menu-item" @click="phase = 'memory'">← 返回回忆库</button>
        </section>
      </Transition>
      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    </div>
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

const router = useRouter()
const authStore = useAuthStore()
const phase = ref<'menu' | 'worlds' | 'memory' | 'courses'>('menu')
const worlds = ref<World[]>([])
const courses = ref<Course[]>([])
const selectedWorld = ref<World | null>(null)
const errorMessage = ref('')

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })

const sceneStyle = computed(() => {
  const scenes = selectedWorld.value?.scenes || {}
  const url = scenes.default || Object.values(scenes)[0]
  return url
    ? { backgroundImage: `url(${url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
    : {}
})

const showError = (error: unknown) => {
  errorMessage.value = parseApiError(error)
  setTimeout(() => (errorMessage.value = ''), 4000)
}

const fetchWorlds = async () => {
  try {
    const res = await axios.get('/api/worlds', { headers: headers() })
    worlds.value = res.data
  } catch (error) {
    showError(error)
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

const enterWorlds = async () => {
  await fetchWorlds()
  phase.value = 'worlds'
}

const selectWorld = async (world: World) => {
  selectedWorld.value = world
  phase.value = 'memory'
}

const enterCourses = async () => {
  await fetchCourses()
  phase.value = 'courses'
}

const startLearning = (courseId: number) => {
  router.push(buildLearningRoute(courseId, { worldId: selectedWorld.value?.id }))
}

const branchFromCheckpoint = async (checkpoint: { id: number; save_name: string }) => {
  try {
    const branchName = prompt('请输入分叉名称（可选）') || undefined
    const res = await axios.post(`/api/checkpoints/${checkpoint.id}/branch`, { branch_name: branchName }, { headers: headers() })
    router.push(buildLearningRoute(res.data.course_id, {
      worldId: res.data.world_id || selectedWorld.value?.id,
      sessionId: res.data.session_id,
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
.home-page { min-height: 100vh; position: relative; background: radial-gradient(ellipse at 50% 30%, #1a1a3e 0%, #0a0a1e 70%); }
.mask { position: absolute; inset: 0; background: rgba(8, 8, 20, 0.55); }
.content { position: relative; z-index: 1; min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 24px; }
.panel { width: 100%; max-width: 760px; padding: 24px; display: flex; flex-direction: column; gap: 12px; }
.panel.wide { max-width: 980px; }
h1,h2 { color: #ffd700; margin-bottom: 10px; }
.muted { color: #aaa; }
.list { display: flex; flex-direction: column; gap: 10px; max-height: 420px; overflow-y: auto; }
.item span { color: #999; font-size: 12px; }
.actions { display: flex; justify-content: space-between; gap: 10px; margin-top: 8px; }
.back { text-align: center; }
.error { position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: rgba(223,74,74,.9); padding: 8px 14px; border-radius: 6px; }
.fade-enter-active,.fade-leave-active { transition: transform .25s ease; }
.fade-enter-from,.fade-leave-to { transform: translateY(8px); }
</style>
