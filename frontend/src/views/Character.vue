<template>
  <div class="char-page-v2">
    <!-- Background -->
    <div class="bg-image" :style="{ backgroundImage: `url(${BG_URL})` }"></div>
    <div class="bg-gradient"></div>
    <ParticleBackground :count="20" :gold-ratio="0.5" />

    <!-- Header -->
    <div class="char-header font-ui">
      <button class="galgame-hud-btn" @click="router.push('/home')">
        <span>←</span> 返回
      </button>
      <span class="header-title">角 色 管 理</span>
      <div style="width:80px;"></div>
    </div>

    <!-- Content -->
    <div class="char-content galgame-scrollbar">
      <div class="char-inner">

        <!-- Stats summary -->
        <div class="stats-row">
          <div class="stat-card galgame-panel">
            <div class="stat-value">{{ stats.total_sessions }}</div>
            <div class="stat-label font-ui">总学习次数</div>
          </div>
          <div class="stat-card galgame-panel">
            <div class="stat-value">{{ stats.total_diary }}</div>
            <div class="stat-label font-ui">学习日记</div>
          </div>
          <div class="stat-card galgame-panel">
            <div class="stat-value">{{ stats.mastery }}%</div>
            <div class="stat-label font-ui">平均掌握度</div>
          </div>
          <div class="stat-card galgame-panel">
            <div class="stat-value">{{ stats.streak }}天</div>
            <div class="stat-label font-ui">连续学习</div>
          </div>
        </div>

        <!-- Characters grid -->
        <div class="section-header">
          <span class="font-ui section-title">我的角色</span>
          <button class="galgame-hud-btn" @click="showCreate = true; createName = ''; createDesc = ''">
            ✚ 创建角色
          </button>
        </div>

        <!-- Create form -->
        <Transition name="slide-down">
          <div v-if="showCreate" class="create-form galgame-panel">
            <div class="form-row">
              <input
                v-model="createName"
                class="galgame-input font-ui"
                placeholder="角色名称"
                maxlength="20"
              />
              <button class="galgame-send-btn" @click="createCharacter">创建</button>
              <button class="galgame-hud-btn" @click="showCreate = false">取消</button>
            </div>
            <textarea
              v-model="createDesc"
              class="galgame-input font-dialogue create-desc"
              placeholder="角色描述（选填）..."
              rows="2"
            ></textarea>
            <p v-if="createError" class="font-ui error-text">{{ createError }}</p>
          </div>
        </Transition>

        <!-- Loading -->
        <div v-if="loading" class="loading-text">加载中…</div>

        <!-- Empty state -->
        <div v-else-if="characters.length === 0" class="empty-state">
          <p class="font-dialogue empty-hint">「还没有创建任何角色。」</p>
          <p class="font-ui empty-sub">点击上方「创建角色」开始吧</p>
        </div>

        <!-- Character cards -->
        <div v-else class="char-grid">
          <div
            v-for="char in characters"
            :key="char.id"
            class="char-card"
            :class="{ selected: selectedId === char.id }"
            @click="selectedId = selectedId === char.id ? null : char.id"
          >
            <!-- Avatar area -->
            <div class="char-avatar" :style="{ background: avatarGradient(char) }">
              <div v-if="char.avatar_url" class="char-avatar-img">
                <img :src="char.avatar_url" :alt="char.name" />
              </div>
              <div v-else class="char-avatar-placeholder">
                {{ char.name.charAt(0) }}
              </div>
            </div>

            <!-- Info -->
            <div class="char-info">
              <div class="font-ui char-name">{{ char.name }}</div>
              <div v-if="char.description" class="font-ui char-desc">{{ char.description }}</div>
              <div class="font-ui char-meta">
                Lv.{{ char.level || 1 }} · 经验 {{ char.exp || 0 }}
              </div>
            </div>

            <!-- Expanded actions -->
            <Transition name="expand">
              <div v-if="selectedId === char.id" class="char-actions">
                <!-- Avatar upload -->
                <div class="avatar-upload">
                  <label class="galgame-hud-btn upload-btn">
                    📷 上传立绘
                    <input
                      type="file"
                      accept="image/*"
                      style="display:none;"
                      @change="handleAvatarUpload($event, char.id)"
                    />
                  </label>
                  <span v-if="uploadProgress[char.id]" class="font-ui upload-progress">
                    {{ uploadProgress[char.id] }}%
                  </span>
                </div>
                <!-- Level up -->
                <button
                  class="galgame-send-btn levelup-btn"
                  :disabled="!canLevelUp(char)"
                  @click.stop="levelUp(char.id)"
                >
                  ⭐ 升级
                </button>
                <!-- Delete -->
                <button class="galgame-hud-btn delete-btn" @click.stop="deleteCharacter(char.id)">
                  🗑 删除
                </button>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'
import ParticleBackground from '@/components/ParticleBackground.vue'

const router = useRouter()
const authStore = useAuthStore()

const BG_URL = 'https://images.unsplash.com/photo-1534796636912-3b95b3ab5986?w=1920&q=80'

interface Character {
  id: number
  name: string
  description?: string
  avatar_url?: string
  level?: number
  exp?: number
}

interface Stats {
  total_sessions: number
  total_diary: number
  mastery: number
  streak: number
}

const characters = ref<Character[]>([])
const stats = reactive<Stats>({ total_sessions: 0, total_diary: 0, mastery: 0, streak: 0 })
const selectedId = ref<number | null>(null)
const showCreate = ref(false)
const createName = ref('')
const createDesc = ref('')
const createError = ref('')
const loading = ref(false)
const uploadProgress = reactive<Record<number, number>>({})

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })

const avatarGradient = (char: Character) => {
  const hues = [200, 260, 320, 180, 40]
  const hue = hues[char.id % hues.length]
  return `linear-gradient(135deg, hsl(${hue},60%,25%), hsl(${hue+40},50%,15%))`
}

const canLevelUp = (char: Character) => {
  return (char.exp || 0) >= 100
}

const fetchCharacters = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/characters', { headers: headers() })
    characters.value = res.data
  } catch (error) {
    console.error(parseApiError(error))
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const res = await axios.get('/api/characters/stats', { headers: headers() })
    Object.assign(stats, res.data)
  } catch {}
}

const createCharacter = async () => {
  if (!createName.value.trim()) { createError.value = '请输入角色名'; return }
  createError.value = ''
  try {
    const res = await axios.post('/api/characters', {
      name: createName.value.trim(),
      description: createDesc.value.trim() || undefined,
    }, { headers: headers() })
    characters.value.unshift(res.data)
    showCreate.value = false
    createName.value = ''
    createDesc.value = ''
  } catch (e: any) {
    createError.value = e?.response?.data?.detail ?? '创建失败'
  }
}

const handleAvatarUpload = async (event: Event, charId: number) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  uploadProgress[charId] = 0
  try {
    const res = await axios.post(`/api/characters/${charId}/avatar`, formData, {
      headers: { ...headers(), 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) uploadProgress[charId] = Math.round((e.loaded * 100) / e.total)
      },
    })
    const char = characters.value.find(c => c.id === charId)
    if (char) char.avatar_url = res.data.avatar_url
  } catch (e) {
    console.error(parseApiError(e))
  } finally {
    delete uploadProgress[charId]
  }
}

const levelUp = async (charId: number) => {
  try {
    const res = await axios.post(`/api/characters/${charId}/levelup`, {}, { headers: headers() })
    const char = characters.value.find(c => c.id === charId)
    if (char) Object.assign(char, res.data)
  } catch (e) {
    console.error(parseApiError(e))
  }
}

const deleteCharacter = async (charId: number) => {
  if (!confirm('确定删除该角色？')) return
  try {
    await axios.delete(`/api/characters/${charId}`, { headers: headers() })
    characters.value = characters.value.filter(c => c.id !== charId)
    if (selectedId.value === charId) selectedId.value = null
  } catch (e) {
    console.error(parseApiError(e))
  }
}

onMounted(async () => {
  await Promise.all([fetchCharacters(), fetchStats()])
})
</script>

<style scoped>
.char-page-v2 {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #0a0a1e;
}

.bg-image {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.08;
}

.bg-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(10,10,30,0.95) 0%, rgba(10,10,30,0.98) 100%);
}

.char-header {
  position: absolute;
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

.char-header button {
  font-size: 13px;
  padding: 6px 14px;
}

.header-title {
  color: #ffd700;
  font-size: 16px;
  letter-spacing: 4px;
}

.char-content {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  padding-top: 68px;
  padding-bottom: 32px;
  padding-left: 24px;
  padding-right: 24px;
}

.char-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-card {
  padding: 16px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #ffd700;
  letter-spacing: 2px;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  letter-spacing: 1px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  color: #ffd700;
  font-size: 14px;
  letter-spacing: 2px;
}

.create-form {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.form-row input {
  flex: 1;
  padding: 8px 12px;
  font-size: 13px;
}

.create-desc {
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  resize: none;
}

.error-text {
  font-size: 12px;
  color: #ef4444;
}

.loading-text {
  color: rgba(255,255,255,0.5);
  text-align: center;
  padding: 40px;
}

.empty-state {
  text-align: center;
  padding: 40px;
}

.empty-hint {
  font-size: 18px;
  color: rgba(255,255,255,0.5);
  margin-bottom: 8px;
}

.empty-sub {
  font-size: 12px;
  color: rgba(255,255,255,0.3);
}

.char-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.char-card {
  background: rgba(0,0,0,0.5);
  border: 1px solid rgba(255,215,0,0.1);
  border-radius: var(--radius-panel);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
}

.char-card:hover {
  border-color: rgba(255,215,0,0.3);
  transform: translateY(-2px);
}

.char-card.selected {
  border-color: rgba(255,215,0,0.5);
  box-shadow: 0 0 16px rgba(255,215,0,0.15);
}

.char-avatar {
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.char-avatar-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.char-avatar-placeholder {
  font-size: 48px;
  font-weight: bold;
  color: rgba(255,255,255,0.3);
}

.char-info {
  padding: 12px;
}

.char-name {
  font-size: 15px;
  color: #f0f0ff;
  letter-spacing: 2px;
  margin-bottom: 4px;
}

.char-desc {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
  line-height: 1.4;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.char-meta {
  font-size: 11px;
  color: rgba(255,215,0,0.5);
}

.char-actions {
  padding: 12px;
  border-top: 1px solid rgba(255,215,0,0.1);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.avatar-upload {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-btn {
  font-size: 12px;
  padding: 4px 10px;
}

.upload-progress {
  font-size: 11px;
  color: rgba(255,215,0,0.5);
}

.levelup-btn {
  font-size: 12px;
  padding: 6px;
}

.delete-btn {
  font-size: 12px;
  padding: 4px 10px;
  color: rgba(255,100,100,0.7);
}

.slide-down-enter-from {
  opacity: 0;
  transform: translateY(-12px);
}

.slide-down-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.slide-down-leave-active {
  transition: opacity 0.2s ease;
}

.expand-enter-from {
  opacity: 0;
  max-height: 0;
}

.expand-enter-active {
  transition: opacity 0.25s ease, max-height 0.25s ease;
  max-height: 200px;
}

.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-leave-active {
  transition: opacity 0.2s ease, max-height 0.2s ease;
}
</style>
