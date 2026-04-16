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
            <span class="section-icon">🔑</span>
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
                @click="settings.provider = p.value"
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
                @click="showApiKey = !showApiKey"
              >
                {{ showApiKey ? '🙈' : '👁' }}
              </button>
            </div>
            <p class="field-hint font-ui">密钥将安全存储于后端，不会明文传输</p>
          </div>

          <!-- Error & save -->
          <Transition name="error-fade">
            <p v-if="error" class="error-text font-ui">{{ error }}</p>
          </Transition>
          <div class="save-row">
            <button
              class="galgame-send-btn settings-save-btn"
              :disabled="saving"
              @click="saveSettings"
            >
              {{ saving ? '保存中…' : '保存设置' }}
            </button>
            <Transition name="saved-fade">
              <span v-if="saved" class="saved-indicator font-ui">✓ 已保存</span>
            </Transition>
          </div>
        </div>

        <!-- LLM Settings -->
        <div class="panel">
          <div class="section-header">
            <span class="section-icon">⚙️</span>
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
            <span class="section-icon">📖</span>
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
            <span class="section-icon danger-icon">⚠️</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import type { LLMProvider } from '@/types'
import ParticleBackground from '@/components/ParticleBackground.vue'

const router = useRouter()
const authStore = useAuthStore()
const settingsStore = useSettingsStore()

const BG_URL = 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1920&q=80'

const providers: Array<{ value: LLMProvider; label: string }> = [
  { value: 'claude', label: 'Claude' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'local', label: '本地模型 (Ollama)' },
]

const settings = reactive({
  provider: settingsStore.provider || 'claude',
  apiKey: '',
  temperature: settingsStore.temperature,
  maxTokens: settingsStore.maxTokens,
  autoModeDelay: settingsStore.autoModeDelay ?? 2800,
  notificationEnabled: true,
})

const showApiKey = ref(false)
const error = ref('')
const saving = ref(false)
const saved = ref(false)

onMounted(async () => {
  await settingsStore.fetchSettings()
  settings.provider = settingsStore.provider
  settings.temperature = settingsStore.temperature
  settings.maxTokens = settingsStore.maxTokens
  settings.autoModeDelay = settingsStore.autoModeDelay ?? 2800
})

const saveSettings = async () => {
  error.value = ''
  saving.value = true
  saved.value = false
  try {
    settingsStore.provider = settings.provider as LLMProvider
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
  padding-bottom: 48px;
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
  padding-bottom: 32px;
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

.relative {
  position: relative;
}

.toggle-vis-btn {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  opacity: 0.5;
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

.save-row {
  display: flex;
  align-items: center;
  gap: 12px;
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
