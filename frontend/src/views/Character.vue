<template>
  <div class="character-page">
    <div class="character-bg-image"></div>
    <div class="character-bg-overlay"></div>

    <header class="header">
      <button class="back-btn" @click="router.push('/home')">← 返回</button>
      <h1>角色设定</h1>
    </header>

    <div v-if="errorMessage" class="error-toast">{{ errorMessage }}</div>

    <main class="main character-content galgame-scrollbar">
      <!-- 角色列表 -->
      <section class="section galgame-panel">
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
      <section v-if="selectedCharacter" class="section galgame-panel">
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

      <!-- 课程列表 -->
      <section v-if="selectedCharacter" class="section galgame-panel">
        <div class="section-header">
          <h2>学习课程</h2>
          <button class="add-btn" @click="openCreateSubject">+ 新建课程</button>
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

      <!-- 课程对话框（创建/编辑） -->
      <div v-if="showSubjectDialog" class="dialog-overlay" @click.self="showSubjectDialog = false">
        <div class="dialog">
          <h3>{{ editingSubjectId ? '编辑课程' : '新建课程' }}</h3>
          <div class="form-group">
            <label>所属世界</label>
            <select v-model.number="subjectForm.world_id">
              <option v-for="world in characterWorlds" :key="world.id" :value="world.id">
                {{ world.name }}
              </option>
            </select>
            <p v-if="characterWorlds.length === 0" class="field-hint">保存时将自动创建角色默认世界</p>
          </div>
          <div class="form-group">
            <label>课程名称</label>
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

const showError = (e: unknown) => {
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

interface Course {
  id: number
  world_id: number
  name: string
  description?: string
  target_level?: string
}

interface World {
  id: number
  name: string
}

interface WorldCharacterLink {
  character_id: number
}

const characters = ref<Character[]>([])
const teacherPersonas = ref<TeacherPersona[]>([])
const subjects = ref<Course[]>([])
const characterWorlds = ref<World[]>([])
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
const subjectForm = ref({ world_id: null as number | null, name: '', description: '', target_level: '' })

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

const fetchCharacterWorlds = async (characterId: number) => {
  const worldsRes = await axios.get('/api/worlds', { headers: headers() })
  const allWorlds = (worldsRes.data || []) as World[]
  const worldWithLinks = await Promise.all(
    allWorlds.map(async (world) => {
      const linksRes = await axios.get(`/api/worlds/${world.id}/characters`, { headers: headers() })
      return { world, links: (linksRes.data || []) as WorldCharacterLink[] }
    })
  )
  characterWorlds.value = worldWithLinks
    .filter((item) => item.links.some((link) => link.character_id === characterId))
    .map((item) => item.world)
}

const ensurePrimaryWorldForCharacter = async (character: Character) => {
  await fetchCharacterWorlds(character.id)
  if (characterWorlds.value.length > 0) {
    return characterWorlds.value[0].id
  }

  const worldRes = await axios.post(
    '/api/worlds',
    {
      name: `${character.name} World`,
      description: `Auto-created world for ${character.name}`,
      scenes: {},
    },
    { headers: headers() }
  )
  const worldId = worldRes.data.id as number
  await axios.post(
    `/api/worlds/${worldId}/characters`,
    {
      character_id: character.id,
      role: character.type === 'traveler' ? 'traveler' : 'sage',
      is_primary: true,
    },
    { headers: headers() }
  )
  characterWorlds.value = [{ id: worldId, name: worldRes.data.name }]
  return worldId
}

const fetchSubjects = async (characterId: number) => {
  try {
    await fetchCharacterWorlds(characterId)
    if (characterWorlds.value.length === 0) {
      subjects.value = []
      return
    }
    const courseResponses = await Promise.all(
      characterWorlds.value.map((world) =>
        axios.get(`/api/worlds/${world.id}/courses`, { headers: headers() })
      )
    )
    subjects.value = courseResponses.flatMap((response) => response.data)
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
  if (!confirm('确定要删除这个角色吗？相关的世界绑定与学习数据可能会受影响。')) return
  try {
    await axios.delete(`/api/character/${id}`, { headers: headers() })
    if (selectedCharacter.value?.id === id) {
      selectedCharacter.value = null
      teacherPersonas.value = []
      subjects.value = []
      characterWorlds.value = []
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
  subjectForm.value = { world_id: characterWorlds.value[0]?.id ?? null, name: '', description: '', target_level: '' }
  editingSubjectId.value = null
}

const openCreateSubject = () => {
  resetSubjectForm()
  showSubjectDialog.value = true
}

const openEditSubject = (subj: Course) => {
  editingSubjectId.value = subj.id
  subjectForm.value = {
    world_id: subj.world_id,
    name: subj.name,
    description: subj.description || '',
    target_level: subj.target_level || '',
  }
  showSubjectDialog.value = true
}

const saveSubject = async () => {
  if (!selectedCharacter.value) return
  try {
    if (editingSubjectId.value) {
      if (!subjectForm.value.world_id) {
        showError(new Error('缺少世界信息，无法更新课程'))
        return
      }
      await axios.put(
        `/api/courses/${editingSubjectId.value}`,
        {
          world_id: subjectForm.value.world_id,
          name: subjectForm.value.name,
          description: subjectForm.value.description,
          target_level: subjectForm.value.target_level,
        },
        { headers: headers() }
      )
    } else {
      const worldId = subjectForm.value.world_id ?? await ensurePrimaryWorldForCharacter(selectedCharacter.value)
      await axios.post(
        `/api/worlds/${worldId}/courses`,
        {
          name: subjectForm.value.name,
          description: subjectForm.value.description,
          target_level: subjectForm.value.target_level,
        },
        { headers: headers() }
      )
    }
    showSubjectDialog.value = false
    resetSubjectForm()
    fetchSubjects(selectedCharacter.value.id)
  } catch (error) {
    showError(error)
  }
}

const deleteSubject = async (id: number) => {
  if (!confirm('确定要删除这个课程吗？')) return
  try {
    await axios.delete(`/api/courses/${id}`, { headers: headers() })
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
  position: relative;
  min-height: 100vh;
  padding: 24px;
  background: linear-gradient(180deg, #0f172a 0%, #111827 55%, #0b1220 100%);
  overflow: hidden;
}

.character-bg-image {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(135deg, rgba(59, 130, 246, 0.09), transparent 40%),
    linear-gradient(315deg, rgba(124, 58, 237, 0.12), transparent 45%);
  opacity: 0.12;
  pointer-events: none;
}

.character-bg-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 12% 12%, rgba(255, 215, 0, 0.1), transparent 45%),
    radial-gradient(circle at 88% 18%, rgba(99, 102, 241, 0.16), transparent 42%);
  pointer-events: none;
}

.header,
.character-content,
.error-toast {
  position: relative;
  z-index: 2;
}

.header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
}

.header h1 {
  margin: 0;
  color: var(--accent-gold, #ffd700);
  font-size: 26px;
}

.back-btn,
.add-btn,
.card-actions button,
.dialog-actions button,
.ai-btn,
.preset-tag {
  border-radius: 10px;
  font-weight: 600;
  transition: all 0.2s ease;
  cursor: pointer;
}

.back-btn,
.card-actions button,
.dialog-actions button,
.preset-tag {
  border: 1px solid var(--border-subtle, #374151);
  background: rgba(17, 24, 39, 0.76);
  color: var(--text-primary, #e5e7eb);
}

.back-btn {
  padding: 10px 14px;
}

.back-btn:hover,
.card-actions button:hover,
.dialog-actions button:hover,
.preset-tag:hover {
  border-color: var(--accent-gold, #ffd700);
  color: #fff;
}

.main {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-height: calc(100vh - 132px);
  overflow-y: auto;
  padding-right: 8px;
}

.section {
  border: 1px solid var(--border-subtle, #374151);
  border-radius: 16px;
  background: rgba(17, 24, 39, 0.82);
  padding: 18px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.section h2 {
  margin: 0;
  color: var(--accent-gold, #ffd700);
  font-size: 20px;
}

.add-btn {
  border: 1px solid rgba(74, 223, 106, 0.45);
  background: rgba(74, 223, 106, 0.18);
  color: #d1fae5;
  padding: 10px 14px;
}

.add-btn:hover {
  background: rgba(74, 223, 106, 0.28);
}

.characters-grid,
.subjects-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

.character-card,
.subject-card,
.persona-card {
  border: 1px solid var(--border-subtle, #374151);
  border-radius: 14px;
  padding: 16px;
  background: rgba(31, 41, 55, 0.72);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.character-card {
  cursor: pointer;
}

.character-card:hover {
  border-color: rgba(255, 215, 0, 0.52);
}

.character-card.selected {
  border-color: rgba(255, 215, 0, 0.75);
  box-shadow: 0 0 0 1px rgba(255, 215, 0, 0.3);
}

.char-avatar {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.34), rgba(255, 215, 0, 0.3));
  color: var(--accent-gold, #ffd700);
  font-size: 22px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.character-card h3,
.subject-card h3,
.persona-header h3 {
  margin: 0 0 8px;
  color: var(--text-primary, #f3f4f6);
}

.character-card p,
.subject-card p,
.traits,
.prompt-preview {
  margin: 0 0 10px;
  color: var(--text-secondary, #9ca3af);
  font-size: 13px;
  line-height: 1.45;
}

.target,
.role-tag,
.active-badge,
.version {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.target,
.active-badge {
  background: rgba(74, 223, 106, 0.18);
  border: 1px solid rgba(74, 223, 106, 0.45);
  color: #86efac;
}

.role-tag {
  margin-bottom: 8px;
  background: rgba(96, 165, 250, 0.2);
  border: 1px solid rgba(96, 165, 250, 0.45);
  color: #93c5fd;
}

.version {
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.35);
  color: #c7d2fe;
}

.personas-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.persona-card.active {
  border-color: rgba(74, 223, 106, 0.6);
}

.persona-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.card-actions button {
  padding: 6px 10px;
  font-size: 12px;
}

.card-actions .delete {
  border-color: rgba(248, 113, 113, 0.45);
  color: #fecaca;
}

.card-actions .delete:hover {
  background: rgba(127, 29, 29, 0.32);
}

.sprite-btn {
  border-color: rgba(96, 165, 250, 0.45) !important;
  color: #93c5fd !important;
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(3, 7, 18, 0.78);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.dialog {
  width: min(560px, 92vw);
  max-height: min(86vh, 920px);
  overflow-y: auto;
  border: 1px solid var(--border-subtle, #374151);
  border-radius: 16px;
  background: rgba(17, 24, 39, 0.92);
  padding: 22px;
}

.dialog h3 {
  margin: 0 0 14px;
  color: var(--accent-gold, #ffd700);
}

.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  color: var(--text-secondary, #d1d5db);
  margin-bottom: 6px;
  font-size: 13px;
}

.field-hint,
.label-hint,
.sprite-hint {
  margin: 6px 0 0;
  color: var(--text-muted, #9ca3af);
  font-size: 12px;
}

.form-group input,
.form-group textarea,
.form-group select,
.ai-input {
  width: 100%;
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #4b5563);
  background: rgba(3, 7, 18, 0.68);
  color: var(--text-primary, #f3f4f6);
  padding: 10px 12px;
  box-sizing: border-box;
}

.form-group textarea {
  min-height: 88px;
  resize: vertical;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus,
.ai-input:focus {
  outline: none;
  border-color: rgba(255, 215, 0, 0.7);
  box-shadow: 0 0 0 2px rgba(255, 215, 0, 0.15);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.dialog-actions button {
  padding: 9px 14px;
}

.dialog-actions button.primary,
.ai-btn {
  border: 1px solid rgba(255, 215, 0, 0.46);
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.88), rgba(251, 191, 36, 0.8));
  color: #111827;
}

.dialog-actions button.primary:hover,
.ai-btn:hover:not(:disabled) {
  filter: brightness(1.04);
}

.ai-generate {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.ai-btn {
  padding: 10px 14px;
  white-space: nowrap;
}

.ai-btn:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}

.preset-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-tag {
  font-size: 12px;
  padding: 7px 10px;
}

.preset-tag-active {
  border-color: rgba(255, 215, 0, 0.7);
  color: var(--accent-gold, #ffd700);
  background: rgba(255, 215, 0, 0.12);
}

.sprite-file-input {
  width: 100%;
  color: var(--text-secondary, #d1d5db);
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
  border-radius: 12px;
  background: rgba(74, 223, 106, 0.14);
  border: 1px solid rgba(74, 223, 106, 0.45);
  color: #86efac;
}

.error-toast {
  position: fixed;
  top: 22px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(185, 28, 28, 0.92);
  border: 1px solid rgba(248, 113, 113, 0.75);
  color: #fee2e2;
  border-radius: 10px;
  padding: 10px 18px;
  font-size: 13px;
}

@media (max-width: 900px) {
  .character-page {
    padding: 14px;
  }

  .main {
    max-height: none;
    overflow: visible;
    padding-right: 0;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .dialog {
    width: min(600px, 96vw);
    padding: 18px;
  }
}
</style>
