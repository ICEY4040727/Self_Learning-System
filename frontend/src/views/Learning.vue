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
      <!-- 最新教师回复 / 打字机 -->
      <div class="dialog-box-wrapper">
        <div class="dialog-name-tag" v-if="isTyping || lastTeacherReply">
          {{ teacherName }}
        </div>
        <div class="dialog-content">
          <div v-if="isTyping" class="dialog-text">
            {{ displayedText }}<span class="cursor">▊</span>
          </div>
          <div v-else-if="lastTeacherReply" class="dialog-text" v-html="formatMessage(lastTeacherReply)"></div>
          <div v-else class="dialog-text dialog-empty">{{ greeting || '……' }}</div>
        </div>
      </div>

      <!-- 选择面板（浮动在对话框上方） -->
      <ChoicePanel
        v-if="currentChoices.length > 0"
        :choices="currentChoices"
        @select="handleChoiceSelect"
      />

      <!-- 输入区域 -->
      <div class="input-area" v-if="currentChoices.length === 0 && !isTyping">
        <input
          v-model="inputText"
          type="text"
          placeholder="输入你的问题或想法..."
          @keyup.enter="sendMessage"
          :disabled="isLoading"
        />
        <button @click="sendMessage" :disabled="isLoading || !inputText.trim()">
          {{ isLoading ? '...' : '发送' }}
        </button>
      </div>
    </div>

    <!-- Layer 3: HUD 栏（placeholder，#98 完善） -->
    <div class="hud-layer">
      <div class="hud-left">
        <button class="hud-btn" @click="goBack">← 返回</button>
        <button class="hud-btn" @click="showSaveLoad = true">📁 存档</button>
      </div>
      <div class="hud-right">
        <EmotionIndicator :stage="relationshipStage" :emotion="currentEmotion" />
      </div>
    </div>

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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import ChoicePanel from '@/components/galgame/ChoicePanel.vue'
import EmotionIndicator from '@/components/galgame/EmotionIndicator.vue'
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

const scrollToBottom = () => {
  // No-op in Galgame layout (no scrolling area)
  // Kept for compatibility with existing calls
}

const startTyping = (fullText: string) => {
  isTyping.value = true
  displayedText.value = ''

  let index = 0
  typeInterval = window.setInterval(() => {
    if (index < fullText.length) {
      displayedText.value += fullText[index]
      index++
      scrollToBottom()
    } else {
      stopTyping()
      // 打字完成后：更新对话框显示 + 添加到消息列表（供 Backlog 使用）
      lastTeacherReply.value = fullText
      messages.value.push({
        id: Date.now(),
        sender_type: 'teacher',
        content: fullText
      })
      renderMermaid()
    }
  }, TYPE_SPEED)
}

const stopTyping = () => {
  if (typeInterval) {
    clearInterval(typeInterval)
    typeInterval = null
  }
  isTyping.value = false
}

const sendMessage = async () => {
  if (!inputText.value.trim() || isLoading.value || isTyping.value) return

  const userMsg = inputText.value.trim()
  inputText.value = ''
  isLoading.value = true

  // 添加用户消息
  messages.value.push({
    id: Date.now(),
    sender_type: 'user',
    content: userMsg
  })
  scrollToBottom()

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
      // 显示选项
      currentChoices.value = data.choices || []
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
    messages.value.push({
      id: Date.now(),
      sender_type: 'teacher',
      content: error.response?.data?.detail || '发送消息失败，请重试'
    })
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
  }
  showSaveLoad.value = false
  scrollToBottom()
  renderMermaid()
}

const goBack = () => {
  router.push('/home')
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
        }
        renderMermaid()
      }
    }
  } catch (error) {
    console.error('Failed to fetch session:', error)
  }
}

onMounted(async () => {
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
  background: radial-gradient(ellipse at bottom, #1a1a2e 0%, #0a0a1e 100%);
}

/* Layer 1: Character */
.character-layer {
  position: absolute;
  bottom: 240px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1;
}

.character-placeholder {
  display: flex;
  justify-content: center;
}

.char-avatar-large {
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, #4a4a8a, #2a2a4a);
  border: 3px solid #ffd700;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  color: #ffd700;
  box-shadow: 0 0 30px rgba(255, 215, 0, 0.2);
}

/* Layer 2: Dialog */
.dialog-layer {
  position: absolute;
  bottom: 50px;
  left: 5%;
  right: 5%;
  z-index: 2;
}

.dialog-box-wrapper {
  background: rgba(0, 0, 0, 0.85);
  border: 2px solid #ffd700;
  border-radius: 8px;
  padding: 20px 24px;
  min-height: 120px;
  max-height: 200px;
  overflow-y: auto;
  box-shadow: 0 0 20px rgba(255, 215, 0, 0.15);
}

.dialog-name-tag {
  display: inline-block;
  background: linear-gradient(90deg, #ffd700, #ff8c00);
  color: #1a1a2e;
  padding: 4px 16px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 14px;
  margin-bottom: 10px;
}

.dialog-content {
  margin-top: 5px;
}

.dialog-text {
  color: #fff;
  font-size: 16px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.dialog-empty {
  color: #888;
  font-style: italic;
}

.cursor {
  animation: blink 1s infinite;
  color: #ffd700;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* Input area (below dialog box) */
.input-area {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.input-area input {
  flex: 1;
  padding: 10px 16px;
  background: rgba(26, 26, 46, 0.9);
  border: 1px solid #4a4a8a;
  border-radius: 6px;
  color: #fff;
  font-size: 14px;
}

.input-area input:focus {
  outline: none;
  border-color: #ffd700;
}

.input-area input::placeholder {
  color: #666;
}

.input-area button {
  padding: 10px 20px;
  background: #4a8a4a;
  border: none;
  border-radius: 6px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.input-area button:hover:not(:disabled) {
  background: #5a9a5a;
}

.input-area button:disabled {
  background: #3a3a5a;
  cursor: not-allowed;
}

/* Layer 3: HUD */
.hud-layer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 44px;
  background: rgba(0, 0, 0, 0.7);
  border-top: 1px solid #4a4a8a;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  z-index: 3;
}

.hud-left, .hud-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hud-btn {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #4a4a8a;
  color: #aaa;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.hud-btn:hover {
  color: #ffd700;
  border-color: #ffd700;
}

/* Mermaid in dialog */
:deep(.mermaid-container) {
  margin: 12px 0;
  padding: 16px;
  background: rgba(42, 42, 74, 0.6);
  border: 1px solid #4a4a8a;
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
    bottom: 50px;
  }
  .dialog-box-wrapper {
    max-height: 45vh;
  }
}
</style>