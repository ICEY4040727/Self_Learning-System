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
      @saved="handleUpdate"
    />

    <!-- Delete Confirmation Dialog -->
    <Transition name="modal-fade">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="confirm-dialog">
          <div class="confirm-icon">[!]</div>
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
import { useToast } from '@/shared/composables/useToast'
import { characterApi } from '@/shared/api/character'
import CharacterCard from '@/characters/components/CharacterCard.vue'
import StepCreateModal from '@/shared/components/StepCreateModal.vue'
import EditCharacterModal from '@/characters/components/EditCharacterModal.vue'
import { parseApiError } from '@/shared/utils/error'

const router = useRouter()
import { PAGE_BACKGROUNDS } from '@/shared/constants/ui'

interface Character {
  id: number
  name: string
  title?: string
  description?: string
  avatar?: string
  type: 'sage' | 'traveler'
  is_builtin?: boolean
  color?: string
  tags?: string[]
  personality?: string
  greeting?: string
  speech_style?: string
  traits?: Record<string, number>
  template_name?: string
  system_prompt_template?: string
  sprites?: { color?: string; accentColor?: string }
  llm_settings?: Record<string, any>
}

const BG_URL = PAGE_BACKGROUNDS.character
const toast = useToast()

const characters = ref<Character[]>([])
const loading = ref(false)
const showModal = ref(false)
const showEditModal = ref(false)
const modalType = ref<'sage' | 'traveler'>('sage')
const editingCharacter = ref<Character | null>(null)

// Delete confirmation
const showDeleteConfirm = ref(false)
const deleteTarget = ref<Character | null>(null)

const sages = computed(() => characters.value.filter(c => c.type === 'sage'))
const travelers = computed(() => characters.value.filter(c => c.type === 'traveler'))

const normalizeCharacter = (character: any): Character => ({
  ...character,
  avatar: character.avatar || character.avatar_url,
  color: character.sprites?.color || character.color,
})

const fetchCharacters = async () => {
  loading.value = true
  try {
    const data = await characterApi.list()
    characters.value = data.map(normalizeCharacter)
  } catch (error) {
    characters.value = []
    toast.error(parseApiError(error))
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

const handleCreate = async (data: any) => {
  try {
    const newChar = await characterApi.create(data as any)
    characters.value.push(normalizeCharacter(newChar))
    showModal.value = false
  } catch (error) {
    toast.error(parseApiError(error))
  }
}

const handleUpdate = async (_updated?: any) => {
  await fetchCharacters()
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
    await characterApi.delete(deleteTarget.value.id)
    characters.value = characters.value.filter(c => c.id !== deleteTarget.value!.id)
    showDeleteConfirm.value = false
    deleteTarget.value = null
  } catch (error) {
    toast.error(parseApiError(error))
  }
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
