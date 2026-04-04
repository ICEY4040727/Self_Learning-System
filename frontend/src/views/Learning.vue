<template>
  <div class="learning-page">
    <div class="scene-bg" :style="sceneStyle"></div>

    <div class="character-layer">
      <CharacterDisplay :name="teacherName" :sprites="sageSprites" :expression="currentExpression" position="left" />
      <CharacterDisplay name="旅者" :sprites="travelerSprites" expression="default" position="right" />
    </div>

    <div v-if="!uiHidden" class="dialog-layer">
      <DialogBox
        :mode="dialogMode"
        :character-name="teacherName"
        :display-content="displayContent"
        :choices="currentChoices"
        @click-next="dialogMode = 'USER_INPUT'"
        @send-message="sendMessage"
        @select-choice="handleChoice"
      />
    </div>

    <HudBar
      v-if="!uiHidden"
      :emotion="currentEmotion"
      :stage="relationshipStage"
      :mastery="0"
      :is-auto="false"
      @save="showCheckpointPanel = true"
      @load="showCheckpointPanel = true"
      @skip="dialogMode = 'USER_INPUT'"
      @toggle-auto="void 0"
      @backlog="showBacklog = true"
      @knowledge-graph="showKnowledgeGraph = true"
      @toggle-ui="uiHidden = true"
      @settings="router.push('/settings')"
      @exit="router.push('/home')"
    />

    <button v-if="uiHidden" class="restore-ui" @click="uiHidden = false">🙈 UI已隐藏（点击恢复）</button>

    <div v-if="stageOverlay" class="stage-overlay">{{ stageOverlay }}</div>
    <div v-if="narration" class="narration">{{ narration }}</div>

    <BacklogPanel :visible="showBacklog" :messages="messages" :teacher-name="teacherName" @close="showBacklog = false" />

    <CheckpointPanel
      v-if="showCheckpointPanel"
      :world-id="worldId"
      :session-id="sessionId"
      @close="showCheckpointPanel = false"
      @branched="handleBranched"
    />

    <div v-if="showKnowledgeGraph" class="modal" @click.self="showKnowledgeGraph = false">
      <div class="modal-panel">
        <button class="close" @click="showKnowledgeGraph = false">✕</button>
        <KnowledgeGraph :world-id="worldId" :session-id="sessionId" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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

interface Message {
  id: number
  sender_type: 'user' | 'teacher'
  content: string
}

type DialogMode = 'TEACHER_SPEAKING' | 'USER_INPUT' | 'CHOICES' | 'WAITING'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const courseId = computed(() => Number(route.params.courseId || route.params.subjectId))
const worldId = ref(Number(route.query.worldId || 0))
const sessionId = ref<number>()
const teacherName = ref('知者')
const sageSprites = ref<Record<string, string>>({})
const travelerSprites = ref<Record<string, string>>({})
const scenes = ref<Record<string, string>>({})
const currentExpression = ref('default')
const currentEmotion = ref('neutral')
const relationshipStage = ref('stranger')
const lastTeacherReply = ref('……')
const currentChoices = ref<string[]>([])
const dialogMode = ref<DialogMode>('WAITING')
const messages = ref<Message[]>([])
const uiHidden = ref(false)
const showBacklog = ref(false)
const showCheckpointPanel = ref(false)
const showKnowledgeGraph = ref(false)
const stageOverlay = ref('')
const narration = ref('')

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })

const sceneStyle = computed(() => {
  const stageScene = scenes.value[relationshipStage.value]
  const fallback = scenes.value.default || Object.values(scenes.value)[0]
  const url = stageScene || fallback
  return url
    ? { backgroundImage: `url(${url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
    : { background: 'radial-gradient(ellipse at bottom, var(--bg-secondary) 0%, var(--bg-primary) 100%)' }
})

const displayContent = computed(() => lastTeacherReply.value)

const showEvent = (text: string, type: 'stage' | 'narration') => {
  if (type === 'stage') {
    stageOverlay.value = text
    setTimeout(() => (stageOverlay.value = ''), 2000)
  } else {
    narration.value = text
    setTimeout(() => (narration.value = ''), 2800)
  }
}

const applyRelationship = (data: any) => {
  if (data.relationship?.stage) relationshipStage.value = data.relationship.stage
  if (data.relationship_stage) relationshipStage.value = data.relationship_stage
  if (Array.isArray(data.relationship_events)) {
    data.relationship_events.forEach((event: any) => {
      const eventType = event.event_type || event.type || ''
      const message = event.message || event.description || JSON.stringify(event)
      showEvent(message, eventType.includes('stage') ? 'stage' : 'narration')
    })
  }
}

const pushTeacherReply = (reply: string) => {
  lastTeacherReply.value = reply || '……'
  messages.value.push({ id: Date.now(), sender_type: 'teacher', content: lastTeacherReply.value })
}

const startLearning = async () => {
  const startRes = await axios.post(`/api/courses/${courseId.value}/start`, {}, { headers: headers() })
  const data = startRes.data
  sessionId.value = data.session_id
  teacherName.value = data.teacher_persona || '知者'
  sageSprites.value = data.sage_sprites || data.character_sprites || {}
  travelerSprites.value = data.traveler_sprites || {}
  scenes.value = data.scenes || {}
  if (data.relationship?.stage) relationshipStage.value = data.relationship.stage
  if (data.relationship_stage) relationshipStage.value = data.relationship_stage

  if (sessionId.value) {
    const historyRes = await axios.get(`/api/sessions/${sessionId.value}/history`, { headers: headers() })
    const history = Array.isArray(historyRes.data) ? historyRes.data : []
    if (history.length > 0) {
      messages.value = history.map((msg: any) => ({
        id: msg.id || Date.now(),
        sender_type: msg.sender_type,
        content: msg.content,
      }))
      const lastTeacher = [...messages.value].reverse().find((msg) => msg.sender_type === 'teacher')
      lastTeacherReply.value = lastTeacher?.content || data.greeting || '准备好开始学习了吗？'
      dialogMode.value = 'TEACHER_SPEAKING'
      return
    }
  }

  pushTeacherReply(data.greeting || '准备好开始学习了吗？')
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
  dialogMode.value = 'WAITING'
  try {
    const res = await axios.post(`/api/courses/${courseId.value}/chat`, { message }, { headers: headers() })
    const data = res.data
    currentEmotion.value = data.emotion?.emotion_type || currentEmotion.value
    currentExpression.value = data.expression_hint || 'default'
    applyRelationship(data)

    if (data.type === 'choice') {
      currentChoices.value = data.choices || []
      pushTeacherReply(data.reply || '')
      dialogMode.value = 'CHOICES'
      return
    }

    currentChoices.value = []
    pushTeacherReply(data.reply || '')
    dialogMode.value = 'TEACHER_SPEAKING'
  } catch (error) {
    pushTeacherReply(parseApiError(error))
    dialogMode.value = 'TEACHER_SPEAKING'
  }
}

const handleChoice = (choice: string) => sendMessage(choice)

const handleBranched = (payload: { session_id: number; course_id: number }) => {
  sessionId.value = payload.session_id
  if (payload.course_id !== courseId.value) {
    router.push(`/learning/${payload.course_id}`)
    return
  }
  void startLearning()
}

onMounted(async () => {
  try {
    await fetchCourse()
    await startLearning()
  } catch (error) {
    alert(parseApiError(error))
    router.push('/home')
  }
})
</script>

<style scoped>
.learning-page { width: 100vw; height: 100vh; position: relative; overflow: hidden; }
.scene-bg { position: absolute; inset: 0; z-index: 0; filter: brightness(.58); }
.character-layer { position: absolute; left: 0; right: 0; bottom: 220px; z-index: 10; display: flex; justify-content: space-between; padding: 0 5%; pointer-events: none; }
.dialog-layer { position: absolute; left: 5%; right: 5%; bottom: 44px; z-index: 20; }
.restore-ui { position: fixed; right: 14px; bottom: 56px; z-index: 40; background: rgba(0,0,0,.75); color: #fff; border: 1px solid #4a4a8a; border-radius: 8px; padding: 8px 10px; cursor: pointer; }
.stage-overlay { position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; font-size: 36px; color: #ffd700; background: rgba(0,0,0,.65); font-family: var(--font-dialogue); }
.narration { position: fixed; right: 5%; bottom: 240px; z-index: 45; background: rgba(0,0,0,.72); border: 1px solid #4a4a8a; border-radius: 10px; padding: 12px 14px; max-width: 360px; }
.modal { position: fixed; inset: 0; z-index: 1100; background: rgba(0,0,0,.65); display: flex; align-items: center; justify-content: center; }
.modal-panel { width: min(92vw, 980px); max-height: 88vh; overflow: auto; background: #0f1022; border: 1px solid #4a4a8a; border-radius: 12px; padding: 16px; position: relative; }
.close { position: absolute; right: 12px; top: 10px; background: none; border: none; color: #aaa; cursor: pointer; }
@media (max-width: 768px) {
  .character-layer { bottom: 180px; transform: scale(.7); transform-origin: bottom center; }
  .dialog-layer { left: 2%; right: 2%; }
}
</style>
