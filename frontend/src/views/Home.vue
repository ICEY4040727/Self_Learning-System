<template>
  <div class="home-page">
    <header class="header">
      <h1>学习主页</h1>
      <div class="user-menu">
        <span class="username">{{ authStore.user?.username }}</span>
        <button @click="router.push('/settings')">设置</button>
        <button @click="handleLogout">退出</button>
      </div>
    </header>

    <nav class="nav">
      <button @click="router.push('/character')">角色设定</button>
      <button @click="router.push('/archive')">档案管理</button>
    </nav>

    <main class="main">
      <section class="characters-section">
        <h2>我的角色</h2>
        <div class="characters-grid">
          <div
            v-for="char in characters"
            :key="char.id"
            class="character-card"
            @click="selectCharacter(char)"
          >
            <div class="char-avatar">
              {{ char.name?.[0] || '?' }}
            </div>
            <h3>{{ char.name }}</h3>
            <p class="char-desc">{{ char.personality || '暂无描述' }}</p>
          </div>
          <div class="character-card add-new" @click="router.push('/character')">
            <span class="plus">+</span>
            <p>创建新角色</p>
          </div>
        </div>
      </section>

      <section v-if="selectedCharacter" class="subjects-section">
        <h2>选择学习科目 - {{ selectedCharacter.name }}</h2>
        <div class="subjects-grid">
          <div
            v-for="subj in subjects"
            :key="subj.id"
            class="subject-card"
            @click="startLearning(subj.id)"
          >
            <h3>{{ subj.name }}</h3>
            <p>{{ subj.description || '暂无描述' }}</p>
            <span class="target-level">{{ subj.target_level || '未设定目标' }}</span>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import axios from 'axios'

const router = useRouter()
const authStore = useAuthStore()

interface Character {
  id: number
  name: string
  personality?: string
}

interface Subject {
  id: number
  name: string
  description?: string
  target_level?: string
}

const characters = ref<Character[]>([])
const subjects = ref<Subject[]>([])
const selectedCharacter = ref<Character | null>(null)

const fetchCharacters = async () => {
  try {
    const response = await axios.get('/api/character')
    characters.value = response.data
  } catch (error) {
    console.error('Failed to fetch characters:', error)
  }
}

const fetchSubjects = async (characterId: number) => {
  try {
    const response = await axios.get('/api/subjects', {
      params: { character_id: characterId }
    })
    subjects.value = response.data
  } catch (error) {
    console.error('Failed to fetch subjects:', error)
  }
}

const selectCharacter = (char: Character) => {
  selectedCharacter.value = char
  fetchSubjects(char.id)
}

const startLearning = (subjectId: number) => {
  router.push(`/learning/${subjectId}`)
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  fetchCharacters()
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 12px;
  margin-bottom: 20px;
}

.header h1 {
  color: #ffd700;
}

.user-menu {
  display: flex;
  gap: 15px;
  align-items: center;
}

.username {
  color: #ffd700;
}

.user-menu button {
  padding: 8px 16px;
  background: #2a2a4a;
  border: none;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.nav {
  display: flex;
  gap: 15px;
  margin-bottom: 30px;
}

.nav button {
  padding: 12px 24px;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.nav button:hover {
  background: #3a3a5a;
  border-color: #ffd700;
}

h2 {
  color: #ffd700;
  margin-bottom: 20px;
}

.characters-grid, .subjects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.character-card {
  background: rgba(0, 0, 0, 0.5);
  border: 2px solid #4a4a8a;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.character-card:hover {
  transform: translateY(-5px);
  border-color: #ffd700;
}

.char-avatar {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #4a4a8a, #2a2a4a);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: #ffd700;
  margin: 0 auto 15px;
}

.add-new {
  border-style: dashed;
}

.plus {
  font-size: 48px;
  color: #4a4a8a;
}

.subject-card {
  background: rgba(0, 0, 0, 0.5);
  border: 2px solid #4a4a8a;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.subject-card:hover {
  border-color: #4a8a4a;
}

.target-level {
  display: inline-block;
  margin-top: 10px;
  padding: 4px 12px;
  background: #4a8a4a;
  border-radius: 12px;
  font-size: 12px;
}
</style>