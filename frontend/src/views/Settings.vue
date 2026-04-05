<template>
  <div class="settings-page">
    <div class="settings-bg-image"></div>
    <div class="settings-bg-overlay"></div>

    <header class="header">
      <button class="back-btn" @click="router.push('/home')">← 返回</button>
      <h1>设置</h1>
    </header>

    <main class="main galgame-scrollbar">
      <section class="settings-section galgame-panel">
        <div class="section-head">
          <h2>后端设置（持久化）</h2>
          <span :class="['state-pill', saveState]">{{ saveStateText }}</span>
        </div>

        <p class="section-desc">将写入 <code>/api/settings</code>：仅保存 default_provider 与 api_key。</p>

        <div class="provider-grid">
          <label
            v-for="option in providerOptions"
            :key="option.value"
            :class="['provider-option', { active: backendSettings.provider === option.value }]"
          >
            <input
              v-model="backendSettings.provider"
              type="radio"
              name="provider"
              :value="option.value"
              :data-testid="`provider-${option.value}`"
            />
            <span>{{ option.label }}</span>
          </label>
        </div>

        <div class="form-group">
          <label>API Key</label>
          <div class="api-key-row">
            <input
              v-model="backendSettings.apiKey"
              :type="showApiKey ? 'text' : 'password'"
              placeholder="输入你的 API Key（留空则不更新）"
            />
            <button class="toggle-btn" type="button" @click="showApiKey = !showApiKey">
              {{ showApiKey ? '隐藏' : '显示' }}
            </button>
          </div>
          <p class="hint">API Key 会在后端加密保存。</p>
        </div>

        <div class="save-row">
          <button
            class="save-btn"
            data-testid="save-backend-settings"
            @click="saveBackendSettings"
            :disabled="saveState === 'saving'"
          >
            {{ saveButtonText }}
          </button>
          <p v-if="saveMessage" :class="['message', saveState === 'error' ? 'error' : 'success']">
            {{ saveMessage }}
          </p>
        </div>
      </section>

      <section class="settings-section galgame-panel">
        <div class="section-head">
          <h2>本地偏好（仅浏览器）</h2>
          <span class="state-pill local">自动保存</span>
        </div>
        <p class="section-desc">以下偏好使用 localStorage 保存，不会调用后端接口。</p>

        <div class="toggle-list">
          <label class="toggle-item">
            <div>
              <span class="toggle-title">打字机效果</span>
              <p class="hint">控制 Learning 页面文字逐字显示动画。</p>
            </div>
            <input v-model="displaySettings.typewriterEffect" data-testid="pref-typewriter" type="checkbox" />
          </label>
          <label class="toggle-item">
            <div>
              <span class="toggle-title">自动滚动</span>
              <p class="hint">聊天内容更新后自动滚动到最新位置。</p>
            </div>
            <input v-model="displaySettings.autoScroll" data-testid="pref-autoscroll" type="checkbox" />
          </label>
        </div>
      </section>

      <section class="settings-section galgame-panel">
        <h2>关于</h2>
        <p class="about-text">
          苏格拉底学习系统 v1.0<br />
          基于苏格拉底教学法的个性化学习平台
        </p>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'

interface DisplaySettings {
  typewriterEffect: boolean
  autoScroll: boolean
}

type SaveState = 'idle' | 'saving' | 'success' | 'error'
type Provider = 'claude' | 'openai' | 'local'

const DISPLAY_SETTINGS_KEY = 'display_settings'
const providerOptions: Array<{ value: Provider; label: string }> = [
  { value: 'claude', label: 'Claude (Anthropic)' },
  { value: 'openai', label: 'OpenAI GPT' },
  { value: 'local', label: '本地模型 (Ollama)' },
]

const router = useRouter()
const authStore = useAuthStore()
const showApiKey = ref(false)
const saveState = ref<SaveState>('idle')
const saveMessage = ref('')
let messageTimer: ReturnType<typeof setTimeout> | null = null

const loadDisplaySettings = (): DisplaySettings => {
  const raw = localStorage.getItem(DISPLAY_SETTINGS_KEY)
  if (!raw) {
    return { typewriterEffect: true, autoScroll: true }
  }

  try {
    const parsed = JSON.parse(raw) as Partial<DisplaySettings>
    return {
      typewriterEffect: typeof parsed.typewriterEffect === 'boolean' ? parsed.typewriterEffect : true,
      autoScroll: typeof parsed.autoScroll === 'boolean' ? parsed.autoScroll : true,
    }
  } catch (error) {
    console.warn('Failed to parse local display settings:', parseApiError(error))
    return { typewriterEffect: true, autoScroll: true }
  }
}

const backendSettings = ref<{ provider: Provider; apiKey: string }>({
  provider: 'claude',
  apiKey: '',
})
const displaySettings = ref<DisplaySettings>(loadDisplaySettings())

watch(
  displaySettings,
  (next) => {
    localStorage.setItem(DISPLAY_SETTINGS_KEY, JSON.stringify(next))
  },
  { deep: true },
)

const saveStateText = computed(() => {
  if (saveState.value === 'saving') return '保存中'
  if (saveState.value === 'success') return '已保存'
  if (saveState.value === 'error') return '保存失败'
  return '未保存'
})

const saveButtonText = computed(() => {
  if (saveState.value === 'saving') return '保存中...'
  if (saveState.value === 'success') return '✓ 已保存'
  return '保存后端设置'
})

const resetMessageLater = () => {
  if (messageTimer) {
    clearTimeout(messageTimer)
  }
  messageTimer = setTimeout(() => {
    saveMessage.value = ''
    if (saveState.value !== 'saving') {
      saveState.value = 'idle'
    }
  }, 2500)
}

const saveBackendSettings = async () => {
  saveState.value = 'saving'
  saveMessage.value = ''

  try {
    const payload: { default_provider: Provider; api_key?: string } = {
      default_provider: backendSettings.value.provider,
    }
    const trimmedApiKey = backendSettings.value.apiKey.trim()
    if (trimmedApiKey) {
      payload.api_key = trimmedApiKey
    }

    await axios.put('/api/settings', payload, {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })

    saveState.value = 'success'
    saveMessage.value = '后端设置保存成功。'
    backendSettings.value.apiKey = ''
  } catch (error) {
    saveState.value = 'error'
    saveMessage.value = parseApiError(error)
  } finally {
    resetMessageLater()
  }
}

const fetchBackendSettings = async () => {
  try {
    const response = await axios.get('/api/settings', {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    const provider = response.data?.default_provider as Provider | undefined
    if (provider && providerOptions.some((option) => option.value === provider)) {
      backendSettings.value.provider = provider
    }
  } catch (error) {
    saveState.value = 'error'
    saveMessage.value = `读取后端设置失败：${parseApiError(error)}`
    resetMessageLater()
  }
}

onMounted(() => {
  fetchBackendSettings()
})

onUnmounted(() => {
  if (messageTimer) {
    clearTimeout(messageTimer)
  }
})
</script>

<style scoped>
.settings-page {
  position: relative;
  min-height: 100vh;
  padding: 24px;
  background: linear-gradient(180deg, #0f172a 0%, #111827 58%, #0b1220 100%);
  overflow: hidden;
}

.settings-bg-image {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(120deg, rgba(56, 189, 248, 0.1), transparent 38%),
    linear-gradient(320deg, rgba(167, 139, 250, 0.1), transparent 45%);
  pointer-events: none;
}

.settings-bg-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 8% 10%, rgba(255, 215, 0, 0.12), transparent 40%),
    radial-gradient(circle at 92% 12%, rgba(99, 102, 241, 0.2), transparent 44%);
  pointer-events: none;
}

.header,
.main {
  position: relative;
  z-index: 2;
}

.header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.header h1 {
  margin: 0;
  color: var(--accent-gold, #ffd700);
}

.back-btn,
.save-btn,
.toggle-btn {
  border-radius: 10px;
  border: 1px solid var(--border-subtle, #4b5563);
  background: rgba(17, 24, 39, 0.8);
  color: var(--text-primary, #e5e7eb);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn {
  padding: 10px 14px;
}

.back-btn:hover,
.toggle-btn:hover {
  border-color: var(--accent-gold, #ffd700);
}

.main {
  max-width: 760px;
  margin: 0 auto;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  padding-right: 8px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-section {
  border: 1px solid var(--border-subtle, #4b5563);
  border-radius: 16px;
  padding: 18px;
  background: rgba(17, 24, 39, 0.84);
}

.settings-section h2 {
  margin: 0;
  color: var(--accent-gold, #ffd700);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.section-desc {
  margin: 0 0 14px;
  color: var(--text-secondary, #9ca3af);
  font-size: 13px;
}

.section-desc code {
  font-family: monospace;
  color: #fde68a;
}

.state-pill {
  font-size: 12px;
  border-radius: 999px;
  padding: 4px 10px;
  border: 1px solid rgba(107, 114, 128, 0.5);
  color: #d1d5db;
}

.state-pill.saving {
  border-color: rgba(96, 165, 250, 0.5);
  color: #93c5fd;
}

.state-pill.success {
  border-color: rgba(74, 223, 106, 0.55);
  color: #86efac;
}

.state-pill.error {
  border-color: rgba(248, 113, 113, 0.6);
  color: #fecaca;
}

.state-pill.local {
  border-color: rgba(99, 102, 241, 0.5);
  color: #c7d2fe;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.provider-option {
  display: flex;
  gap: 8px;
  align-items: center;
  border: 1px solid var(--border-subtle, #4b5563);
  border-radius: 12px;
  padding: 10px;
  color: var(--text-secondary, #d1d5db);
  cursor: pointer;
}

.provider-option.active {
  border-color: rgba(255, 215, 0, 0.7);
  background: rgba(255, 215, 0, 0.1);
  color: #fef3c7;
}

.provider-option input {
  margin: 0;
}

.form-group {
  margin-bottom: 10px;
}

.form-group label {
  display: block;
  color: var(--text-primary, #f3f4f6);
  margin-bottom: 6px;
}

.api-key-row {
  display: flex;
  gap: 8px;
}

.api-key-row input {
  flex: 1;
  border: 1px solid var(--border-subtle, #4b5563);
  border-radius: 10px;
  background: rgba(3, 7, 18, 0.7);
  color: var(--text-primary, #f3f4f6);
  padding: 10px 12px;
}

.api-key-row input:focus {
  outline: none;
  border-color: rgba(255, 215, 0, 0.75);
}

.toggle-btn {
  padding: 10px 12px;
}

.hint {
  margin: 6px 0 0;
  color: var(--text-muted, #9ca3af);
  font-size: 12px;
}

.save-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.save-btn {
  align-self: flex-start;
  padding: 10px 16px;
}

.save-btn:hover:not(:disabled) {
  border-color: rgba(74, 223, 106, 0.6);
  color: #dcfce7;
}

.save-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.message {
  margin: 0;
  font-size: 13px;
  border-radius: 10px;
  padding: 8px 10px;
  border: 1px solid rgba(74, 223, 106, 0.4);
  background: rgba(74, 223, 106, 0.14);
  color: #86efac;
}

.message.error {
  border-color: rgba(248, 113, 113, 0.6);
  background: rgba(248, 113, 113, 0.12);
  color: #fecaca;
}

.toggle-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toggle-item {
  border: 1px solid var(--border-subtle, #4b5563);
  border-radius: 12px;
  background: rgba(31, 41, 55, 0.6);
  padding: 12px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.toggle-item input[type='checkbox'] {
  width: 18px;
  height: 18px;
  accent-color: #ffd700;
}

.toggle-title {
  color: var(--text-primary, #f3f4f6);
  font-weight: 600;
}

.about-text {
  margin: 8px 0 0;
  color: var(--text-secondary, #cbd5e1);
  line-height: 1.8;
}

@media (max-width: 700px) {
  .settings-page {
    padding: 14px;
  }

  .main {
    max-height: none;
    overflow-y: visible;
    padding-right: 0;
  }

  .api-key-row {
    flex-direction: column;
  }
}
</style>
