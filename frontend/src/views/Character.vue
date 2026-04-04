<template>
  <div class="character-page">
    <header class="header">
      <button class="back-btn" @click="router.push('/home')">← 返回</button>
      <h1>角色设定</h1>
    </header>

    <div v-if="errorMessage" class="error-toast">{{ errorMessage }}</div>

    <main class="main">
      <!-- 角色列表 -->
      <section class="section">
        <div class="section-header">
          <h2>我的角色</h2>
          <button class="add-btn" @click="openCreateCharacter">+ 新建角色</button>
        </div>

        <div class="characters-grid">
          <div
            v-for="char in characters"
            :key="char.id"
            :class="['character-card', { selected: selectedCharacter?.id === char.id }]"
            @click="selectCharacter(char)"
          >
            <div class="char-avatar">{{ char.name?.[0] || '?' }}</div>
            <h3>{{ char.name }}</h3>
            <span class="role-tag">{{ char.type === 'traveler' ? '旅者' : '知者' }}</span>
            <p>{{ char.personality || '暂无描述' }}</p>
            <div class="card-actions">
              <button @click.stop="openEditCharacter(char)">编辑</button>
              <button @click.stop="openSpriteUpload(char)" class="sprite-btn">立绘</button>
              <button @click.stop="deleteCharacter(char.id)" class="delete">删除</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 立绘上传对话框 -->
      <div v-if="showSpriteDialog" class="dialog-overlay" @click.self="showSpriteDialog = false">
        <div class="dialog">
          <h3>上传立绘 — {{ spriteCharacter?.name }}</h3>
          <p class="sprite-hint">文件名须为 default/happy/thinking/concerned + .png/.jpg/.webp，每张 ≤ 2MB</p>
          <div class="form-group">
            <input
              type="file"
              ref="spriteFileInput"
              multiple
              accept="image/png,image/jpeg,image/webp"
              class="sprite-file-input"
            />
          </div>
          <div v-if="spriteCharacter?.sprites" class="sprite-preview">
            <span v-for="(_url, expr) in spriteCharacter.sprites" :key="expr" class="sprite-tag">
              ✅ {{ expr }}
            </span>
          </div>
          <div class="dialog-actions">
            <button @click="showSpriteDialog = false">取消</button>
            <button class="primary" @click="uploadSprites" :disabled="spriteUploading">
              {{ spriteUploading ? '上传中...' : '上传' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 教师人格列表 -->
      <section v-if="selectedCharacter" class="section">
        <div class="section-header">
          <h2>教师人格 - {{ selectedCharacter.name }}</h2>
          <button class="add-btn" @click="openCreatePersona">+ 新建人格</button>
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
              特质: {{ formatTraits(persona.traits) }}
            </p>
            <p class="prompt-preview" v-if="persona.system_prompt_template">
              {{ persona.system_prompt_template.substring(0, 100) }}...
            </p>
            <div class="card-actions">
              <button v-if="!persona.is_active" @click="activatePersona(persona.id)">激活</button>
              <span v-else class="active-badge">已激活</span>
              <button @click="openEditPersona(persona)">编辑</button>
              <button @click="deletePersona(persona.id)" class="delete">删除</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 科目列表 -->
      <section v-if="selectedCharacter" class="section">
        <div class="section-header">
          <h2>学习科目</h2>
          <button class="add-btn" @click="openCreateSubject">+ 新建科目</button>
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
            <div class="card-actions">
              <button @click.stop="openEditSubject(subj)">编辑</button>
              <button @click.stop="deleteSubject(subj.id)" class="delete">删除</button>
            </div>
          </div>
        </div>
      </section>

      <!-- 角色对话框（创建/编辑） -->
      <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
        <div class="dialog">
          <h3>{{ editingCharacterId ? '编辑角色' : '新建角色' }}</h3>
          <div class="form-group">
            <label>角色名称</label>
            <input v-model="characterForm.name" placeholder="输入角色名称" />
          </div>
          <div class="form-group">
            <label>角色类型</label>
            <select v-model="characterForm.type">
              <option value="sage">知者（sage）</option>
              <option value="traveler">旅者（traveler）</option>
            </select>
          </div>
          <div class="form-group">
            <label>性格描述</label>
            <textarea v-model="characterForm.personality" placeholder="描述角色性格"></textarea>
          </div>
          <div class="form-group">
            <label>背景故事</label>
            <textarea v-model="characterForm.background" placeholder="描述角色背景"></textarea>
          </div>
          <div class="form-group">
            <label>说话风格</label>
            <textarea v-model="characterForm.speech_style" placeholder="如：温柔、幽默、严肃、口头禅等"></textarea>
          </div>
          <div class="dialog-actions">
            <button @click="showCreateDialog = false">取消</button>
            <button class="primary" @click="saveCharacter">
              {{ editingCharacterId ? '保存' : '创建' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 教师人格对话框（创建/编辑） -->
      <div v-if="showPersonaDialog" class="dialog-overlay" @click.self="showPersonaDialog = false">
        <div class="dialog">
          <h3>{{ editingPersonaId ? '编辑教师人格' : '新建教师人格' }}</h3>
          <div class="form-group">
            <label>人格名称</label>
            <input v-model="personaForm.name" placeholder="如：苏格拉底型、朋友型" />
          </div>
          <div class="form-group">
            <label>版本</label>
            <input v-model="personaForm.version" placeholder="1.0" />
          </div>
          <div class="form-group">
            <label>教学风格</label>
            <!-- AI Generate -->
            <div class="ai-generate">
              <input
                v-model="aiDescription"
                placeholder="描述你想要的教师风格，如：像爱因斯坦一样幽默的物理老师"
                class="ai-input"
              />
              <button class="ai-btn" @click="generatePersona" :disabled="aiGenerating || !aiDescription.trim() || aiCooldown > 0">
                {{ aiGenerating ? '生成中...' : aiCooldown > 0 ? `${aiCooldown}s` : '✨ AI 生成' }}
              </button>
            </div>
            <!-- Quick Presets -->
            <div class="preset-row">
              <button
                v-for="preset in PERSONA_PRESETS"
                :key="preset.id"
                class="preset-tag"
                :class="{ 'preset-tag-active': selectedPreset === preset.id }"
                @click="selectPreset(preset)"
              >
                {{ preset.icon }} {{ preset.name }}
              </button>
            </div>
          </div>
          <div class="form-group">
            <label>性格特质（逗号分隔）</label>
            <input v-model="personaForm.traitsInput" placeholder="如：耐心, 幽默, 严谨, 鼓励" />
          </div>
          <div class="form-group">
            <label>教师人格描述 <span class="label-hint">（可手动编辑）</span></label>
            <textarea v-model="personaForm.system_prompt_template" rows="4" placeholder="AI 生成或从预设选择后可在此编辑..."></textarea>
          </div>
          <div class="dialog-actions">
            <button @click="showPersonaDialog = false">取消</button>
            <button class="primary" @click="savePersona">
              {{ editingPersonaId ? '保存' : '创建' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 科目对话框（创建/编辑） -->
      <div v-if="showSubjectDialog" class="dialog-overlay" @click.self="showSubjectDialog = false">
        <div class="dialog">
          <h3>{{ editingSubjectId ? '编辑科目' : '新建科目' }}</h3>
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
            <button class="primary" @click="saveSubject">
              {{ editingSubjectId ? '保存' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'

const router = useRouter()
const authStore = useAuthStore()
const errorMessage = ref('')

const showError = (e: any) => {
  errorMessage.value = parseApiError(e)
  setTimeout(() => { errorMessage.value = '' }, 5000)
}

interface Character {
  id: number
  name: string
  type?: 'sage' | 'traveler'
  personality?: string
  sprites?: Record<string, string>
  background?: string
  speech_style?: string
}

interface TeacherPersona {
  id: number
  character_id: number
  name: string
  version: string
  traits?: any
  system_prompt_template?: string
  is_active: boolean
}

interface Subject {
  id: number
  character_id: number
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
const showSpriteDialog = ref(false)
const spriteCharacter = ref<Character | null>(null)
const spriteUploading = ref(false)
const spriteFileInput = ref<HTMLInputElement | null>(null)

const openSpriteUpload = (char: Character) => {
  spriteCharacter.value = char
  showSpriteDialog.value = true
}

const uploadSprites = async () => {
  if (!spriteCharacter.value || !spriteFileInput.value?.files?.length) return
  spriteUploading.value = true
  try {
    const formData = new FormData()
    for (const file of spriteFileInput.value.files) {
      formData.append('files', file)
    }
    const res = await axios.post(
      `/api/characters/${spriteCharacter.value.id}/sprites`,
      formData,
      { headers: headers() }
    )
    // Update local character data
    spriteCharacter.value.sprites = res.data.sprites
    // Update in characters list
    const idx = characters.value.findIndex(c => c.id === spriteCharacter.value?.id)
    if (idx >= 0) characters.value[idx].sprites = res.data.sprites
    if (spriteFileInput.value) spriteFileInput.value.value = ''
    showSpriteDialog.value = false
  } catch (error) {
    showError(error)
  } finally {
    spriteUploading.value = false
  }
}

const editingCharacterId = ref<number | null>(null)
const editingPersonaId = ref<number | null>(null)
const editingSubjectId = ref<number | null>(null)

// AI persona generation
const aiDescription = ref('')
const aiGenerating = ref(false)
const aiCooldown = ref(0)
let cooldownTimer: number | null = null
const selectedPreset = ref('')

const PERSONA_PRESETS = [
  { id: 'socrates', icon: '🏛️', name: '苏格拉底',
    prompt: '你是苏格拉底，古希腊雅典的哲学家。你相信真正的智慧始于承认自己的无知。你说话平和从容但思维极其犀利，喜欢用市集上买菜、匠人做陶这样的日常类比来探讨深刻的问题。面对学生的错误你从不恼怒，只是微笑着抛出下一个问题。',
    traits: '平和, 犀利, 类比, 追问' },
  { id: 'zhuge', icon: '🎯', name: '诸葛亮',
    prompt: '你是诸葛孔明，蜀汉丞相。你运筹帷幄、思虑缜密，善于从全局出发分析问题。你说话不疾不徐、引经据典，偶尔用三国战役中的策略来类比学习中的难题。你对学生要求严格但从不苛刻，更希望他们学会"谋定而后动"。',
    traits: '缜密, 全局, 引经据典, 战略' },
  { id: 'explorer', icon: '🤝', name: '探险伙伴',
    prompt: '你是一个热爱探索的冒险家，把每个知识点都当作一座待攀登的山峰。你语气轻松活泼，会说「我们一起看看这里有什么宝藏」「哇这个问题比想象的有趣」。你把犯错当作探险的一部分——「走错路也能发现新风景」。',
    traits: '冒险, 乐观, 好奇, 轻松' },
  { id: 'professor', icon: '📚', name: '学院导师',
    prompt: '你是一位现代大学的资深教授，治学严谨、逻辑清晰。你习惯用专业术语讨论问题，会纠正不精确的表述，但也善于用学科内的经典案例让抽象概念变得直观。你对学术诚信和独立思考有很高的期望。',
    traits: '严谨, 专业, 逻辑, 案例' },
  { id: 'senpai', icon: '🌸', name: '治愈系学姐',
    prompt: '你是一个温柔体贴的学姐，总是笑眯眯地鼓励后辈。你常说「这个想法超棒的！」「别担心，我刚学这个的时候也觉得好难」。你喜欢用生活中的小例子解释复杂的东西，犯错的时候你会说「没关系啦，我们换个角度试试～」',
    traits: '温柔, 鼓励, 共情, 亲切' },
]

const selectPreset = (preset: typeof PERSONA_PRESETS[0]) => {
  selectedPreset.value = preset.id
  personaForm.value.system_prompt_template = preset.prompt
  personaForm.value.traitsInput = preset.traits
  if (!personaForm.value.name) {
    personaForm.value.name = preset.name
  }
}

const startCooldown = () => {
  aiCooldown.value = 30
  cooldownTimer = window.setInterval(() => {
    aiCooldown.value--
    if (aiCooldown.value <= 0 && cooldownTimer) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

const generatePersona = async () => {
  if (!aiDescription.value.trim() || aiCooldown.value > 0) return
  aiGenerating.value = true
  try {
    const res = await axios.post('/api/persona/generate', {
      description: aiDescription.value.trim(),
    }, { headers: headers() })
    personaForm.value.system_prompt_template = res.data.system_prompt_template || ''
    personaForm.value.traitsInput = (res.data.traits || []).join(', ')
    if (!personaForm.value.name) {
      personaForm.value.name = res.data.name_suggestion
    }
    selectedPreset.value = ''
    startCooldown()
  } catch (error) {
    showError(error)
  } finally {
    aiGenerating.value = false
  }
}

const characterForm = ref({ name: '', type: 'sage' as 'sage' | 'traveler', personality: '', background: '', speech_style: '' })
const personaForm = ref({ name: '', version: '1.0', traitsInput: '', system_prompt_template: '' })
const subjectForm = ref({ name: '', description: '', target_level: '' })

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })

// --- Helpers ---

const formatTraits = (traits: any): string => {
  if (Array.isArray(traits)) return traits.join(', ')
  if (typeof traits === 'object') return Object.values(traits).join(', ')
  return String(traits)
}

const parseTraits = (input: string): string[] => {
  return input.split(/[,，]/).map(s => s.trim()).filter(Boolean)
}

// --- Fetch ---

const fetchCharacters = async () => {
  try {
    const res = await axios.get('/api/character', { headers: headers() })
    characters.value = res.data
  } catch (error) {
    showError(error)
  }
}

const fetchTeacherPersonas = async (characterId: number) => {
  try {
    const res = await axios.get(`/api/teacher_persona?character_id=${characterId}`, { headers: headers() })
    teacherPersonas.value = res.data
  } catch (error) {
    showError(error)
  }
}

const fetchSubjects = async (characterId: number) => {
  try {
    const res = await axios.get(`/api/subjects?character_id=${characterId}`, { headers: headers() })
    subjects.value = res.data
  } catch (error) {
    showError(error)
  }
}

const selectCharacter = (char: Character) => {
  selectedCharacter.value = char
  fetchTeacherPersonas(char.id)
  fetchSubjects(char.id)
}

// --- Character CRUD ---

const resetCharacterForm = () => {
  characterForm.value = { name: '', type: 'sage', personality: '', background: '', speech_style: '' }
  editingCharacterId.value = null
}

const openCreateCharacter = () => {
  resetCharacterForm()
  showCreateDialog.value = true
}

const openEditCharacter = (char: Character) => {
  editingCharacterId.value = char.id
  characterForm.value = {
    name: char.name,
    type: char.type || 'sage',
    personality: char.personality || '',
    background: char.background || '',
    speech_style: char.speech_style || '',
  }
  showCreateDialog.value = true
}

const saveCharacter = async () => {
  try {
    if (editingCharacterId.value) {
      await axios.put(`/api/character/${editingCharacterId.value}`, characterForm.value, { headers: headers() })
    } else {
      await axios.post('/api/character', characterForm.value, { headers: headers() })
    }
    showCreateDialog.value = false
    resetCharacterForm()
    fetchCharacters()
  } catch (error) {
    showError(error)
  }
}

const deleteCharacter = async (id: number) => {
  if (!confirm('确定要删除这个角色吗？相关的人格和科目也会被删除。')) return
  try {
    await axios.delete(`/api/character/${id}`, { headers: headers() })
    if (selectedCharacter.value?.id === id) {
      selectedCharacter.value = null
      teacherPersonas.value = []
      subjects.value = []
    }
    fetchCharacters()
  } catch (error) {
    showError(error)
  }
}

// --- Persona CRUD ---

const resetPersonaForm = () => {
  personaForm.value = { name: '', version: '1.0', traitsInput: '', system_prompt_template: '' }
  editingPersonaId.value = null
}

const openCreatePersona = () => {
  resetPersonaForm()
  showPersonaDialog.value = true
}

const editingPersonaWasActive = ref(false)

const openEditPersona = (persona: TeacherPersona) => {
  editingPersonaId.value = persona.id
  editingPersonaWasActive.value = persona.is_active
  personaForm.value = {
    name: persona.name,
    version: persona.version,
    traitsInput: persona.traits ? formatTraits(persona.traits) : '',
    system_prompt_template: persona.system_prompt_template || '',
  }
  showPersonaDialog.value = true
}

const savePersona = async () => {
  if (!selectedCharacter.value) return
  const payload = {
    character_id: selectedCharacter.value.id,
    name: personaForm.value.name,
    version: personaForm.value.version,
    traits: parseTraits(personaForm.value.traitsInput),
    system_prompt_template: personaForm.value.system_prompt_template,
    is_active: editingPersonaId.value ? editingPersonaWasActive.value : false,
  }
  try {
    if (editingPersonaId.value) {
      await axios.put(`/api/teacher_persona/${editingPersonaId.value}`, payload, { headers: headers() })
    } else {
      await axios.post('/api/teacher_persona', payload, { headers: headers() })
    }
    showPersonaDialog.value = false
    resetPersonaForm()
    fetchTeacherPersonas(selectedCharacter.value.id)
  } catch (error) {
    showError(error)
  }
}

const deletePersona = async (id: number) => {
  if (!confirm('确定要删除这个教师人格吗？')) return
  try {
    await axios.delete(`/api/teacher_persona/${id}`, { headers: headers() })
    if (selectedCharacter.value) {
      fetchTeacherPersonas(selectedCharacter.value.id)
    }
  } catch (error) {
    showError(error)
  }
}

const activatePersona = async (personaId: number) => {
  try {
    await axios.put(`/api/teacher_persona/${personaId}/activate`, {}, { headers: headers() })
    if (selectedCharacter.value) {
      fetchTeacherPersonas(selectedCharacter.value.id)
    }
  } catch (error) {
    showError(error)
  }
}

// --- Subject CRUD ---

const resetSubjectForm = () => {
  subjectForm.value = { name: '', description: '', target_level: '' }
  editingSubjectId.value = null
}

const openCreateSubject = () => {
  resetSubjectForm()
  showSubjectDialog.value = true
}

const openEditSubject = (subj: Subject) => {
  editingSubjectId.value = subj.id
  subjectForm.value = {
    name: subj.name,
    description: subj.description || '',
    target_level: subj.target_level || '',
  }
  showSubjectDialog.value = true
}

const saveSubject = async () => {
  if (!selectedCharacter.value) return
  const payload = {
    character_id: selectedCharacter.value.id,
    name: subjectForm.value.name,
    description: subjectForm.value.description,
    target_level: subjectForm.value.target_level,
  }
  try {
    if (editingSubjectId.value) {
      await axios.put(`/api/subjects/${editingSubjectId.value}`, payload, { headers: headers() })
    } else {
      await axios.post('/api/subjects', payload, { headers: headers() })
    }
    showSubjectDialog.value = false
    resetSubjectForm()
    fetchSubjects(selectedCharacter.value.id)
  } catch (error) {
    showError(error)
  }
}

const deleteSubject = async (id: number) => {
  if (!confirm('确定要删除这个科目吗？')) return
  try {
    await axios.delete(`/api/subjects/${id}`, { headers: headers() })
    if (selectedCharacter.value) {
      fetchSubjects(selectedCharacter.value.id)
    }
  } catch (error) {
    showError(error)
  }
}

onMounted(() => {
  fetchCharacters()
})

onUnmounted(() => {
  if (cooldownTimer) clearInterval(cooldownTimer)
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

.character-card.selected {
  border-color: #ffd700;
  box-shadow: 0 0 12px rgba(255, 215, 0, 0.3);
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

.role-tag {
  display: inline-block;
  margin-bottom: 8px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: #fff;
  background: #4a4a8a;
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
  max-height: 90vh;
  overflow-y: auto;
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
  box-sizing: border-box;
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

.error-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(215, 58, 74, 0.9);
  color: #fff;
  padding: 12px 24px;
  border-radius: 8px;
  z-index: 2000;
  font-size: 14px;
}

/* AI Generate */
.ai-generate {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.ai-input {
  flex: 1;
  padding: 10px;
  background: var(--bg-secondary, #1a1a2e);
  border: 1px solid var(--border-subtle, #4a4a8a);
  border-radius: 6px;
  color: var(--text-primary, #fff);
  font-size: 13px;
}

.ai-input:focus {
  outline: none;
  border-color: var(--accent-gold, #ffd700);
}

.ai-btn {
  padding: 10px 16px;
  background: linear-gradient(135deg, var(--accent-gold, #ffd700), var(--accent-orange, #ff8c00));
  color: var(--bg-primary, #0a0a1e);
  border: none;
  border-radius: 6px;
  font-weight: bold;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast, 0.2s);
}

.ai-btn:hover:not(:disabled) {
  box-shadow: 0 0 12px rgba(255, 215, 0, 0.4);
}

.ai-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Preset Tags */
.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-tag {
  padding: 6px 12px;
  background: var(--bg-secondary, #2a2a4a);
  border: 1px solid var(--border-subtle, #4a4a8a);
  border-radius: 16px;
  color: var(--text-secondary, #aaa);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition-fast, 0.2s);
}

.preset-tag:hover {
  border-color: var(--accent-gold, #ffd700);
  color: var(--text-primary, #fff);
}

.preset-tag-active {
  border-color: var(--accent-gold, #ffd700);
  color: var(--accent-gold, #ffd700);
  background: rgba(255, 215, 0, 0.1);
}

.label-hint {
  font-size: 11px;
  color: var(--text-muted, #666);
  font-weight: normal;
}

/* Sprite upload */
.sprite-btn {
  border-color: var(--emotion-thinking, #60a5fa) !important;
  color: var(--emotion-thinking, #60a5fa) !important;
}

.sprite-hint {
  font-size: 12px;
  color: var(--text-muted, #888);
  margin-bottom: 12px;
}

.sprite-file-input {
  width: 100%;
  color: var(--text-secondary, #aaa);
  font-size: 13px;
}

.sprite-preview {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.sprite-tag {
  font-size: 12px;
  padding: 3px 10px;
  background: rgba(74, 223, 106, 0.1);
  border: 1px solid var(--emotion-positive, #4adf6a);
  border-radius: 12px;
  color: var(--emotion-positive, #4adf6a);
}
</style>
