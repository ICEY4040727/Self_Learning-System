<template>
  <div class="settings-page">
    <!-- Background -->
    <div class="bg-image" :style="{ backgroundImage: `url(${BG_URL})` }"></div>
    <div class="bg-gradient"></div>
    <ParticleBackground :count="16" :gold-ratio="0.5" />

    <!-- Header -->
    <div class="settings-header font-ui">
      <button class="galgame-hud-btn" @click="router.push('/home')">
        <span>←</span> 返回
      </button>
      <span class="header-title">系 统 设 置</span>
      <div style="width:80px;"></div>
    </div>

    <!-- Content -->
    <div class="settings-content galgame-scrollbar">
      <div class="settings-inner">

        <!-- API Settings -->
        <div class="panel">
          <div class="section-header">
            <span class="section-icon"></span>
            <div>
              <div class="section-title font-ui">API 设置</div>
              <div class="section-hint font-ui">使用哪个模型驱动对话</div>
            </div>
          </div>

          <!-- Provider toggle -->
          <div class="field-group">
            <label class="font-ui field-label">模型 Provider</label>
            <div class="provider-row">
              <button
                v-for="p in providers"
                :key="p.value"
                class="provider-btn"
                :class="{ active: settings.provider === p.value }"
                @click="selectProvider(p.value)"
              >
                {{ p.label }}
              </button>
            </div>
          </div>

          <!-- API Key -->
          <div class="field-group">
            <label class="font-ui field-label">API Key</label>
            <div class="relative">
              <input
                v-model="settings.apiKey"
                class="galgame-input settings-api-input"
                :type="showApiKey ? 'text' : 'password'"
                placeholder="sk-..."
              />
              <button
                type="button"
                class="toggle-vis-btn"
                :aria-label="showApiKey ? '隐藏 API Key' : '显示 API Key'"
                @click="showApiKey = !showApiKey"
              >
                <EyeOff v-if="showApiKey" :size="16" />
                <Eye v-else :size="16" />
              </button>
            </div>
            <p class="field-hint font-ui">密钥将安全存储于后端，不会明文传输</p>
          </div>

          <div class="field-group">
            <p class="field-hint font-ui">
              {{ settingsStore.apiKeyConfigured ? '已保存 API Key，可直接测试或清除后重填。' : '尚未保存 API Key。' }}
            </p>
          </div>

          <div class="field-group">
            <label class="font-ui field-label">Model</label>
            <input
              v-model="settings.model"
              class="galgame-input settings-api-input"
              placeholder="gpt-4o-mini / deepseek-chat / llama3.1"
            />
            <div class="model-suggestion-row">
              <button
                v-for="model in modelOptions"
                :key="model"
                class="model-chip"
                type="button"
                :class="{ active: settings.model === model }"
                @click="settings.model = model"
              >
                {{ model }}
              </button>
            </div>
            <div class="model-tools">
              <button
                class="galgame-hud-btn model-refresh-btn"
                type="button"
                :disabled="modelListLoading"
                @click="refreshModelList"
              >
                <RefreshCw :size="14" :class="{ spinning: modelListLoading }" />
                {{ modelListLoading ? '读取中' : '刷新模型' }}
              </button>
              <span v-if="modelListMessage" class="model-list-message font-ui">
                {{ modelListMessage }}
              </span>
            </div>
          </div>

          <div class="field-group">
            <label class="font-ui field-label">Base URL</label>
            <input
              v-model="settings.baseUrl"
              class="galgame-input settings-api-input"
              placeholder="https://example.com"
            />
            <p class="field-hint font-ui">OpenAI-compatible 网关可填根地址，后端会自动补 /v1</p>
          </div>

          <div class="settings-preview">
            <div class="settings-preview-title font-ui">请求预览</div>
            <div class="settings-preview-grid">
              <span>Provider</span>
              <strong>{{ apiRequestPreview.provider }}</strong>
              <span>Model</span>
              <strong>{{ apiRequestPreview.model }}</strong>
              <span>Base URL</span>
              <strong>{{ apiRequestPreview.baseUrl }}</strong>
              <span>Endpoint</span>
              <strong>{{ apiRequestPreview.endpoint }}</strong>
              <span>Key</span>
              <strong>{{ apiRequestPreview.keyState }}</strong>
            </div>
          </div>

          <div class="field-group">
            <label class="font-ui field-label">导入配置</label>
            <textarea
              v-model="importConfigText"
              class="galgame-input settings-api-input"
              rows="3"
              placeholder='粘贴 {"key":"...","url":"https://..."} 或 NewAPI JSON'
            />
            <div class="settings-inline-actions">
              <button class="galgame-hud-btn" type="button" @click="applyImportedConfig">导入</button>
            </div>
          </div>

          <!-- Error & save -->
          <Transition name="error-fade">
            <p v-if="error" class="error-text font-ui">{{ error }}</p>
          </Transition>
          <Transition name="error-fade">
            <p
              v-if="connectionMessage"
              class="settings-status font-ui"
              :class="{
                'settings-status-success': connectionStatus === 'success',
                'settings-status-error': connectionStatus === 'error',
              }"
            >
              {{ connectionMessage }}
            </p>
          </Transition>
        </div>

        <!-- LLM Settings -->
        <div v-if="false" class="panel">
          <div class="section-header">
            <span class="section-icon"></span>
            <div>
              <div class="section-title font-ui">LLM 参数</div>
              <div class="section-hint font-ui">调整对话生成行为</div>
            </div>
          </div>

          <!-- Temperature -->
          <div class="field-group">
            <label class="font-ui field-label">
              Temperature
              <span class="field-value">{{ settings.temperature }}</span>
            </label>
            <input
              type="range"
              v-model.number="settings.temperature"
              min="0"
              max="2"
              step="0.1"
              class="range-slider"
            />
            <p class="field-hint font-ui">控制回答的随机性 (0=确定性, 2=创造性)</p>
          </div>

          <!-- Max Tokens -->
          <div class="field-group">
            <label class="font-ui field-label">
              Max Tokens
              <span class="field-value">{{ settings.maxTokens }}</span>
            </label>
            <input
              type="range"
              v-model.number="settings.maxTokens"
              min="256"
              max="8192"
              step="256"
              class="range-slider"
            />
            <p class="field-hint font-ui">单次回复最大 token 数</p>
          </div>
        </div>

        <!-- Learning Settings -->
        <div class="panel">
          <div class="section-header">
            <span class="section-icon"></span>
            <div>
              <div class="section-title font-ui">学习设置</div>
              <div class="section-hint font-ui">个性化学习体验</div>
            </div>
          </div>

          <!-- Auto Mode Delay -->
          <div class="field-group">
            <label class="font-ui field-label">
              自动播放延迟
              <span class="field-value">{{ settings.autoModeDelay }}ms</span>
            </label>
            <input
              type="range"
              v-model.number="settings.autoModeDelay"
              min="1000"
              max="5000"
              step="500"
              class="range-slider"
            />
            <p class="field-hint font-ui">自动播放时每句话之间的间隔</p>
          </div>

          <!-- Notification Toggle -->
          <div class="toggle-row">
            <span class="font-ui toggle-label">复习提醒通知</span>
            <button
              class="toggle-switch"
              :class="{ on: settings.notificationEnabled }"
              @click="settings.notificationEnabled = !settings.notificationEnabled"
            >
              <span class="toggle-knob"></span>
            </button>
          </div>
        </div>

        <!-- Danger Zone -->
        <div class="panel danger-zone">
          <div class="section-header">
            <span class="section-icon danger-icon">[!]</span>
            <div>
              <div class="section-title danger-title font-ui">危险区域</div>
              <div class="section-hint font-ui">以下操作不可逆</div>
            </div>
          </div>
          <div class="danger-actions">
            <button class="danger-btn" @click="handleExport">
              导出数据
            </button>
            <button class="danger-btn danger-btn-red" @click="handleLogout">
              退出登录
            </button>
          </div>
        </div>

      </div>
    </div>

    <div class="settings-action-bar">
      <div class="settings-action-inner">
        <div class="settings-action-summary font-ui">
          <span>{{ apiRequestPreview.provider }}</span>
          <strong>{{ apiRequestPreview.model }}</strong>
          <em>{{ apiRequestPreview.keyState }}</em>
        </div>
        <div class="settings-action-buttons">
          <button
            class="galgame-hud-btn"
            type="button"
            @click="runConnectionTest"
          >
            测试连接
          </button>
          <button
            class="galgame-hud-btn"
            type="button"
            :disabled="!settingsStore.apiKeyConfigured && !settings.apiKey.trim()"
            @click="clearSavedKey"
          >
            清除 Key
          </button>
          <button
            class="galgame-send-btn settings-save-btn"
            type="button"
            :disabled="saving"
            @click="saveSettings"
          >
            {{ saving ? '保存中…' : '保存设置' }}
          </button>
          <Transition name="saved-fade">
            <span v-if="saved" class="saved-indicator font-ui">[v] 已保存</span>
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/app/stores/auth'
import { useSettingsStore } from '@/settings/stores/settings'
import client from '@/shared/api/client'
import type { LLMProvider } from '@/shared/types'
import ParticleBackground from '@/shared/components/ParticleBackground.vue'
import { Eye, EyeOff, RefreshCw } from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

import { PAGE_BACKGROUNDS } from '@/shared/constants/ui'
import { useToast } from '@/shared/composables/useToast'
const BG_URL = PAGE_BACKGROUNDS.settings
const toast = useToast()

const providerProfiles: Record<LLMProvider, {
  label: string
  defaultModel: string
  defaultBaseUrl: string
  endpointPath: string
  needsApiKey: boolean
  suggestions: string[]
}> = {
  custom: {
    label: 'Custom / NewAPI',
    defaultModel: 'gpt-4o-mini',
    defaultBaseUrl: '',
    endpointPath: '/chat/completions',
    needsApiKey: true,
    suggestions: ['gpt-4o-mini', 'deepseek-chat', 'qwen-plus', 'glm-4-plus'],
  },
  claude: {
    label: 'Claude',
    defaultModel: 'claude-3-5-sonnet-20241022',
    defaultBaseUrl: 'https://api.anthropic.com/v1',
    endpointPath: '/messages',
    needsApiKey: true,
    suggestions: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022'],
  },
  openai: {
    label: 'OpenAI',
    defaultModel: 'gpt-4o-mini',
    defaultBaseUrl: 'https://api.openai.com/v1',
    endpointPath: '/chat/completions',
    needsApiKey: true,
    suggestions: ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini'],
  },
  deepseek: {
    label: 'DeepSeek',
    defaultModel: 'deepseek-chat',
    defaultBaseUrl: 'https://api.deepseek.com/v1',
    endpointPath: '/chat/completions',
    needsApiKey: true,
    suggestions: ['deepseek-chat', 'deepseek-reasoner'],
  },
  local: {
    label: '本地模型 (Ollama)',
    defaultModel: 'llama3.1',
    defaultBaseUrl: 'http://localhost:11434',
    endpointPath: '/api/chat',
    needsApiKey: false,
    suggestions: ['llama3.1', 'qwen2.5', 'deepseek-r1'],
  },
}

const providers: Array<{ value: LLMProvider; label: string }> = ([
  'custom',
  'claude',
  'openai',
  'deepseek',
  'local',
] as LLMProvider[]).map((value) => ({ value, label: providerProfiles[value].label }))

const settings = reactive({
  provider: settingsStore.provider || 'claude',
  apiKey: '',
  model: settingsStore.model,
  baseUrl: settingsStore.baseUrl,
  temperature: settingsStore.temperature,
  maxTokens: settingsStore.maxTokens,
  autoModeDelay: settingsStore.autoModeDelay ?? 2800,
  notificationEnabled: true,
})

const defaultModels = Object.fromEntries(
  Object.entries(providerProfiles).map(([provider, profile]) => [provider, profile.defaultModel]),
) as Record<LLMProvider, string>

const allKnownModels = new Set(
  Object.values(providerProfiles).flatMap((profile) => [profile.defaultModel, ...profile.suggestions]),
)

const normalizeImportedBaseUrl = (value: string) => {
  let normalized = value.trim().split(/[?#]/)[0].replace(/\/+$/, '')
  const lower = normalized.toLowerCase()
  const marker = '/v1/'
  const markerIndex = lower.indexOf(marker)
  if (markerIndex >= 0) {
    normalized = normalized.slice(0, markerIndex + '/v1'.length)
  }
  return normalized
}

const normalizePreviewBaseUrl = (provider: LLMProvider, value: string) => {
  let normalized = value.trim().split(/[?#]/)[0].replace(/\/+$/, '')
  const profile = providerProfiles[provider]
  if (!normalized) {
    return profile.defaultBaseUrl
  }
  const lower = normalized.toLowerCase()
  if (provider === 'local') {
    return lower.endsWith('/api/chat') ? normalized.slice(0, -'/api/chat'.length) : normalized
  }
  const marker = '/v1/'
  const markerIndex = lower.indexOf(marker)
  if (markerIndex >= 0) {
    return normalized.slice(0, markerIndex + '/v1'.length)
  }
  return lower.endsWith('/v1') ? normalized : `${normalized}/v1`
}

const isAutoModel = (model: string) => !model.trim() || allKnownModels.has(model.trim())

const selectProvider = (provider: LLMProvider) => {
  const previousProvider = settings.provider
  const currentBaseUrl = normalizePreviewBaseUrl(previousProvider, settings.baseUrl)
  const previousDefaultBaseUrl = providerProfiles[previousProvider].defaultBaseUrl
  settingsStore.applyProviderSettings(provider)
  settings.provider = provider
  settings.apiKey = ''

  if (settingsStore.model) {
    settings.model = settingsStore.model
  } else if (isAutoModel(settings.model)) {
    settings.model = providerProfiles[provider].defaultModel
  }

  if (settingsStore.baseUrl) {
    settings.baseUrl = settingsStore.baseUrl
  } else if (!settings.baseUrl.trim() || currentBaseUrl === previousDefaultBaseUrl) {
    settings.baseUrl = providerProfiles[provider].defaultBaseUrl
  }
}

const modelSuggestions = computed(() => providerProfiles[settings.provider].suggestions)
const remoteModels = ref<string[]>([])
const modelListMessage = ref('')
const modelListLoading = ref(false)
const modelOptions = computed(() => remoteModels.value.length ? remoteModels.value : modelSuggestions.value)

const apiRequestPreview = computed(() => {
  const provider = settings.provider
  const profile = providerProfiles[provider]
  const baseUrl = normalizePreviewBaseUrl(provider, settings.baseUrl)
  const model = settings.model.trim() || profile.defaultModel
  const endpoint = baseUrl ? `${baseUrl}${profile.endpointPath}` : '请填写 Base URL'
  const hasKey = settings.apiKey.trim() || settingsStore.apiKeyConfigured
  const keyState = profile.needsApiKey
    ? (hasKey ? '已配置' : '需要配置')
    : '不需要'

  return {
    provider: profile.label,
    model,
    baseUrl: baseUrl || '未填写',
    endpoint,
    keyState,
  }
})

const showApiKey = ref(false)
const importConfigText = ref('')
const error = ref('')
const connectionMessage = ref('')
const connectionStatus = ref<'success' | 'error' | ''>('')
const saving = ref(false)
const saved = ref(false)

watch(
  () => [settings.provider, settings.baseUrl],
  () => {
    remoteModels.value = []
    modelListMessage.value = ''
  },
)

onMounted(async () => {
  await settingsStore.fetchSettings()
  settingsStore.applyProviderSettings(settingsStore.provider)
  settings.provider = settingsStore.provider
  settings.model = settingsStore.model || providerProfiles[settingsStore.provider].defaultModel
  settings.baseUrl = settingsStore.baseUrl || providerProfiles[settingsStore.provider].defaultBaseUrl
  settings.temperature = settingsStore.temperature
  settings.maxTokens = settingsStore.maxTokens
  settings.autoModeDelay = settingsStore.autoModeDelay ?? 2800
})

const applyImportedConfig = () => {
  try {
    const raw = importConfigText.value.trim()
    if (!raw) return
    const data = JSON.parse(raw)
    const provider = data.provider ?? (data.url || data.base_url || data.baseUrl ? 'custom' : settings.provider)
    const key = data.key ?? data.api_key ?? data.apiKey ?? ''
    const url = data.url ?? data.base_url ?? data.baseUrl ?? ''
    const importedProvider = provider as LLMProvider
    const model = data.model ?? data.model_name ?? (settings.model || defaultModels[importedProvider] || '')
    settings.provider = importedProvider
    settings.apiKey = String(key)
    settings.baseUrl = normalizeImportedBaseUrl(String(url))
    settings.model = String(model)
    remoteModels.value = []
    modelListMessage.value = ''
    error.value = ''
    connectionMessage.value = ''
    connectionStatus.value = ''
  } catch {
    error.value = '导入失败：请粘贴有效 JSON'
  }
}

const runConnectionTest = async () => {
  error.value = ''
  connectionMessage.value = ''
  connectionStatus.value = ''
  try {
    settingsStore.provider = settings.provider as LLMProvider
    settingsStore.model = settings.model
    settingsStore.baseUrl = settings.baseUrl
    settingsStore.temperature = settings.temperature
    settingsStore.maxTokens = settings.maxTokens
    settingsStore.apiKey = settings.apiKey
    const result = await settingsStore.testConnection()
    connectionStatus.value = result.ok ? 'success' : 'error'
    connectionMessage.value = result.ok
      ? `连接成功：${result.provider}${result.base_url ? ` @ ${result.base_url}` : ''}`
      : result.message
  } catch (e: any) {
    connectionStatus.value = 'error'
    connectionMessage.value = e?.response?.data?.detail ?? e?.message ?? '连接测试失败'
  }
}

const refreshModelList = async () => {
  error.value = ''
  modelListMessage.value = ''
  modelListLoading.value = true
  try {
    settingsStore.provider = settings.provider as LLMProvider
    settingsStore.model = settings.model
    settingsStore.baseUrl = settings.baseUrl
    settingsStore.apiKey = settings.apiKey
    const fetchModels = typeof settingsStore.fetchAvailableModels === 'function'
      ? () => settingsStore.fetchAvailableModels()
      : () => client.post<{
          provider: string
          base_url: string | null
          source: string
          models: string[]
          message: string | null
        }>('/settings/models', {
          default_provider: settingsStore.provider,
          model: settingsStore.model,
          base_url: settingsStore.baseUrl,
          ...(settingsStore.apiKey.trim() ? { api_key: settingsStore.apiKey.trim() } : {}),
        }).then(({ data }) => data)
    const result = await fetchModels()
    remoteModels.value = result.models ?? []
    modelListMessage.value = result.source === 'remote'
      ? `已从网关读取 ${remoteModels.value.length} 个模型`
      : (result.message || '使用预设模型候选')
  } catch (e: any) {
    remoteModels.value = []
    modelListMessage.value = e?.response?.data?.detail ?? e?.message ?? '读取模型失败'
  } finally {
    modelListLoading.value = false
  }
}

const clearSavedKey = async () => {
  error.value = ''
  connectionMessage.value = ''
  connectionStatus.value = ''
  try {
    await settingsStore.clearApiKey()
    settings.apiKey = ''
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? e?.message ?? '清除失败'
  }
}

const saveSettings = async () => {
  error.value = ''
  connectionMessage.value = ''
  connectionStatus.value = ''
  saving.value = true
  saved.value = false
  try {
    settingsStore.provider = settings.provider as LLMProvider
    settingsStore.model = settings.model
    settingsStore.baseUrl = settings.baseUrl
    settingsStore.temperature = settings.temperature
    settingsStore.maxTokens = settings.maxTokens
    settingsStore.autoModeDelay = settings.autoModeDelay
    if (settings.apiKey.trim()) {
      settingsStore.apiKey = settings.apiKey.trim()
    }
    await settingsStore.saveSettings()
    saved.value = true
    settings.apiKey = ''
    setTimeout(() => (saved.value = false), 3000)
  } catch (e: any) {
    error.value = e?.message ?? '保存失败'
  } finally {
    saving.value = false
  }
}

const handleExport = () => {
  toast.info('数据导出功能开发中')
}

const handleLogout = () => {
  if (confirm('确定退出登录？')) {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.settings-page {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  overflow-y: auto;
  padding-bottom: 104px;
}

.bg-image {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.08;
  z-index: -2;
}

.bg-gradient {
  position: fixed;
  inset: 0;
  background: linear-gradient(to bottom, rgba(10,10,30,0.95) 0%, rgba(10,10,30,0.98) 100%);
  z-index: -1;
}

.settings-header {
  position: relative;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255,215,0,0.1);
  z-index: 10;
}

.settings-header button {
  font-size: 13px;
  padding: 6px 14px;
}

.header-title {
  color: #ffd700;
  font-size: 16px;
  letter-spacing: 4px;
}

.settings-content {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  padding-top: 72px;
  padding-bottom: 120px;
  padding-left: 24px;
  padding-right: 24px;
}

.settings-inner {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel {
  padding: 22px 26px;
  background: rgba(8, 8, 28, 0.85);
  border: 1px solid rgba(255,215,0,0.12);
  border-radius: 14px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}

.section-icon {
  font-size: 18px;
  margin-top: 2px;
}

.section-title {
  color: #ffd700;
  font-size: 14px;
  letter-spacing: 2px;
}

.section-hint {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
  margin-top: 2px;
}

.danger-title {
  color: #ef4444;
}

.danger-icon {
  color: #ef4444;
}

.field-group {
  margin-bottom: 18px;
}

.field-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  letter-spacing: 1px;
  margin-bottom: 10px;
}

.field-value {
  color: rgba(255,215,0,0.6);
}

.provider-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.provider-btn {
  padding: 8px 18px;
  font-size: 13px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,215,0,0.15);
  border-radius: 6px;
  color: rgba(255,255,255,0.6);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Noto Sans SC', sans-serif;
}

.provider-btn.active {
  background: rgba(255,215,0,0.12);
  border-color: rgba(255,215,0,0.5);
  color: #ffd700;
}

.settings-api-input {
  width: 100%;
  padding: 10px 44px 10px 14px;
  font-size: 13px;
}

.model-suggestion-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.model-chip {
  padding: 6px 10px;
  border: 1px solid rgba(255,215,0,0.16);
  border-radius: 6px;
  background: rgba(255,255,255,0.04);
  color: rgba(255,255,255,0.55);
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
}

.model-chip.active {
  border-color: rgba(255,215,0,0.5);
  color: #ffd700;
  background: rgba(255,215,0,0.12);
}

.model-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.model-refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 6px 12px;
}

.model-refresh-btn:disabled {
  opacity: 0.5;
  cursor: wait;
}

.model-list-message {
  color: rgba(255,255,255,0.42);
  font-size: 11px;
}

.spinning {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.settings-preview {
  margin: 2px 0 18px;
  padding-top: 14px;
  border-top: 1px solid rgba(255,215,0,0.12);
}

.settings-preview-title {
  color: rgba(255,215,0,0.7);
  font-size: 12px;
  letter-spacing: 1px;
  margin-bottom: 10px;
}

.settings-preview-grid {
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr);
  gap: 8px 12px;
  font-size: 11px;
}

.settings-preview-grid span {
  color: rgba(255,255,255,0.32);
}

.settings-preview-grid strong {
  color: rgba(255,255,255,0.72);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.settings-inline-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.settings-inline-actions .galgame-hud-btn {
  font-size: 12px;
  padding: 6px 12px;
}

.relative {
  position: relative;
}

.toggle-vis-btn {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.5;
  color: rgba(255,255,255,0.85);
}

.field-hint {
  font-size: 11px;
  color: rgba(255,255,255,0.25);
  margin-top: 6px;
}

.range-slider {
  width: 100%;
  -webkit-appearance: none;
  height: 4px;
  border-radius: 2px;
  background: rgba(255,255,255,0.1);
  outline: none;
}

.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ffd700;
  cursor: pointer;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.toggle-label {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  letter-spacing: 1px;
}

.toggle-switch {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
}

.toggle-switch.on {
  background: rgba(255,215,0,0.3);
  border-color: rgba(255,215,0,0.5);
}

.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(255,255,255,0.4);
  transition: all 0.2s ease;
}

.toggle-switch.on .toggle-knob {
  left: 22px;
  background: #ffd700;
}

.error-text {
  font-size: 12px;
  color: #ef4444;
  margin-bottom: 12px;
}

.settings-status {
  font-size: 12px;
  margin-bottom: 12px;
}

.settings-status-success {
  color: #4adf6a;
}

.settings-status-error {
  color: #ef4444;
}

.settings-save-btn {
  padding: 10px 32px;
  font-size: 13px;
  letter-spacing: 2px;
}

.saved-indicator {
  font-size: 12px;
  color: #4adf6a;
}

.settings-action-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px 18px 16px;
  background: linear-gradient(to top, rgba(8, 8, 28, 0.98), rgba(8, 8, 28, 0.72));
  border-top: 1px solid rgba(255,215,0,0.12);
  z-index: 20;
  backdrop-filter: blur(10px);
}

.settings-action-inner {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.settings-action-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  font-size: 11px;
  color: rgba(255,255,255,0.45);
}

.settings-action-summary strong {
  color: rgba(255,215,0,0.85);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}

.settings-action-summary em {
  font-style: normal;
  color: rgba(255,255,255,0.28);
}

.settings-action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

@media (max-width: 640px) {
  .settings-content {
    padding-left: 14px;
    padding-right: 14px;
    padding-bottom: 164px;
  }

  .panel {
    padding: 18px;
  }

  .settings-action-inner {
    align-items: stretch;
    flex-direction: column;
  }

  .settings-action-summary {
    justify-content: space-between;
  }

  .settings-action-summary strong {
    max-width: 150px;
  }

  .settings-action-buttons {
    justify-content: stretch;
  }

  .settings-action-buttons .galgame-hud-btn,
  .settings-action-buttons .settings-save-btn {
    flex: 1 1 0;
    min-width: 0;
    padding-left: 10px;
    padding-right: 10px;
  }
}

.danger-zone {
  border-color: rgba(239,68,68,0.2);
}

.danger-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.danger-btn {
  padding: 8px 20px;
  font-size: 13px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 6px;
  color: rgba(255,255,255,0.6);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Noto Sans SC', sans-serif;
}

.danger-btn:hover {
  background: rgba(255,255,255,0.08);
}

.danger-btn-red {
  color: rgba(255,100,100,0.7);
  border-color: rgba(255,100,100,0.3);
}

.danger-btn-red:hover {
  background: rgba(255,100,100,0.1);
}

/* Transitions */
.error-fade-enter-from,
.error-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.error-fade-enter-active,
.error-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.saved-fade-enter-from,
.saved-fade-leave-to {
  opacity: 0;
}

.saved-fade-enter-active,
.saved-fade-leave-active {
  transition: opacity 0.3s ease;
}
</style>
