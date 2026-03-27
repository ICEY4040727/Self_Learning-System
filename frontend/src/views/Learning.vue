<template>
  <div class="learning-page">
    <!-- Layer 0: 场景背景 -->
    <div class="scene-layer">
      <div class="scene-bg"></div>
    </div>

    <!-- Layer 1: 角色层 -->
    <div class="character-layer">
      <div class="character-placeholder">
        <div class="char-avatar-large">{{ teacherName?.[0] || '?' }}</div>
      </div>
    </div>

    <!-- Layer 2: 对话框层 -->
    <div class="dialog-layer">
      <DialogBox
        :mode="dialogMode"
        :character-name="teacherName"
        :display-content="currentDisplayContent"
        :is-typing="isTyping"
        :choices="currentChoices"
        :has-more-segments="hasMoreSegments"
        @click-next="handleClickNext"
        @skip-typing="skipTyping"
        @send-message="handleSendFromDialog"
        @select-choice="handleChoiceSelect"
      />
    </div>

    <!-- Layer 3: HUD -->
    <HudBar
      :emotion="currentEmotion"
      :stage="relationshipStage"
      :mastery="0"
      :is-auto="isAuto"
      @save="showSaveLoad = true"
      @load="showSaveLoad = true"
      @skip="skipTyping"
      @toggle-auto="isAuto = !isAuto"
      @backlog="showBacklog = true"
      @settings="router.push('/settings')"
      @exit="confirmExit"
    />

    <!-- 模态层 -->
    <ToolConfirmDialog
      v-if="showToolConfirm"
      :tool="toolRequest.tool"
      :query="toolRequest.query"
      :reason="toolRequest.reason"
      @confirm="executeTool"
      @cancel="cancelTool"
    />

    <SaveLoad
      v-if="showSaveLoad"
      :subject-id="subjectId"
      :session-id="sessionId"
      @close="showSaveLoad = false"
      @load="handleLoadSave"
    />

    <BacklogPanel
      :visible="showBacklog"
      :messages="messages"
      :teacher-name="teacherName"
      @close="showBacklog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import DialogBox from '@/components/galgame/DialogBox.vue'
import HudBar from '@/components/galgame/HudBar.vue'
import BacklogPanel from '@/components/galgame/BacklogPanel.vue'
import SaveLoad from '@/components/galgame/SaveLoad.vue'
import ToolConfirmDialog from '@/components/galgame/ToolConfirmDialog.vue'
import mermaid from 'mermaid'
import DOMPurify from 'dompurify'

interface ChatMessage {
  id: number
  sender_type: 'user' | 'teacher'
  content: string
  emotion?: {
    valence: number
    emotion_type: string
  }
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const subjectId = ref(parseInt(route.params.subjectId as string))
const subjectName = ref('加载中...')
const teacherName = ref('教师')
const relationshipStage = ref('stranger')
const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const isLoading = ref(false)
const isTyping = ref(false)
const displayedText = ref('')
const currentChoices = ref<string[]>([])
const showToolConfirm = ref(false)
const showSaveLoad = ref(false)
const sessionId = ref<number | undefined>(undefined)
const currentEmotion = ref('')
const toolRequest = ref({ tool: '', query: '', reason: '' })
const lastTeacherReply = ref('')
const greeting = ref('')
const showBacklog = ref(false)
const isAuto = ref(false)
let autoTimer: number | null = null

type DialogMode = 'TEACHER_SPEAKING' | 'USER_INPUT' | 'CHOICES' | 'WAITING'
const dialogMode = ref<DialogMode>('WAITING')

// Segmentation for long replies
const segments = ref<string[]>([])
const currentSegmentIndex = ref(0)
const hasMoreSegments = computed(() => currentSegmentIndex.value < segments.value.length - 1)

const splitIntoSegments = (text: string): string[] => {
  // Split by double newlines (paragraph breaks)
  const paragraphs = text.split(/\n\n+/).filter(Boolean)
  if (paragraphs.length > 1) return paragraphs

  // Single long paragraph: split at sentence boundaries around 200 chars
  if (text.length > 250) {
    const result: string[] = []
    let remaining = text
    while (remaining.length > 250) {
      // Primary: split at sentence-ending punctuation
      let cutPoint = remaining.slice(0, 300).search(/[。！？.!?\n][^。！？.!?\n]*$/)
      // Fallback: split at clause-level punctuation (，；：,;:)
      if (cutPoint <= 100) {
        cutPoint = remaining.slice(0, 300).search(/[，；：,;:][^，；：,;:]*$/)
      }
      if (cutPoint > 80) {
        result.push(remaining.slice(0, cutPoint + 1))
        remaining = remaining.slice(cutPoint + 1).trimStart()
      } else {
        break
      }
    }
    if (remaining) result.push(remaining)
    if (result.length > 1) return result
  }

  return [text]
}

const currentDisplayContent = computed(() => {
  if (dialogMode.value === 'TEACHER_SPEAKING') {
    if (isTyping.value) return displayedText.value
    // Show current segment formatted
    const seg = segments.value[currentSegmentIndex.value]
    return seg ? formatMessage(seg) : formatMessage(lastTeacherReply.value)
  }
  if (dialogMode.value === 'CHOICES') {
    return formatMessage(lastTeacherReply.value)
  }
  if (dialogMode.value === 'WAITING' && !lastTeacherReply.value) {
    return greeting.value || '……'
  }
  return ''
})

// 打字机效果
let typeInterval: number | null = null
const TYPE_SPEED = 30 // ms per character

let mermaidCounter = 0

const formatMessage = (content: string) => {
  // Replace mermaid code blocks with render containers
  const formatted = content.replace(/```mermaid\n([\s\S]*?)```/g, (_match, code) => {
    const id = `mermaid-${++mermaidCounter}`
    return `<div class="mermaid-container"><pre class="mermaid" id="${id}">${code.trim()}</pre></div>`
  })
  // Convert remaining newlines to <br>, then sanitize
  const html = formatted.replace(/\n/g, '<br>')
  return DOMPurify.sanitize(html, {
    ADD_TAGS: ['pre', 'div'],
    ADD_ATTR: ['class', 'id'],
  })
}

const renderMermaid = () => {
  nextTick(async () => {
    const elements = document.querySelectorAll('.mermaid[data-processed]')
    // Clear previously processed flag for re-render
    elements.forEach(el => el.removeAttribute('data-processed'))
    try {
      await mermaid.run({ querySelector: '.mermaid' })
    } catch (e) {
      console.warn('Mermaid render failed:', e)
    }
  })
}

let typingResolve: (() => void) | null = null

const startTyping = (fullText: string): Promise<void> => {
  return new Promise((resolve) => {
    typingResolve = resolve
    currentFullText.value = fullText

    // Split into segments for long replies
    segments.value = splitIntoSegments(fullText)
    currentSegmentIndex.value = 0

    // Type the first segment
    typeSegment(segments.value[0])
  })
}

const typeSegment = (text: string) => {
  isTyping.value = true
  dialogMode.value = 'TEACHER_SPEAKING'
  displayedText.value = ''

  let index = 0
  typeInterval = window.setInterval(() => {
    if (index < text.length) {
      displayedText.value += text[index]
      index++
    } else {
      stopTyping()
      // If more segments remain, wait for click; otherwise finish
      if (!hasMoreSegments.value) {
        finishAllSegments()
      }
      // else: stay in TEACHER_SPEAKING, user clicks to advance
    }
  }, TYPE_SPEED)
}

const advanceSegment = () => {
  if (hasMoreSegments.value) {
    currentSegmentIndex.value++
    typeSegment(segments.value[currentSegmentIndex.value])
  } else {
    // All segments shown, switch to input
    dialogMode.value = 'USER_INPUT'
  }
}

const finishAllSegments = () => {
  // Record full reply to messages (for Backlog)
  lastTeacherReply.value = currentFullText.value
  messages.value.push({
    id: Date.now(),
    sender_type: 'teacher',
    content: currentFullText.value
  })
  renderMermaid()

  if (typingResolve) {
    typingResolve()
    typingResolve = null
  }

  // Auto mode
  if (isAuto.value && currentChoices.value.length === 0) {
    autoTimer = window.setTimeout(() => {
      dialogMode.value = 'USER_INPUT'
    }, 2000)
  }
}

const stopTyping = () => {
  if (typeInterval) {
    clearInterval(typeInterval)
    typeInterval = null
  }
  isTyping.value = false
}

// Store current full text for skip functionality
const currentFullText = ref('')

const skipTyping = () => {
  if (isTyping.value) {
    // Skip current segment's typewriter animation
    stopTyping()
    displayedText.value = segments.value[currentSegmentIndex.value] || currentFullText.value
    if (!hasMoreSegments.value) {
      finishAllSegments()
    }
    return
  }
}

const handleClickNext = () => {
  if (autoTimer) {
    clearTimeout(autoTimer)
    autoTimer = null
  }
  if (hasMoreSegments.value) {
    advanceSegment()
  } else {
    dialogMode.value = 'USER_INPUT'
  }
}

const handleSendFromDialog = (message: string) => {
  inputText.value = message
  sendMessage()
}

const confirmExit = () => {
  if (confirm('确定要返回主页吗？当前对话不会丢失。')) {
    router.push('/home')
  }
}

const sendMessage = async () => {
  if (!inputText.value.trim() || isLoading.value || isTyping.value) return

  const userMsg = inputText.value.trim()
  inputText.value = ''
  isLoading.value = true
  dialogMode.value = 'WAITING'

  // 添加用户消息到 Backlog
  messages.value.push({
    id: Date.now(),
    sender_type: 'user',
    content: userMsg
  })

  try {
    const response = await axios.post(
      `/api/subjects/${subjectId.value}/chat`,
      { message: userMsg },
      {
        headers: { Authorization: `Bearer ${authStore.token}` }
      }
    )

    const data = response.data

    // 处理不同响应类型
    if (data.type === 'tool_request') {
      // Show teacher reply first (strip tool tags)
      if (data.reply) {
        const cleanReply = data.reply.replace(/<tool>[\s\S]*?<\/tool>/g, '').trim()
        if (cleanReply) {
          await startTyping(cleanReply)
        }
      }
      // Then show tool confirmation
      toolRequest.value = {
        tool: data.tool || 'search',
        query: data.query || userMsg,
        reason: data.reason || '需要查找相关信息'
      }
      showToolConfirm.value = true
    } else if (data.type === 'choice') {
      // 显示选项 + 记录到 Backlog
      currentChoices.value = data.choices || []
      lastTeacherReply.value = data.reply || ''
      if (data.reply) {
        messages.value.push({
          id: Date.now(),
          sender_type: 'teacher',
          content: data.reply
        })
      }
      if (data.emotion?.emotion_type) {
        currentEmotion.value = data.emotion.emotion_type
      }
      if (data.relationship_stage) {
        relationshipStage.value = data.relationship_stage
      }
      dialogMode.value = 'CHOICES'
    } else {
      // 显示教师回复 (打字机效果)
      await startTyping(data.reply)

      // 更新情感状态与关系阶段
      if (data.emotion?.emotion_type) {
        currentEmotion.value = data.emotion.emotion_type
      }
      if (data.relationship_stage) {
        relationshipStage.value = data.relationship_stage
      }
    }
  } catch (error: any) {
    console.error('Send message error:', error)
    lastTeacherReply.value = error.response?.data?.detail || '发送消息失败，请重试'
    messages.value.push({
      id: Date.now(),
      sender_type: 'teacher',
      content: lastTeacherReply.value
    })
    dialogMode.value = 'USER_INPUT'
  } finally {
    isLoading.value = false
  }
}

const handleChoiceSelect = async (choice: string) => {
  inputText.value = choice
  currentChoices.value = []
  await sendMessage()
}

const executeTool = async () => {
  showToolConfirm.value = false

  // 调用工具确认API
  try {
    await axios.post(
      '/api/chat/tool_confirm',
      {
        tool: toolRequest.value.tool,
        query: toolRequest.value.query,
        reason: toolRequest.value.reason
      },
      {
        headers: { Authorization: `Bearer ${authStore.token}` }
      }
    )
  } catch (error) {
    console.error('Tool execution error:', error)
  }
}

const cancelTool = () => {
  showToolConfirm.value = false
}

const handleLoadSave = (saveData: any) => {
  // 恢复存档状态
  if (saveData.relationship_stage) {
    relationshipStage.value = saveData.relationship_stage
  }
  if (saveData.chat_history) {
    messages.value = saveData.chat_history
    const lastTeacher = [...messages.value].reverse().find(m => m.sender_type === 'teacher')
    if (lastTeacher) {
      lastTeacherReply.value = lastTeacher.content
      dialogMode.value = 'TEACHER_SPEAKING'
    } else {
      dialogMode.value = 'USER_INPUT'
    }
  }
  showSaveLoad.value = false
  renderMermaid()
}

const fetchSubjectInfo = async () => {
  try {
    const response = await axios.get(`/api/subjects/${subjectId.value}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    subjectName.value = response.data.name
  } catch (error) {
    console.error('Failed to fetch subject:', error)
  }
}

const fetchActiveSession = async () => {
  try {
    // 获取最近的会话历史
    const response = await axios.post(`/api/subjects/${subjectId.value}/start`, {}, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })

    if (response.data.teacher_persona) {
      teacherName.value = response.data.teacher_persona
    }
    if (response.data.greeting) {
      greeting.value = response.data.greeting
    }
    if (response.data.relationship_stage) {
      relationshipStage.value = response.data.relationship_stage
    }

    if (response.data.session_id) {
      sessionId.value = response.data.session_id
      // 获取会话历史（保留在 messages 供 Backlog 使用）
      const historyRes = await axios.get(
        `/api/sessions/${response.data.session_id}/history`,
        { headers: { Authorization: `Bearer ${authStore.token}` } }
      )

      if (historyRes.data && historyRes.data.length > 0) {
        messages.value = historyRes.data.map((m: any) => ({
          id: m.id,
          sender_type: m.sender_type,
          content: m.content
        }))
        // 恢复最后一条教师回复到对话框
        const lastTeacher = [...messages.value].reverse().find(m => m.sender_type === 'teacher')
        if (lastTeacher) {
          lastTeacherReply.value = lastTeacher.content
          dialogMode.value = 'TEACHER_SPEAKING'
        }
        renderMermaid()
      } else {
        // 新 session，显示 greeting 后等待输入
        dialogMode.value = 'USER_INPUT'
      }
    }
  } catch (error) {
    console.error('Failed to fetch session:', error)
  }
}

// Cleanup moved to bottom onUnmounted

// Keyboard support
const handleKeyDown = (e: KeyboardEvent) => {
  // Don't intercept when typing in input
  if (dialogMode.value === 'USER_INPUT') return
  // Don't intercept when modals are open
  if (showSaveLoad.value || showBacklog.value || showToolConfirm.value) return

  if (e.code === 'Space' || e.code === 'Enter') {
    if (isTyping.value) {
      e.preventDefault()
      skipTyping()
    } else if (dialogMode.value === 'TEACHER_SPEAKING') {
      e.preventDefault()
      handleClickNext()
    }
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)
  mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    themeVariables: {
      primaryColor: '#4a4a8a',
      primaryTextColor: '#fff',
      primaryBorderColor: '#ffd700',
      lineColor: '#888',
      secondaryColor: '#2a2a4a',
      tertiaryColor: '#1a1a2e',
    },
  })
  await fetchSubjectInfo()
  await fetchActiveSession()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  if (typeInterval) clearInterval(typeInterval)
  if (autoTimer) clearTimeout(autoTimer)
})
</script>

<style scoped>
/* === Galgame Four-Layer Layout === */
.learning-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* Layer 0: Scene Background */
.scene-layer {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.scene-bg {
  width: 100%;
  height: 100%;
  background: radial-gradient(ellipse at bottom, var(--bg-secondary) 0%, var(--bg-primary) 100%);
}

/* Layer 1: Character */
.character-layer {
  position: absolute;
  bottom: 280px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  animation: fadeSlideIn var(--transition-slow);
}

.character-placeholder {
  display: flex;
  justify-content: center;
}

.char-avatar-large {
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, #4a4a8a, #2a2a4a);
  border: 3px solid var(--accent-gold);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  color: var(--accent-gold);
  box-shadow: 0 0 30px rgba(255, 215, 0, 0.2);
}

/* Layer 2: Dialog */
.dialog-layer {
  position: absolute;
  bottom: 44px;
  left: 5%;
  right: 5%;
  z-index: 20;
}

/* Mermaid in dialog */
:deep(.mermaid-container) {
  margin: 12px 0;
  padding: 16px;
  background: rgba(42, 42, 74, 0.6);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  overflow-x: auto;
}

:deep(.mermaid-container svg) {
  max-width: 100%;
  height: auto;
}

/* Mobile */
@media (max-width: 768px) {
  .character-layer {
    display: none;
  }
  .dialog-layer {
    left: 2%;
    right: 2%;
  }
}
</style>