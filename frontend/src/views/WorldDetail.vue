<template>
  <div class="world-detail-page">
    <!-- Background -->
    <div class="scene-bg" :style="getWorldBgStyle(selectedWorld)"></div>
    <div class="scene-overlay"></div>

    <!-- Header -->
    <div class="char-header">
      <button class="back-btn" @click="router.push('/home/worlds')">
        <span>←</span> 返回
      </button>
      <h1 class="header-title">{{ selectedWorld?.name || '世界详情' }}</h1>
      <div class="header-actions">
        <button class="action-btn" @click="showEditWorld = true">
          <Edit3 :size="14" /> 编辑
        </button>
        <button class="action-btn action-btn-danger" @click="confirmDelete">
          <Trash2 :size="14" /> 删除
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="char-content">
      <!-- World Info Card -->
      <div v-if="selectedWorld" class="world-info-card" v-motion
        :initial="{ opacity: 0, y: -20 }"
        :enter="{ opacity: 1, y: 0 }"
      >
        <div class="world-avatar" :style="{ background: selectedWorld.sages?.[0]?.color || 'rgba(255,215,0,0.2)' }">
          {{ selectedWorld.symbol || selectedWorld.sages?.[0]?.symbol || '?' }}
        </div>
        <div class="world-info">
          <div class="world-name">{{ selectedWorld.name }}</div>
          <div class="world-desc">{{ selectedWorld.description || '暂无描述' }}</div>
        </div>
      </div>

      <!-- Travelers Section -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">旅 者</span>
          <span class="section-sublabel">TRAVELERS</span>
        </div>
        <div class="section-line"></div>
        <div class="traveler-row">
          <div class="traveler-card" v-if="currentTraveler" @click="handleEditTraveler(currentTraveler)">
            <div class="traveler-avatar" :style="{ background: currentTraveler.color || 'rgba(96,165,250,0.35)' }">
              {{ currentTraveler.name?.[0] || '?' }}
            </div>
            <div class="traveler-info">
              <div class="traveler-name">{{ currentTraveler.name }}</div>
              <div class="traveler-title">{{ currentTraveler.title || '旅者' }}</div>
            </div>
          </div>
          <div v-else class="traveler-empty">
            尚未设置旅者身份
          </div>
          <button class="traveler-switch-btn" @click="showTravelerSelect = true">
            切换旅者 ▼
          </button>
        </div>
      </div>

      <!-- Sages Section -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">知 者</span>
          <span class="section-sublabel">SAGES</span>
        </div>
        <div class="section-line"></div>
        <div class="char-grid">
          <div
            v-for="(sage, idx) in selectedWorld?.sages || []"
            :key="sage.id"
            class="sage-card"
            :style="{ animationDelay: `${idx * 0.1}s` }"
            @click="handleEditSage(sage)"
          >
            <div class="sage-avatar" :style="{ background: sage.color }">
              {{ sage.symbol || '?' }}
            </div>
            <div class="sage-info">
              <div class="sage-name">{{ sage.name }}</div>
              <div v-if="sage.title" class="sage-title">{{ sage.title }}</div>
            </div>
            <div class="card-actions">
              <button class="card-action-btn" @click.stop="handleEditSage(sage)">
                <Edit3 :size="12" />
              </button>
              <button class="card-action-btn card-action-delete" @click.stop="confirmDeleteSage(sage)">
                <Trash2 :size="12" />
              </button>
            </div>
          </div>
          <!-- Add sage button -->
          <div class="add-card" @click="showSageSelect = true">
            <div class="add-icon">+</div>
            <div class="add-text">添加知者</div>
          </div>
        </div>
      </div>

      <!-- Courses Section -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">课 程</span>
          <span class="section-sublabel">COURSES</span>
        </div>
        <div class="section-line"></div>
        <div v-if="loading" class="loading-text">加载中…</div>
        <div v-else class="courses-list">
          <div
            v-for="(course, i) in courses"
            :key="course.id"
            class="course-item"
            :style="{ animationDelay: `${i * 0.1}s` }"
            @click="startLearning(course.id)"
          >
            <div class="course-icon">{{ course.icon || '📚' }}</div>
            <div class="course-info">
              <div class="course-name">{{ course.name }}</div>
              <div class="course-desc">{{ course.description || '暂无描述' }}</div>
              <div v-if="course.progress && course.progress > 0" class="course-progress">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: `${course.progress * 100}%` }"></div>
                </div>
                <span class="progress-text">{{ Math.round(course.progress * 100) }}%</span>
              </div>
            </div>
            <div class="course-arrow">▸</div>
          </div>
          <!-- Add course button -->
          <div class="add-card add-card-course" @click="showCreateCourse = true">
            <div class="add-icon">+</div>
            <div class="add-text">创建课程</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Toast -->
    <p v-if="errorMessage" class="error-toast font-ui">{{ errorMessage }}</p>

    <!-- Create Course Modal -->
    <CreateCourseModal
      :show="showCreateCourse"
      :world-id="worldId"
      @close="showCreateCourse = false"
      @create="handleCreateCourse"
    />

    <!-- Create Persona Modal -->
    <CreatePersonaModal
      :show="showCreatePersona"
      :world-id="worldId"
      :character-type="'sage'"
      @close="showCreatePersona = false"
      @create="handleCreatePersona"
    />

    <!-- Step Create Modal (for Traveler or Sage) -->
    <StepCreateModal
      :show="showStepCreate"
      :default-type="stepCreateDefaultType"
      :world-id="worldId"
      @close="showStepCreate = false"
      @create="handleStepCreate"
    />

    <!-- Edit World Modal -->
    <div v-if="showEditWorld" class="modal-overlay" @click.self="showEditWorld = false">
      <div class="edit-world-modal">
        <div class="modal-title">编辑世界</div>
        <div class="modal-body">
          <div class="form-group">
            <label>世界名称</label>
            <input v-model="editWorldForm.name" type="text" placeholder="世界名称" />
          </div>
          <div class="form-group">
            <label>世界描述</label>
            <textarea v-model="editWorldForm.description" placeholder="世界描述" rows="3"></textarea>
          </div>
          <div class="form-group">
            <label>世界符号</label>
            <input v-model="editWorldForm.symbol" type="text" placeholder="如 🏛️" maxlength="2" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showEditWorld = false">取消</button>
          <button class="btn-confirm" @click="handleUpdateWorld">保存</button>
        </div>
      </div>
    </div>

    <!-- Traveler Select Modal -->
    <div v-if="showTravelerSelect" class="modal-overlay" @click.self="showTravelerSelect = false">
      <div class="select-traveler-modal">
        <div class="modal-title">选择旅者身份</div>
        <div class="traveler-list">
          <div
            v-for="traveler in availableTravelers"
            :key="traveler.id"
            class="traveler-option"
            :class="{ active: currentTraveler?.id === traveler.id }"
            @click="selectTraveler(traveler)"
          >
            <div class="traveler-avatar-sm" :style="{ background: traveler.color }">
              {{ traveler.name?.[0] || '?' }}
            </div>
            <div class="traveler-option-info">
              <div class="traveler-option-name">{{ traveler.name }}</div>
              <div class="traveler-option-title">{{ traveler.title || '旅者' }}</div>
            </div>
            <div v-if="currentTraveler?.id === traveler.id" class="traveler-check">✓</div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-add" @click="openStepCreate('traveler')">
            + 添加新旅者
          </button>
          <button class="btn-cancel" @click="showTravelerSelect = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- Sage Select Modal -->
    <div v-if="showSageSelect" class="modal-overlay" @click.self="showSageSelect = false">
      <div class="select-traveler-modal">
        <div class="modal-title">添加知者</div>
        <div class="traveler-list">
          <div
            v-for="sage in availableSages"
            :key="sage.id"
            class="traveler-option"
            @click="selectSage(sage)"
          >
            <div class="traveler-avatar-sm" :style="{ background: sage.color || '#ffd700' }">
              {{ sage.symbol || sage.name?.[0] || '?' }}
            </div>
            <div class="traveler-option-info">
              <div class="traveler-option-name">{{ sage.name }}</div>
              <div class="traveler-option-title">{{ sage.title || '知者' }}</div>
            </div>
          </div>
          <div v-if="availableSages.length === 0" class="traveler-empty" style="text-align: center; padding: 20px; color: rgba(255,255,255,0.4);">
            暂无未关联的知者
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-add" @click="openStepCreate('sage')">
            + 创建新知者
          </button>
          <button class="btn-cancel" @click="showSageSelect = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- Delete World Confirmation -->
    <Transition name="modal-fade">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="confirm-dialog">
          <div class="confirm-icon">⚠</div>
          <div class="confirm-title">确认删除</div>
          <div class="confirm-message">
            确定要删除世界 <span class="confirm-name">{{ selectedWorld?.name }}</span> 吗？<br />
            此操作无法撤销。
          </div>
          <div class="confirm-actions">
            <button class="btn-cancel" @click="showDeleteConfirm = false">取消</button>
            <button class="btn-confirm btn-confirm-danger" @click="handleDeleteWorld">确认删除</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Edit3, Trash2 } from 'lucide-vue-next'
import client from '@/api/client'

import { parseApiError } from '@/utils/error'
import CreateCourseModal from '@/components/CreateCourseModal.vue'
import CreatePersonaModal from '@/components/CreatePersonaModal.vue'
import StepCreateModal from '@/components/StepCreateModal.vue'

const route = useRoute()
const router = useRouter()

interface Character {
  id: number
  name: string
  title?: string
  avatar?: string
  type: 'sage' | 'traveler'
  color?: string
  symbol?: string
}

interface World {
  id: number
  name: string
  description?: string
  symbol?: string
  scenes?: { background?: string }
  sages?: Character[]
  travelers?: Character[]
}

interface Course {
  id: number
  name: string
  description?: string
  icon?: string
  progress?: number
}

const worldId = computed(() => Number(route.params.worldId))

const selectedWorld = ref<World | null>(null)
const courses = ref<Course[]>([])
const allCharacters = ref<Character[]>([])
const errorMessage = ref('')
const loading = ref(false)

// Modal states
const showCreateCourse = ref(false)
const showCreatePersona = ref(false)
const showStepCreate = ref(false)
const stepCreateDefaultType = ref<'sage' | 'traveler'>('traveler')
const showEditWorld = ref(false)
const showTravelerSelect = ref(false)
const showSageSelect = ref(false)
const showDeleteConfirm = ref(false)

// Mock characters for fallback (matching database IDs for user_id=2)
const MOCK_CHARACTERS: Character[] = [
  { id: 10, name: '苏格拉底', title: '哲学之父', type: 'sage', color: 'rgba(245, 158, 11, 0.35)' },
  { id: 11, name: '柏拉图', title: '理念论者', type: 'sage', color: 'rgba(139, 92, 246, 0.35)' },
  { id: 12, name: '亚里士多德', title: '百科全书', type: 'sage', color: 'rgba(16, 185, 129, 0.35)' },
  { id: 13, name: '孙子', title: '兵圣', type: 'sage', color: 'rgba(220, 38, 38, 0.35)' },
  { id: 110, name: '旅者', title: '求知者', type: 'traveler', color: 'rgba(59, 130, 246, 0.35)' },
  { id: 111, name: '行者', title: '探索者', type: 'traveler', color: 'rgba(6, 182, 212, 0.35)' },
]

// Edit forms
const editWorldForm = ref({
  name: '',
  description: '',
  symbol: ''
})

// Current traveler (primary traveler for this world)
const currentTraveler = computed(() => {
  return selectedWorld.value?.travelers?.[0] || null
})

// Available travelers (all travelers not linked to this world, type='traveler')
const availableTravelers = computed(() => {
  const linkedIds = new Set(selectedWorld.value?.travelers?.map(t => t.id) || [])
  return allCharacters.value.filter(c => c.type === 'traveler' && !linkedIds.has(c.id))
})

// Available sages (all sages not linked to this world)
const availableSages = computed(() => {
  const linkedIds = new Set(selectedWorld.value?.sages?.map(s => s.id) || [])
  return allCharacters.value.filter(c => c.type === 'sage' && !linkedIds.has(c.id))
})

// Background style
const getWorldBgStyle = (world: World | null) => {
  if (!world) return { background: 'linear-gradient(135deg, #1e3a5f, #4c1d95)' }
  const url = world.scenes?.background
  return url ? { backgroundImage: `url(${url})` } : { background: 'linear-gradient(135deg, #1e3a5f, #4c1d95)' }
}

// Error handler
const showError = (error: unknown) => {
  errorMessage.value = parseApiError(error)
  setTimeout(() => (errorMessage.value = ''), 4000)
}

// Fetch world data
const fetchWorld = async () => {
  try {
    const { data } = await client.get(`/worlds/${worldId.value}`)
    selectedWorld.value = data
    // Initialize edit form
    editWorldForm.value = {
      name: data.name || '',
      description: data.description || '',
      symbol: data.symbol || ''
    }
  } catch (error) {
    showError(error)
  }
}

// Fetch courses
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

// Fetch all characters
const fetchCharacters = async () => {
  try {
    const { data } = await client.get('/character')
    console.log('[DEBUG] fetchCharacters API result:', data)
    // Use MOCK_CHARACTERS as fallback if API returns empty
    allCharacters.value = (data && data.length > 0) ? data : MOCK_CHARACTERS
    console.log('[DEBUG] allCharacters after fetch:', allCharacters.value.length)
  } catch (error) {
    console.error('[DEBUG] fetchCharacters error:', error)
    allCharacters.value = MOCK_CHARACTERS
    showError(error)
  }
}

// Create sage persona
const handleCreatePersona = async (data: Record<string, any>) => {
  try {
    const { data: newCharacter } = await client.post('/character', data)
    await client.post(`/worlds/${worldId.value}/characters`, {
      character_id: newCharacter.id,
      role: 'sage',
      is_primary: !selectedWorld.value?.sages?.length,
    })
    await fetchWorld()
    showCreatePersona.value = false
  } catch (error) {
    showError(error)
  }
}

// Edit sage
const handleEditSage = (sage: Character) => {
  console.log('Edit sage:', sage)
  // TODO: Open edit modal for sage
}

// Edit traveler
const handleEditTraveler = (traveler: Character) => {
  console.log('Edit traveler:', traveler)
  // TODO: Open edit modal for traveler
}

// Select traveler
const selectTraveler = async (traveler: Character) => {
  try {
    // Set as primary traveler for this world
    await client.put(`/worlds/${worldId.value}/characters/${traveler.id}/set-primary`)
    await fetchWorld()
    showTravelerSelect.value = false
  } catch (error) {
    showError(error)
  }
}

// Select sage (link existing sage to this world)
const selectSage = async (sage: Character) => {
  try {
    await client.post(`/worlds/${worldId.value}/characters`, {
      character_id: sage.id,
      role: 'sage',
      is_primary: !selectedWorld.value?.sages?.length,
    })
    await fetchWorld()
    await fetchCharacters()
    showSageSelect.value = false
  } catch (error) {
    showError(error)
  }
}

// Confirm delete sage
const confirmDeleteSage = async (sage: Character) => {
  try {
    await client.delete(`/worlds/${worldId.value}/characters/${sage.id}`)
    await fetchWorld()
  } catch (error) {
    showError(error)
  }
}

// Update world
const handleUpdateWorld = async () => {
  try {
    await client.put(`/worlds/${worldId.value}`, {
      name: editWorldForm.value.name,
      description: editWorldForm.value.description,
      symbol: editWorldForm.value.symbol,
    })
    await fetchWorld()
    showEditWorld.value = false
  } catch (error) {
    showError(error)
  }
}

// Confirm delete world
const confirmDelete = () => {
  showDeleteConfirm.value = true
}

// Delete world
const handleDeleteWorld = async () => {
  try {
    await client.delete(`/worlds/${worldId.value}`)
    router.push('/home/worlds')
  } catch (error) {
    showError(error)
    showDeleteConfirm.value = false
  }
}

// Create course
const handleCreateCourse = async (data: {
  name: string
  description: string
  target_level: string
  meta: Record<string, any>
}) => {
  try {
    const { data: newCourse } = await client.post(`/worlds/${worldId.value}/courses`, {
      name: data.name,
      description: data.description,
      target_level: data.target_level,
      meta: data.meta,
    })
    courses.value = [...courses.value, newCourse]
    showCreateCourse.value = false
  } catch (error) {
    showError(error)
  }
}

// Start learning
const startLearning = (courseId: number) => {
  router.push({
    path: `/home/worlds/${worldId.value}/courses/${courseId}`,
    query: { from: 'new' }
  })
}

// Open step create modal
const openStepCreate = (type: 'sage' | 'traveler') => {
  stepCreateDefaultType.value = type
  showStepCreate.value = true
  showTravelerSelect.value = false
}

// Handle step create (from StepCreateModal)
const handleStepCreate = async (data: Record<string, any>) => {
  try {
    const role = data.type === 'traveler' ? 'traveler' : 'sage'
    const { data: newCharacter } = await client.post('/character', data)
    await client.post(`/worlds/${worldId.value}/characters`, {
      character_id: newCharacter.id,
      role,
      is_primary: role === 'traveler' 
        ? !selectedWorld.value?.travelers?.length 
        : !selectedWorld.value?.sages?.length,
    })
    await fetchWorld()
    showStepCreate.value = false
  } catch (error) {
    showError(error)
  }
}

onMounted(async () => {
  await fetchWorld()
  await fetchCourses()
  await fetchCharacters()
})
</script>

<style scoped>
.world-detail-page {
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
  transition: background-image 0.8s ease;
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

/* Header - matching Character.vue */
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

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
}

.action-btn-danger:hover {
  background: rgba(220, 38, 38, 0.2);
  border-color: rgba(220, 38, 38, 0.5);
  color: #ef4444;
}

/* Content */
.char-content {
  position: relative;
  z-index: 1;
  max-width: 900px;
  margin: 0 auto;
  padding: 32px;
}

/* World Info Card */
.world-info-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 16px;
  margin-bottom: 40px;
}

.world-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  border: 2px solid rgba(255, 215, 0, 0.4);
  flex-shrink: 0;
}

.world-info {
  flex: 1;
}

.world-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 22px;
  color: #ffd700;
  letter-spacing: 4px;
  margin-bottom: 8px;
}

.world-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.6;
}

/* Section Group */
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

/* Traveler Section */
.traveler-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.traveler-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(96, 165, 250, 0.1);
  border: 1px solid rgba(96, 165, 250, 0.3);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.traveler-card:hover {
  background: rgba(96, 165, 250, 0.15);
  border-color: rgba(96, 165, 250, 0.5);
}

.traveler-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.traveler-info {
  text-align: left;
}

.traveler-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 15px;
  color: #fff;
  margin-bottom: 2px;
}

.traveler-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(96, 165, 250, 0.8);
}

.traveler-empty {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
  padding: 16px 20px;
}

.traveler-switch-btn {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.traveler-switch-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
}

/* Character Grid */
.char-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.sage-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  background: rgba(8, 8, 28, 0.9);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  animation: cardEntry 0.4s ease backwards;
}

.sage-card:hover {
  border-color: rgba(255, 215, 0, 0.5);
  transform: translateY(-2px);
}

.sage-card:hover .card-actions {
  opacity: 1;
}

.card-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.card-action-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  border: none;
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
}

.card-action-btn:hover {
  background: rgba(255, 215, 0, 0.2);
  color: #ffd700;
}

.card-action-delete:hover {
  background: rgba(220, 38, 38, 0.2);
  color: #ef4444;
}

.sage-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  border: 2px solid rgba(255, 215, 0, 0.3);
}

.sage-info {
  text-align: center;
}

.sage-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #ffd700;
  margin-bottom: 4px;
}

.sage-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

/* Add Card */
.add-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 140px;
  height: 160px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed rgba(255, 215, 0, 0.25);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  animation: cardEntry 0.4s ease backwards;
  animation-delay: 0.3s;
}

.add-card:hover {
  background: rgba(255, 215, 0, 0.05);
  border-color: rgba(255, 215, 0, 0.5);
  transform: translateY(-2px);
}

.add-card-course {
  width: 100%;
  height: auto;
  padding: 16px;
  flex-direction: row;
  gap: 12px;
}

.add-icon {
  font-size: 28px;
  color: rgba(255, 215, 0, 0.4);
  margin-bottom: 8px;
}

.add-card-course .add-icon {
  margin-bottom: 0;
}

.add-text {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 215, 0, 0.4);
  letter-spacing: 2px;
}

/* Courses List */
.courses-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.course-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: rgba(8, 8, 28, 0.9);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  animation: cardEntry 0.4s ease backwards;
}

.course-item:hover {
  border-color: rgba(255, 215, 0, 0.5);
  transform: translateX(8px);
}

.course-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.course-info {
  flex: 1;
}

.course-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 15px;
  color: #ffd700;
  margin-bottom: 4px;
}

.course-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
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
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #4adf6a);
  transition: width 0.3s ease;
}

.progress-text {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: #4adf6a;
}

.course-arrow {
  color: rgba(255, 215, 0, 0.4);
  font-size: 18px;
}

.loading-text {
  font-family: "Noto Sans SC", sans-serif;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
  margin-top: 32px;
}

@keyframes cardEntry {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.edit-world-modal,
.select-traveler-modal {
  width: 420px;
  max-width: 90vw;
  padding: 28px;
  background: rgba(12, 12, 30, 0.98);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 18px;
  color: #ffd700;
  letter-spacing: 4px;
  text-align: center;
  margin-bottom: 24px;
}

.modal-body {
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 6px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px 14px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s ease;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: rgba(255, 215, 0, 0.5);
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-cancel,
.btn-confirm,
.btn-add {
  padding: 10px 20px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  letter-spacing: 2px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-cancel {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.7);
}

.btn-cancel:hover {
  border-color: rgba(255, 255, 255, 0.4);
  color: white;
}

.btn-confirm {
  background: rgba(255, 215, 0, 0.9);
  border: none;
  color: #0a0a1e;
  font-weight: 600;
}

.btn-confirm:hover {
  background: #ffd700;
}

.btn-confirm-danger {
  background: rgba(220, 38, 38, 0.9);
  color: #fff;
}

.btn-confirm-danger:hover {
  background: #dc2626;
}

.btn-add {
  flex: 1;
  background: rgba(255, 215, 0, 0.1);
  border: 1px dashed rgba(255, 215, 0, 0.3);
  color: rgba(255, 215, 0, 0.7);
}

.btn-add:hover {
  background: rgba(255, 215, 0, 0.15);
  border-color: rgba(255, 215, 0, 0.5);
}

/* Traveler Select Modal */
.traveler-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.traveler-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.traveler-option:hover {
  background: rgba(255, 255, 255, 0.05);
}

.traveler-option.active {
  background: rgba(96, 165, 250, 0.1);
}

.traveler-avatar-sm {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  flex-shrink: 0;
}

.traveler-option-info {
  flex: 1;
  text-align: left;
}

.traveler-option-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: #fff;
}

.traveler-option-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.traveler-check {
  color: #4adf6a;
  font-size: 16px;
}

/* Confirm Dialog */
.confirm-dialog {
  width: 360px;
  max-width: 90vw;
  padding: 32px;
  background: rgba(12, 12, 30, 0.98);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.confirm-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.confirm-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 20px;
  color: #ffd700;
  margin-bottom: 12px;
}

.confirm-message {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
  margin-bottom: 24px;
}

.confirm-name {
  color: #ffd700;
  font-weight: 600;
}

.confirm-actions {
  display: flex;
  gap: 12px;
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
}

/* Modal Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
