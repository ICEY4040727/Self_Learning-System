<template>
  <div class="char-page">
    <!-- Background -->
    <div class="scene-bg" :style="{ backgroundImage: `url(${BG_URL})` }"></div>
    <div class="scene-overlay"></div>

    <!-- Header -->
    <div class="char-header">
      <button class="back-btn" @click="router.push('/home')">
        <span>←</span> 返回
      </button>
      <h1 class="header-title">角 色 管 理</h1>
      <div style="width: 80px;"></div>
    </div>

    <!-- Content -->
    <div class="char-content">
      <!-- Sages Section -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">知 者</span>
          <span class="section-sublabel">SAGES</span>
        </div>
        <div class="section-line"></div>
        <div class="char-grid">
          <CharacterCard
            v-for="(sage, idx) in sages"
            :key="sage.id"
            :name="sage.name"
            :title="sage.title"
            :avatar="sage.avatar"
            type="sage"
            :is-builtin="sage.is_builtin"
            :color="sage.color"
            :style="{ animationDelay: `${idx * 0.1}s` }"
            @click="handleCardClick(sage)"
            @edit="handleEdit(sage)"
            @delete="confirmDelete(sage)"
          />
          <!-- Add sage button -->
          <div class="add-card" @click="handleAddCharacter('sage')">
            <div class="add-icon">+</div>
            <div class="add-text">添加知者</div>
          </div>
        </div>
      </div>

      <!-- Travelers Section -->
      <div class="section-group">
        <div class="section-header">
          <span class="section-label">旅 者</span>
          <span class="section-sublabel">TRAVELERS</span>
        </div>
        <div class="section-line"></div>
        <div class="char-grid">
          <CharacterCard
            v-for="(traveler, idx) in travelers"
            :key="traveler.id"
            :name="traveler.name"
            :title="traveler.title"
            :avatar="traveler.avatar"
            type="traveler"
            :is-builtin="traveler.is_builtin"
            :color="traveler.color"
            :style="{ animationDelay: `${(sages.length + idx) * 0.1}s` }"
            @click="handleCardClick(traveler)"
            @edit="handleEdit(traveler)"
            @delete="confirmDelete(traveler)"
          />
          <!-- Add traveler button -->
          <div class="add-card" @click="handleAddCharacter('traveler')">
            <div class="add-icon">+</div>
            <div class="add-text">添加旅者</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <StepCreateModal
      :show="showModal"
      :default-type="modalType"
      @close="showModal = false"
      @create="handleCreate"
    />

    <!-- Edit Modal -->
    <EditCharacterModal
      :show="showEditModal"
      :character="editingCharacter"
      @close="showEditModal = false"
      @update="handleUpdate"
    />

    <!-- Delete Confirmation Dialog -->
    <Transition name="modal-fade">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="confirm-dialog">
          <div class="confirm-icon">⚠</div>
          <div class="confirm-title">确认删除</div>
          <div class="confirm-message">
            确定要删除角色 <span class="confirm-name">{{ deleteTarget?.name }}</span> 吗？<br />
            此操作无法撤销。
          </div>
          <div class="confirm-actions">
            <button class="btn-cancel" @click="showDeleteConfirm = false">取消</button>
            <button class="btn-confirm" @click="handleDelete">确认删除</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '@/api/client'
import CharacterCard from '@/components/CharacterCard.vue'
import StepCreateModal from '@/components/StepCreateModal.vue'
import EditCharacterModal from '@/components/EditCharacterModal.vue'

const router = useRouter()

const COLORS = [
  'rgba(245, 158, 11, 0.35)',
  'rgba(139, 92, 246, 0.35)',
  'rgba(16, 185, 129, 0.35)',
  'rgba(220, 38, 38, 0.35)',
  'rgba(59, 130, 246, 0.35)',
  'rgba(6, 182, 212, 0.35)',
]

interface Character {
  id: number
  name: string
  title?: string
  description?: string
  avatar?: string
  type: 'sage' | 'traveler'
  is_builtin: boolean
  color?: string
  tags?: string[]
  personality?: string
}

import charBg from '@/assets/char-bg.jpg'

const BG_URL = charBg

const characters = ref<Character[]>([])
const loading = ref(false)
const showModal = ref(false)
const showEditModal = ref(false)
const modalType = ref<'sage' | 'traveler'>('sage')
const editingCharacter = ref<Character | null>(null)

// Delete confirmation
const showDeleteConfirm = ref(false)
const deleteTarget = ref<Character | null>(null)

// Mock data for preview
const MOCK_CHARACTERS: Character[] = [
  { id: 1, name: '苏格拉底', title: '哲学之父', type: 'sage', is_builtin: true, color: COLORS[0] },
  { id: 2, name: '柏拉图', title: '理念论者', type: 'sage', is_builtin: true, color: COLORS[1] },
  { id: 3, name: '亚里士多德', title: '百科全书', type: 'sage', is_builtin: true, color: COLORS[2] },
  { id: 4, name: '孙子', title: '兵圣', type: 'sage', is_builtin: true, color: COLORS[3] },
  { id: 101, name: '旅者', title: '求知者', type: 'traveler', is_builtin: true, color: COLORS[4] },
  { id: 102, name: '行者', title: '探索者', type: 'traveler', is_builtin: true, color: COLORS[5] },
]

const sages = computed(() => characters.value.filter(c => c.type === 'sage'))
const travelers = computed(() => characters.value.filter(c => c.type === 'traveler'))

const fetchCharacters = async () => {
  loading.value = true
  try {
    const { data } = await client.get('/character')
    // 修复字段名：后端返回 avatar_url，前端使用 avatar
    characters.value = data.map((c: any) => ({
      ...c,
      avatar: c.avatar || c.avatar_url
    }))
    if (characters.value.length === 0) {
      characters.value = MOCK_CHARACTERS
    }
  } catch {
    characters.value = MOCK_CHARACTERS
  } finally {
    loading.value = false
  }
}

const handleAddCharacter = (type: 'sage' | 'traveler') => {
  modalType.value = type
  showModal.value = true
}

const handleCardClick = (character: Character) => {
  // 可以在这里添加点击卡片后的操作，比如进入详情页
  console.log('Card clicked:', character)
}

const handleEdit = (character: Character) => {
  editingCharacter.value = character
  showEditModal.value = true
}

const handleCreate = async (data: {
  type: 'sage' | 'traveler'
  name: string
  title: string
  description: string
  avatar?: string
  colorIdx: number
  tags: string[]
  personality?: string
  traits?: string[]
}) => {
  try {
    const response = await client.post('/character', {
      name: data.name,
      title: data.title,
      description: data.description,
      avatar: data.avatar,
      type: data.type,
      color: COLORS[data.colorIdx],
      tags: data.tags,
      personality: data.personality
    })
    // 添加到列表，使用后端返回的数据
    characters.value.push({
      ...response.data,
      avatar: response.data.avatar || response.data.avatar_url
    })
  } catch {
    // Mock mode: 添加到本地
    const newChar: Character = {
      id: Date.now(),
      name: data.name,
      title: data.title,
      description: data.description,
      avatar: data.avatar,
      type: data.type,
      is_builtin: false,
      color: COLORS[data.colorIdx],
      tags: data.tags,
      personality: data.personality
    }
    characters.value.push(newChar)
  }
  showModal.value = false
}

const handleUpdate = async (data: {
  id: number
  name: string
  title: string
  description: string
  avatar?: string
  colorIdx: number
  tags: string[]
  personality?: string
  type: 'sage' | 'traveler'
}) => {
  if (!editingCharacter.value) return
  
  try {
    await client.put(`/character/${editingCharacter.value.id}`, {
      name: data.name,
      title: data.title,
      description: data.description,
      avatar: data.avatar,
      tags: data.tags,
      personality: data.personality
    })
    
    // 更新本地数据
    const idx = characters.value.findIndex(c => c.id === editingCharacter.value!.id)
    if (idx !== -1) {
      characters.value[idx] = {
        ...characters.value[idx],
        name: data.name,
        title: data.title,
        description: data.description,
        avatar: data.avatar,
        color: COLORS[data.colorIdx],
        tags: data.tags,
        personality: data.personality
      }
    }
  } catch {
    // Mock mode: 更新本地数据
    const idx = characters.value.findIndex(c => c.id === editingCharacter.value!.id)
    if (idx !== -1) {
      characters.value[idx] = {
        ...characters.value[idx],
        name: data.name,
        title: data.title,
        description: data.description,
        avatar: data.avatar,
        color: COLORS[data.colorIdx],
        tags: data.tags,
        personality: data.personality
      }
    }
  }
  showEditModal.value = false
  editingCharacter.value = null
}

const confirmDelete = (character: Character) => {
  deleteTarget.value = character
  showDeleteConfirm.value = true
}

const handleDelete = async () => {
  if (!deleteTarget.value) return
  
  try {
    await client.delete(`/character/${deleteTarget.value.id}`)
  } catch {
    // Mock mode: 本地删除
  }
  
  // 从列表中移除
  characters.value = characters.value.filter(c => c.id !== deleteTarget.value!.id)
  
  showDeleteConfirm.value = false
  deleteTarget.value = null
}

onMounted(() => { fetchCharacters() })
</script>

<style scoped>
.char-page {
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

.char-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.add-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 160px;
  height: 200px;
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

.add-icon {
  font-size: 28px;
  color: rgba(255, 215, 0, 0.4);
  margin-bottom: 8px;
}

.add-text {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 215, 0, 0.4);
  letter-spacing: 2px;
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

/* Delete Confirmation Dialog */
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

.btn-cancel,
.btn-confirm {
  flex: 1;
  padding: 12px 20px;
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
  background: rgba(220, 38, 38, 0.9);
  border: none;
  color: white;
}

.btn-confirm:hover {
  background: rgba(220, 38, 38, 1);
}

/* Modal transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
