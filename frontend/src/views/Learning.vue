<template>
  <div class="learning-page">
    <!-- 顶部导航 -->
    <header class="header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h2>{{ subjectName }}</h2>
      <div class="header-actions">
        <EmotionIndicator :stage="relationshipStage" :emotion="currentEmotion" />
        <button class="save-btn" @click="showSaveLoad = true">存档/读档</button>
      </div>
    </header>

    <!-- 对话区域 -->
    <main class="dialog-area" ref="dialogArea">
      <div class="messages-container">
        <div
          v-for="msg in messages"
          :key="msg.id"
          :class="['message', msg.sender_type]"
        >
          <div v-if="msg.sender_type === 'teacher'" class="character-avatar">
            {{ teacherName?.[0] || '?' }}
          </div>
          <div class="message-content">
            <span class="sender-name" v-if="msg.sender_type === 'teacher'">{{ teacherName }}</span>
            <div class="message-text" v-html="formatMessage(msg.content)"></div>
          </div>
        </div>

        <!-- 打字机效果显示 -->
        <div v-if="isTyping" class="message teacher typing">
          <div class="character-avatar">{{ teacherName?.[0] || '?' }}</div>
          <div class="message-content">
            <span class="sender-name">{{ teacherName }}</span>
            <div class="message-text typewriter">{{ displayedText }}</div>
            <span class="cursor">▊</span>
          </div>
        </div>
      </div>
    </main>

    <!-- 选择面板 -->
    <ChoicePanel
      v-if="currentChoices.length > 0"
      :choices="currentChoices"
      @select="handleChoiceSelect"
    />

    <!-- 输入区域 -->
    <footer class="input-area" v-if="currentChoices.length === 0 && !isTyping">
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
    </footer>

    <!-- 工具确认弹窗 -->
    <ToolConfirmDialog
      v-if="showToolConfirm"
      :tool="toolRequest.tool"
      :query="toolRequest.query"
      :reason="toolRequest.reason"
      @confirm="executeTool"
      @cancel="cancelTool"
    />

    <!-- 存档/读档面板 -->
    <SaveLoad
      v-if="showSaveLoad"
      :subject-id="subjectId"
      @close="showSaveLoad = false"
      @load="handleLoadSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import DialogBox from '@/components/galgame/DialogBox.vue'
import ChoicePanel from '@/components/galgame/ChoicePanel.vue'
import CharacterDisplay from '@/components/galgame/CharacterDisplay.vue'
import EmotionIndicator from '@/components/galgame/EmotionIndicator.vue'
import SaveLoad from '@/components/galgame/SaveLoad.vue'
import ToolConfirmDialog from '@/components/galgame/ToolConfirmDialog.vue'
import mermaid from 'mermaid'

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
const currentEmotion = ref('')
const toolRequest = ref({ tool: '', query: '', reason: '' })
const dialogArea = ref<HTMLElement | null>(null)

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
  // Convert remaining newlines to <br>
  return formatted.replace(/\n/g, '<br>')
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
  nextTick(() => {
    if (dialogArea.value) {
      dialogArea.value.scrollTop = dialogArea.value.scrollHeight
    }
  })
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
      // 打字完成后添加到消息列表
      messages.value.push({
        id: Date.now(),
        sender_type: 'teacher',
        content: fullText
      })
      scrollToBottom()
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
      // 显示工具确认弹窗
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

    if (response.data.session_id) {
      // 获取会话历史
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
        scrollToBottom()
        renderMermaid()
      }

      // 获取关系阶段
      if (response.data.relationship_stage) {
        relationshipStage.value = response.data.relationship_stage
      }
    }

    if (response.data.teacher_persona) {
      teacherName.value = response.data.teacher_persona
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
.learning-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: rgba(0, 0, 0, 0.5);
  border-bottom: 1px solid #4a4a8a;
}

.header h2 {
  color: #ffd700;
  margin: 0;
}

.back-btn, .save-btn {
  padding: 8px 16px;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.back-btn:hover, .save-btn:hover {
  background: #3a3a5a;
  border-color: #ffd700;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.dialog-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  max-height: calc(100vh - 200px);
}

.messages-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.character-avatar {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #4a4a8a, #2a2a4a);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #ffd700;
  flex-shrink: 0;
}

.message-content {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid #4a4a8a;
  border-radius: 12px;
  padding: 12px 16px;
  position: relative;
}

.message.user .message-content {
  background: rgba(74, 74, 138, 0.3);
  border-color: #4a8a4a;
}

.sender-name {
  display: block;
  font-size: 12px;
  color: #ffd700;
  margin-bottom: 5px;
}

.message-text {
  color: #fff;
  line-height: 1.6;
}

.typing .message-text {
  min-height: 20px;
}

.cursor {
  animation: blink 1s infinite;
  color: #ffd700;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.input-area {
  display: flex;
  gap: 10px;
  padding: 15px 20px;
  background: rgba(0, 0, 0, 0.5);
  border-top: 1px solid #4a4a8a;
}

.input-area input {
  flex: 1;
  padding: 12px 16px;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
}

.input-area input:focus {
  outline: none;
  border-color: #ffd700;
}

.input-area input::placeholder {
  color: #888;
}

.input-area button {
  padding: 12px 24px;
  background: #4a8a4a;
  border: none;
  border-radius: 8px;
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
</style>