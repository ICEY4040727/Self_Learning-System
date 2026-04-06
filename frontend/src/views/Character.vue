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
            v-for="sage in sages"
            :key="sage.id"
            :name="sage.name"
            :title="sage.title"
            :avatar-url="sage.avatar_url"
            type="sage"
            :is-builtin="sage.is_builtin"
            :color="sage.color"
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
            v-for="traveler in travelers"
            :key="traveler.id"
            :name="traveler.name"
            :title="traveler.title"
            :avatar-url="traveler.avatar_url"
            type="traveler"
            :is-builtin="traveler.is_builtin"
            :color="traveler.color"
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
    <CreateCharacterModal
      :show="showModal"
      :default-type="modalType"
      @close="showModal = false"
      @create="handleCreate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '@/api/client'
import CharacterCard from '@/components/CharacterCard.vue'
import CreateCharacterModal from '@/components/CreateCharacterModal.vue'

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
  avatar_url?: string
  type: 'sage' | 'traveler'
  is_builtin: boolean
  color?: string
  tags?: string[]
}

import charBg from '@/assets/char-bg.jpg'

const BG_URL = charBg

const characters = ref<Character[]>([])
const loading = ref(false)
const showModal = ref(false)
const modalType = ref<'sage' | 'traveler'>('sage')

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
    characters.value = data
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

const handleCreate = (data: {
  type: 'sage' | 'traveler'
  title: string
  description: string
  tags: string[]
  colorIdx: number
  imageUrl?: string
}) => {
  const newChar: Character = {
    id: Date.now(),
    name: data.title,
    title: data.title,
    description: data.description,
    avatar_url: data.imageUrl,
    type: data.type,
    is_builtin: false,
    color: COLORS[data.colorIdx],
    tags: data.tags,
  }
  characters.value.push(newChar)
  showModal.value = false
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
}

.add-card:hover {
  background: rgba(255, 215, 0, 0.05);
  border-color: rgba(255, 215, 0, 0.5);
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
</style>
