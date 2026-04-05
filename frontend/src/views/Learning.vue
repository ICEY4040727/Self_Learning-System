<template>
  <div class="learning-page">
    <div class="scene-bg" :style="sceneStyle" @click="handleSceneClick"></div>
    <div class="scene-overlay"></div>

    <div class="character-layer">
      <CharacterDisplay :name="teacherName" :sprites="sageSprites" :expression="currentExpression" position="left" />
      <CharacterDisplay name="旅者" :sprites="travelerSprites" expression="default" position="right" />
    </div>

    <div v-if="!uiHidden" class="dialog-layer" @click.stop>
      <DialogBox
        :mode="dialogMode"
        :character-name="teacherName"
        :display-content="displayContent"
        :is-typing="isTyping"
        :has-more-segments="false"
        :choices="currentChoices"
        @click-next="handleDialogContinue"
        @skip-typing="skipTyping"
        @send-message="sendMessage"
        @select-choice="handleChoice"
      />
    </div>

    <div v-if="!uiHidden" class="hud-layer" @click.stop>
      <HudBar
        :emotion="currentEmotion"
        :stage="relationshipStage"
        :mastery="0"
        :is-auto="autoMode"
        @save="openCheckpointPanel('commit')"
        @load="openCheckpointPanel('branch')"
        @skip="handleSkip"
        @toggle-auto="toggleAutoMode"
        @backlog="showBacklog = true"
        @knowledge-graph="showKnowledgeGraph = true"
        @toggle-ui="uiHidden = true"
        @settings="router.push('/settings')"
        @exit="router.push('/home')"
      />
    </div>

    <button v-if="uiHidden" class="restore-ui" @click="uiHidden = false">🙈 UI已隐藏（点击恢复）</button>

    <div v-if="stageOverlay" class="stage-overlay">{{ stageOverlay }}</div>
    <div v-if="narration" class="narration">{{ narration }}</div>

    <BacklogPanel :visible="showBacklog" :messages="messages" :teacher-name="teacherName" @close="showBacklog = false" />

    <CheckpointPanel
      v-if="showCheckpointPanel"
      :world-id="worldId"
      :session-id="sessionId"
      :initial-mode="checkpointMode"
      @close="showCheckpointPanel = false"
      @branched="handleBranched"
    />

    <div v-if="showKnowledgeGraph" class="modal" @click.self="showKnowledgeGraph = false">
      <div class="modal-panel galgame-panel">
        <button class="close" @click="showKnowledgeGraph = false">✕</button>
        <KnowledgeGraph :world-id="worldId" :session-id="sessionId" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import CharacterDisplay from '@/components/galgame/CharacterDisplay.vue'
import DialogBox from '@/components/galgame/DialogBox.vue'
import HudBar from '@/components/galgame/HudBar.vue'
import BacklogPanel from '@/components/galgame/BacklogPanel.vue'
import CheckpointPanel from '@/components/galgame/CheckpointPanel.vue'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import { parseApiError } from '@/utils/error'
import { useAuthStore } from '@/stores/auth'
import { buildLearningRoute, parseQueryNumber } from '@/utils/navigation'

interface Message {
  id: number
  sender_type: 'user' | 'teacher'
  content: string
}

interface LearningStartResponse {
  session_id?: number
  teacher_persona?: string | null
  relationship_stage?: string | null
  relationship?: { stage?: string | null } | null
  greeting?: string | null
  scenes?: Record<string, string> | null
  sage_sprites?: Record<string, string> | null
  traveler_sprites?: Record<string, string> | null
  character_sprites?: Record<string, string> | null
}

interface HistoryMessage {
  id?: number
  sender_type?: string
  content?: string
}

interface RelationshipEvent {
  type?: string
  event_type?: string
  message?: string
  description?: string
}

interface ChatResponsePayload {
  type?: string
  reply?: string
  choices?: string[]
  emotion?: { emotion_type?: string } | null
  relationship_stage?: string | null
  relationship?: { stage?: string | null } | null
  relationship_events?: RelationshipEvent[] | null
  expression_hint?: string | null
}

interface BranchPayload {
  session_id: number
  course_id: number
  world_id?: number
}

type DialogMode = 'TEACHER_SPEAKING' | 'USER_INPUT' | 'CHOICES' | 'WAITING'
type CheckpointMode = 'commit' | 'branch'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const courseId = computed(() => Number(route.params.courseId))
const worldId = ref(parseQueryNumber(route.query.worldId) ?? 0)
const sessionId = ref<number | undefined>(parseQueryNumber(route.query.sessionId))
const teacherName = ref('知者')
const sageSprites = ref<Record<string, string>>({})
const travelerSprites = ref<Record<string, string>>({})
const scenes = ref<Record<string, string>>({})
const currentExpression = ref('default')
const currentEmotion = ref('neutral')
const relationshipStage = ref('stranger')
const fullTeacherReply = ref('……')
const typedTeacherReply = ref('……')
const isTyping = ref(false)
const currentChoices = ref<string[]>([])
const dialogMode = ref<DialogMode>('WAITING')
const messages = ref<Message[]>([])
const uiHidden = ref(false)
const autoMode = ref(false)
const showBacklog = ref(false)
const showCheckpointPanel = ref(false)
const checkpointMode = ref<CheckpointMode>('commit')
const showKnowledgeGraph = ref(false)
const stageOverlay = ref('')
const narration = ref('')

let typingTimer: ReturnType<typeof window.setInterval> | null = null
let autoAdvanceTimer: ReturnType<typeof window.setTimeout> | null = null

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })
const anyPanelOpen = computed(() => showBacklog.value || showCheckpointPanel.value || showKnowledgeGraph.value)

const sceneStyle = computed(() => {
  const stageScene = scenes.value[relationshipStage.value]
  const fallback = scenes.value.default || Object.values(scenes.value)[0]
  const url = stageScene || fallback
  return url
    ? { backgroundImage: `url(${url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
    : { background: 'radial-gradient(ellipse at bottom, var(--bg-secondary) 0%, var(--bg-primary) 100%)' }
})

const displayContent = computed(() => typedTeacherReply.value)

const clearTypingTimer = () => {
  if (typingTimer) {
    window.clearInterval(typingTimer)
    typingTimer = null
  }
}

const clearAutoAdvanceTimer = () => {
  if (autoAdvanceTimer) {
    window.clearTimeout(autoAdvanceTimer)
    autoAdvanceTimer = null
  }
}

const startTypewriter = (text: string) => {
  clearTypingTimer()
  fullTeacherReply.value = text || '……'
  typedTeacherReply.value = ''
  isTyping.value = true

  if (!fullTeacherReply.value) {
    isTyping.value = false
    return
  }

  let index = 0
  typingTimer = window.setInterval(() => {
    index += 1
    typedTeacherReply.value = fullTeacherReply.value.slice(0, index)
    if (index >= fullTeacherReply.value.length) {
      clearTypingTimer()
      isTyping.value = false
    }
  }, 38)
}

const skipTyping = () => {
  if (!isTyping.value) return
  clearTypingTimer()
  typedTeacherReply.value = fullTeacherReply.value
  isTyping.value = false
}

const showEvent = (text: string, type: 'stage' | 'narration') => {
  if (type === 'stage') {
    stageOverlay.value = text
    setTimeout(() => (stageOverlay.value = ''), 2000)
  } else {
    narration.value = text
    setTimeout(() => (narration.value = ''), 2800)
  }
}

const applyRelationship = (data: ChatResponsePayload) => {
  if (data.relationship?.stage) relationshipStage.value = data.relationship.stage
  if (data.relationship_stage) relationshipStage.value = data.relationship_stage
  if (Array.isArray(data.relationship_events)) {
    data.relationship_events.forEach((event) => {
      const eventType = event.event_type || event.type || ''
      const message = event.message || event.description || JSON.stringify(event)
      showEvent(message, eventType.includes('stage') ? 'stage' : 'narration')
    })
  }
}

const presentTeacherReply = (reply: string, appendToHistory = true) => {
  const normalizedReply = reply || '……'
  startTypewriter(normalizedReply)
  if (appendToHistory) {
    messages.value.push({ id: Date.now(), sender_type: 'teacher', content: normalizedReply })
  }
}

const resetLearningState = () => {
  clearTypingTimer()
  clearAutoAdvanceTimer()
  messages.value = []
  currentChoices.value = []
  dialogMode.value = 'WAITING'
  fullTeacherReply.value = '……'
  typedTeacherReply.value = '……'
  isTyping.value = false
  currentExpression.value = 'default'
  currentEmotion.value = 'neutral'
}

const startLearning = async () => {
  const startRes = await axios.post<LearningStartResponse>(`/api/courses/${courseId.value}/start`, {}, { headers: headers() })
  const data = startRes.data
  sessionId.value = data.session_id
  teacherName.value = data.teacher_persona || '知者'
  sageSprites.value = data.sage_sprites || data.character_sprites || {}
  travelerSprites.value = data.traveler_sprites || {}
  scenes.value = data.scenes || {}
  if (data.relationship?.stage) relationshipStage.value = data.relationship.stage
  if (data.relationship_stage) relationshipStage.value = data.relationship_stage

  if (sessionId.value) {
    const historyRes = await axios.get<HistoryMessage[]>(`/api/sessions/${sessionId.value}/history`, { headers: headers() })
    const history = Array.isArray(historyRes.data) ? historyRes.data : []
    if (history.length > 0) {
      messages.value = history.map((msg) => ({
        id: msg.id || Date.now(),
        sender_type: msg.sender_type === 'user' ? 'user' : 'teacher',
        content: msg.content || '',
      }))
      const lastTeacher = [...messages.value].reverse().find((msg) => msg.sender_type === 'teacher')
      presentTeacherReply(lastTeacher?.content || data.greeting || '准备好开始学习了吗？', false)
      dialogMode.value = 'TEACHER_SPEAKING'
      return
    }
  }

  presentTeacherReply(data.greeting || '准备好开始学习了吗？')
  dialogMode.value = 'TEACHER_SPEAKING'
}

const fetchCourse = async () => {
  if (worldId.value) return
  const res = await axios.get(`/api/courses/${courseId.value}`, { headers: headers() })
  worldId.value = res.data.world_id
}

const sendMessage = async (message: string) => {
  if (!message.trim()) return
  messages.value.push({ id: Date.now(), sender_type: 'user', content: message })
  currentChoices.value = []
  dialogMode.value = 'WAITING'

  try {
    const res = await axios.post<ChatResponsePayload>(`/api/courses/${courseId.value}/chat`, { message }, { headers: headers() })
    const data = res.data
    currentEmotion.value = data.emotion?.emotion_type || currentEmotion.value
    currentExpression.value = data.expression_hint || 'default'
    applyRelationship(data)

    const isChoiceReply = data.type === 'choice' || (Array.isArray(data.choices) && data.choices.length > 0)
    if (isChoiceReply) {
      currentChoices.value = data.choices || []
      presentTeacherReply(data.reply || '')
      dialogMode.value = 'CHOICES'
      return
    }

    presentTeacherReply(data.reply || '')
    dialogMode.value = 'TEACHER_SPEAKING'
  } catch (error) {
    presentTeacherReply(parseApiError(error))
    dialogMode.value = 'TEACHER_SPEAKING'
  }
}

const handleChoice = (choice: string) => sendMessage(choice)

const openCheckpointPanel = (mode: CheckpointMode) => {
  checkpointMode.value = mode
  showCheckpointPanel.value = true
}

const handleDialogContinue = () => {
  if (dialogMode.value !== 'TEACHER_SPEAKING') return
  if (isTyping.value) {
    skipTyping()
    return
  }
  dialogMode.value = 'USER_INPUT'
}

const handleSkip = () => {
  if (dialogMode.value !== 'TEACHER_SPEAKING') return
  if (isTyping.value) {
    skipTyping()
    return
  }
  dialogMode.value = 'USER_INPUT'
}

const toggleAutoMode = () => {
  autoMode.value = !autoMode.value
}

const handleSceneClick = () => {
  if (uiHidden.value) {
    uiHidden.value = false
    return
  }
  if (!anyPanelOpen.value) uiHidden.value = true
}

const handleBranched = (payload: BranchPayload) => {
  showCheckpointPanel.value = false
  sessionId.value = payload.session_id
  const nextWorldId = payload.world_id || worldId.value
  if (payload.course_id !== courseId.value) {
    router.push(buildLearningRoute(payload.course_id, {
      worldId: nextWorldId,
      sessionId: payload.session_id,
    }))
    return
  }
  void router.replace(buildLearningRoute(payload.course_id, {
    worldId: nextWorldId,
    sessionId: payload.session_id,
  }))
}

const bootstrapLearning = async () => {
  worldId.value = parseQueryNumber(route.query.worldId) ?? 0
  sessionId.value = parseQueryNumber(route.query.sessionId)
  resetLearningState()
  try {
    await fetchCourse()
    await startLearning()
  } catch (error) {
    showEvent(parseApiError(error), 'narration')
    void router.push('/home')
  }
}

watch(
  () => route.fullPath,
  () => {
    void bootstrapLearning()
  },
  { immediate: true },
)

watch(
  () => [autoMode.value, dialogMode.value, isTyping.value, anyPanelOpen.value, uiHidden.value] as const,
  ([auto, mode, typing, panelOpen, hidden]) => {
    clearAutoAdvanceTimer()
    if (!auto || mode !== 'TEACHER_SPEAKING' || typing || panelOpen || hidden) return
    autoAdvanceTimer = window.setTimeout(() => {
      dialogMode.value = 'USER_INPUT'
    }, 2800)
  },
)

onBeforeUnmount(() => {
  clearTypingTimer()
  clearAutoAdvanceTimer()
})
</script>

<style scoped>
.learning-page { width: 100vw; height: 100vh; position: relative; overflow: hidden; }
.scene-bg { position: absolute; inset: 0; z-index: 0; filter: brightness(.58); }
.scene-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(to bottom, rgba(6, 8, 18, 0.2), rgba(0, 0, 0, 0.35));
}
.character-layer { position: absolute; left: 0; right: 0; bottom: 220px; z-index: 10; display: flex; justify-content: space-between; padding: 0 5%; pointer-events: none; }
.dialog-layer { position: absolute; left: 5%; right: 5%; bottom: 44px; z-index: 20; }
.hud-layer { position: fixed; inset: 0; pointer-events: none; z-index: 30; }
.hud-layer :deep(.hud-bar) { pointer-events: auto; }
.restore-ui { position: fixed; right: 14px; bottom: 56px; z-index: 40; background: rgba(0,0,0,.75); color: #fff; border: 1px solid #4a4a8a; border-radius: var(--radius-hud-btn); padding: 8px 10px; cursor: pointer; }
.stage-overlay { position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; font-size: 36px; color: #ffd700; background: rgba(0,0,0,.65); font-family: var(--font-dialogue); }
.narration { position: fixed; right: 5%; bottom: 240px; z-index: 45; background: rgba(0,0,0,.72); border: 1px solid #4a4a8a; border-radius: 10px; padding: 12px 14px; max-width: 360px; }
.modal { position: fixed; inset: 0; z-index: 1100; background: rgba(0,0,0,.65); display: flex; align-items: center; justify-content: center; }
.modal-panel { width: min(92vw, 980px); max-height: 88vh; overflow: auto; border-radius: var(--radius-modal); padding: 16px; position: relative; }
.close { position: absolute; right: 12px; top: 10px; background: none; border: none; color: #aaa; cursor: pointer; font-size: 18px; }
@media (max-width: 768px) {
  .character-layer { bottom: 180px; transform: scale(.7); transform-origin: bottom center; }
  .dialog-layer { left: 2%; right: 2%; }
  .narration { right: 2%; max-width: 76vw; }
}
</style>
