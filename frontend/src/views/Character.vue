<template>
  <div class="character-page">
    <header class="header">
      <button class="back-btn" @click="router.push('/home')">← 返回</button>
      <h1>角色设定</h1>
    </header>

    <main class="main">
      <!-- 角色列表 -->
      <section class="section">
        <div class="section-header">
          <h2>我的角色</h2>
          <button class="add-btn" @click="showCreateDialog = true">+ 新建角色</button>
        </div>

        <div class="characters-grid">
          <div
            v-for="char in characters"
            :key="char.id"
            class="character-card"
            @click="selectCharacter(char)"
          >
            <div class="char-avatar">{{ char.name?.[0] || '?' }}</div>
            <h3>{{ char.name }}</h3>
            <p>{{ char.personality || '暂无描述' }}</p>
            <div class="card-actions">
              <button @click.stop="editCharacter(char)">编辑</button>
              <button @click.stop="deleteCharacter(char.id)" class="delete">删除</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 教师人格列表 -->
      <section v-if="selectedCharacter" class="section">
        <div class="section-header">
          <h2>教师人格 - {{ selectedCharacter.name }}</h2>
          <button class="add-btn" @click="showPersonaDialog = true">+ 新建人格</button>
        </div>

        <div class="personas-list">
          <div
            v-for="persona in teacherPersonas"
            :key="persona.id"
            :class="['persona-card', { active: persona.is_active }]"
          >
            <div class="persona-header">
              <h3>{{ persona.name }}</h3>
              <span class="version">v{{ persona.version }}</span>
            </div>
            <p class="traits" v-if="persona.traits">
              特质: {{ JSON.stringify(persona.traits) }}
            </p>
            <p class="prompt-preview" v-if="persona.system_prompt_template">
              {{ persona.system_prompt_template.substring(0, 100) }}...
            </p>
            <div class="card-actions">
              <button v-if="!persona.is_active" @click="activatePersona(persona.id)">激活</button>
              <span v-else class="active-badge">已激活</span>
              <button @click="editPersona(persona)">编辑</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 科目列表 -->
      <section v-if="selectedCharacter" class="section">
        <div class="section-header">
          <h2>学习科目</h2>
          <button class="add-btn" @click="showSubjectDialog = true">+ 新建科目</button>
        </div>

        <div class="subjects-list">
          <div
            v-for="subj in subjects"
            :key="subj.id"
            class="subject-card"
          >
            <h3>{{ subj.name }}</h3>
            <p>{{ subj.description || '暂无描述' }}</p>
            <span class="target">{{ subj.target_level || '未设目标' }}</span>
          </div>
        </div>
      </section>

      <!-- 创建角色对话框 -->
      <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
        <div class="dialog">
          <h3>新建角色</h3>
          <div class="form-group">
            <label>角色名称</label>
            <input v-model="characterForm.name" placeholder="输入角色名称" />
          </div>
          <div class="form-group">
            <label>性格描述</label>
            <textarea v-model="characterForm.personality" placeholder="描述角色性格"></textarea>
          </div>
          <div class="form-group">
            <label>背景故事</label>
            <textarea v-model="characterForm.background" placeholder="描述角色背景"></textarea>
          </div>
          <div class="dialog-actions">
            <button @click="showCreateDialog = false">取消</button>
            <button class="primary" @click="createCharacter">创建</button>
          </div>
        </div>
      </div>

      <!-- 创建教师人格对话框 -->
      <div v-if="showPersonaDialog" class="dialog-overlay" @click.self="showPersonaDialog = false">
        <div class="dialog">
          <h3>新建教师人格</h3>
          <div class="form-group">
            <label>人格名称</label>
            <input v-model="personaForm.name" placeholder="如：苏格拉底型、朋友型" />
          </div>
          <div class="form-group">
            <label>版本</label>
            <input v-model="personaForm.version" placeholder="1.0" />
          </div>
          <div class="form-group">
            <label>系统提示词模板</label>
            <textarea v-model="personaForm.system_prompt_template" rows="6" placeholder="设置AI教师的系统提示词..."></textarea>
          </div>
          <div class="dialog-actions">
            <button @click="showPersonaDialog = false">取消</button>
            <button class="primary" @click="createPersona">创建</button>
          </div>
        </div>
      </div>

      <!-- 创建科目对话框 -->
      <div v-if="showSubjectDialog" class="dialog-overlay" @click.self="showSubjectDialog = false">
        <div class="dialog">
          <h3>新建科目</h3>
          <div class="form-group">
            <label>科目名称</label>
            <input v-model="subjectForm.name" placeholder="如：数学、英语" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="subjectForm.description" placeholder="科目描述"></textarea>
          </div>
          <div class="form-group">
            <label>目标级别</label>
            <input v-model="subjectForm.target_level" placeholder="如：初级、中级、高级" />
          </div>
          <div class="dialog-actions">
            <button @click="showSubjectDialog = false">取消</button>
            <button class="primary" @click="createSubject">创建</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

interface Character {
  id: number
  name: string
  personality?: string
  background?: string
}

interface TeacherPersona {
  id: number
  name: string
  version: string
  traits?: any
  system_prompt_template?: string
  is_active: boolean
}

interface Subject {
  id: number
  name: string
  description?: string
  target_level?: string
}

const characters = ref<Character[]>([])
const teacherPersonas = ref<TeacherPersona[]>([])
const subjects = ref<Subject[]>([])
const selectedCharacter = ref<Character | null>(null)

const showCreateDialog = ref(false)
const showPersonaDialog = ref(false)
const showSubjectDialog = ref(false)

const characterForm = ref({ name: '', personality: '', background: '' })
const personaForm = ref({ name: '', version: '1.0', system_prompt_template: '' })
const subjectForm = ref({ name: '', description: '', target_level: '' })

const api = (path: string) => {
  return axios.get(path, { headers: { Authorization: `Bearer ${authStore.token}` } })
}

const fetchCharacters = async () => {
  try {
    const response = await api('/api/character')
    characters.value = response.data
  } catch (error) {
    console.error('Failed to fetch characters:', error)
  }
}

const fetchTeacherPersonas = async (characterId: number) => {
  try {
    const response = await api(`/api/teacher_persona?character_id=${characterId}`)
    teacherPersonas.value = response.data
  } catch (error) {
    console.error('Failed to fetch personas:', error)
  }
}

const fetchSubjects = async (characterId: number) => {
  try {
    const response = await api(`/api/subjects?character_id=${characterId}`)
    subjects.value = response.data
  } catch (error) {
    console.error('Failed to fetch subjects:', error)
  }
}

const selectCharacter = (char: Character) => {
  selectedCharacter.value = char
  fetchTeacherPersonas(char.id)
  fetchSubjects(char.id)
}

const createCharacter = async () => {
  try {
    await axios.post('/api/character', characterForm.value, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    showCreateDialog.value = false
    characterForm.value = { name: '', personality: '', background: '' }
    fetchCharacters()
  } catch (error) {
    console.error('Failed to create character:', error)
  }
}

const editCharacter = (char: Character) => {
  characterForm.value = { ...char }
  showCreateDialog.value = true
}

const deleteCharacter = async (id: number) => {
  if (!confirm('确定要删除这个角色吗？')) return
  try {
    await axios.delete(`/api/character/${id}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    fetchCharacters()
  } catch (error) {
    console.error('Failed to delete character:', error)
  }
}

const createPersona = async () => {
  if (!selectedCharacter.value) return
  try {
    await axios.post('/api/teacher_persona', {
      ...personaForm.value,
      character_id: selectedCharacter.value.id
    }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    showPersonaDialog.value = false
    personaForm.value = { name: '', version: '1.0', system_prompt_template: '' }
    fetchTeacherPersonas(selectedCharacter.value.id)
  } catch (error) {
    console.error('Failed to create persona:', error)
  }
}

const editPersona = (persona: TeacherPersona) => {
  personaForm.value = { ...persona }
  showPersonaDialog.value = true
}

const activatePersona = async (personaId: number) => {
  try {
    await axios.put(`/api/teacher_persona/${personaId}/activate`, {}, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    if (selectedCharacter.value) {
      fetchTeacherPersonas(selectedCharacter.value.id)
    }
  } catch (error) {
    console.error('Failed to activate persona:', error)
  }
}

const createSubject = async () => {
  if (!selectedCharacter.value) return
  try {
    await axios.post('/api/subjects', {
      ...subjectForm.value,
      character_id: selectedCharacter.value.id
    }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    showSubjectDialog.value = false
    subjectForm.value = { name: '', description: '', target_level: '' }
    fetchSubjects(selectedCharacter.value.id)
  } catch (error) {
    console.error('Failed to create subject:', error)
  }
}

onMounted(() => {
  fetchCharacters()
})
</script>

<style scoped>
.character-page {
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
}

.header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
}

.header h1 {
  color: #ffd700;
}

.back-btn {
  padding: 8px 16px;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.back-btn:hover {
  background: #3a3a5a;
  border-color: #ffd700;
}

.section {
  margin-bottom: 30px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section h2 {
  color: #ffd700;
}

.add-btn {
  padding: 8px 16px;
  background: #4a8a4a;
  border: none;
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
}

.add-btn:hover {
  background: #5a9a5a;
}

.characters-grid, .subjects-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.character-card, .subject-card {
  background: rgba(0, 0, 0, 0.5);
  border: 2px solid #4a4a8a;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.character-card:hover {
  border-color: #ffd700;
}

.char-avatar {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #4a4a8a, #2a2a4a);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #ffd700;
  margin-bottom: 10px;
}

.character-card h3, .subject-card h3 {
  color: #fff;
  margin-bottom: 8px;
}

.character-card p, .subject-card p {
  color: #888;
  font-size: 14px;
  margin-bottom: 10px;
}

.target {
  display: inline-block;
  padding: 4px 12px;
  background: #4a8a4a;
  border-radius: 12px;
  font-size: 12px;
  color: #fff;
}

.card-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.card-actions button {
  padding: 6px 12px;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.card-actions button:hover {
  background: #3a3a5a;
}

.card-actions button.delete {
  border-color: #8a4a4a;
}

.card-actions button.delete:hover {
  background: #8a4a4a;
}

.active-badge {
  padding: 6px 12px;
  background: #4a8a4a;
  border-radius: 4px;
  font-size: 12px;
  color: #fff;
}

.personas-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.persona-card {
  background: rgba(0, 0, 0, 0.5);
  border: 2px solid #4a4a8a;
  border-radius: 12px;
  padding: 20px;
}

.persona-card.active {
  border-color: #4a8a4a;
}

.persona-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.persona-header h3 {
  color: #fff;
}

.version {
  color: #888;
  font-size: 12px;
}

.traits, .prompt-preview {
  color: #888;
  font-size: 14px;
  margin-bottom: 10px;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  border-radius: 12px;
  padding: 30px;
  width: 90%;
  max-width: 500px;
}

.dialog h3 {
  color: #ffd700;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  color: #fff;
  margin-bottom: 8px;
}

.form-group input, .form-group textarea {
  width: 100%;
  padding: 10px;
  background: #1a1a2e;
  border: 1px solid #4a4a8a;
  border-radius: 6px;
  color: #fff;
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.dialog-actions button {
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  color: #fff;
}

.dialog-actions button.primary {
  background: #4a8a4a;
  border: none;
}

.dialog-actions button.primary:hover {
  background: #5a9a5a;
}
</style>