<template>
  <div class="settings-page">
    <header class="header">
      <button class="back-btn" @click="router.push('/home')">← 返回</button>
      <h1>设置</h1>
    </header>

    <main class="main">
      <!-- API Key 设置 -->
      <section class="settings-section">
        <h2>API 配置</h2>
        <div class="form-group">
          <label>LLM 提供商</label>
          <select v-model="settings.provider">
            <option value="claude">Claude (Anthropic)</option>
            <option value="openai">OpenAI GPT</option>
            <option value="local">本地模型 (Ollama)</option>
          </select>
        </div>

        <div class="form-group">
          <label>API Key</label>
          <input
            v-model="settings.apiKey"
            type="password"
            placeholder="输入你的API Key"
          />
          <p class="hint">你的API Key会加密存储，不会被泄露</p>
        </div>

        <button class="save-btn" @click="saveApiSettings" :disabled="saving">
          {{ saving ? '保存中...' : '保存API设置' }}
        </button>
        <p v-if="saveMessage" :class="['message', saveSuccess ? 'success' : 'error']">
          {{ saveMessage }}
        </p>
      </section>

      <!-- 主题设置 -->
      <section class="settings-section">
        <h2>显示设置</h2>
        <div class="form-group">
          <label>
            <input type="checkbox" v-model="settings.typewriterEffect" />
            启用打字机效果
          </label>
        </div>
        <div class="form-group">
          <label>
            <input type="checkbox" v-model="settings.autoScroll" />
            自动滚动到最新消息
          </label>
        </div>
      </section>

      <!-- 关于 -->
      <section class="settings-section">
        <h2>关于</h2>
        <p class="about-text">
          苏格拉底学习系统 v1.0<br>
          基于苏格拉底教学法的个性化学习系统
        </p>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const settings = ref({
  provider: 'claude',
  apiKey: '',
  typewriterEffect: true,
  autoScroll: true
})

const saving = ref(false)
const saveMessage = ref('')
const saveSuccess = ref(false)

const saveApiSettings = async () => {
  saving.value = true
  saveMessage.value = ''

  try {
    await axios.put(
      '/api/settings',
      {
        default_provider: settings.value.provider,
        api_key: settings.value.apiKey
      },
      {
        headers: { Authorization: `Bearer ${authStore.token}` }
      }
    )

    saveSuccess.value = true
    saveMessage.value = 'API设置保存成功！'
    settings.value.apiKey = '' // 清除输入的key
  } catch (error: any) {
    saveSuccess.value = false
    saveMessage.value = error.response?.data?.detail || '保存失败，请重试'
  } finally {
    saving.value = false

    // 3秒后清除消息
    setTimeout(() => {
      saveMessage.value = ''
    }, 3000)
  }
}

const fetchSettings = async () => {
  try {
    const response = await axios.get('/api/settings', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })

    if (response.data) {
      settings.value.provider = response.data.default_provider || 'claude'
    }
  } catch (error) {
    console.error('Failed to fetch settings:', error)
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<style scoped>
.settings-page {
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
  transition: all 0.3s;
}

.back-btn:hover {
  background: #3a3a5a;
  border-color: #ffd700;
}

.main {
  max-width: 600px;
  margin: 0 auto;
}

.settings-section {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid #4a4a8a;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.settings-section h2 {
  color: #ffd700;
  font-size: 18px;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #4a4a8a;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  color: #fff;
  margin-bottom: 8px;
  font-size: 14px;
}

.form-group input[type="text"],
.form-group input[type="password"],
.form-group select {
  width: 100%;
  padding: 12px;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #ffd700;
}

.form-group input[type="checkbox"] {
  margin-right: 10px;
}

.hint {
  color: #888;
  font-size: 12px;
  margin-top: 5px;
}

.save-btn {
  padding: 12px 24px;
  background: #4a8a4a;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.save-btn:hover:not(:disabled) {
  background: #5a9a5a;
}

.save-btn:disabled {
  background: #3a3a5a;
  cursor: not-allowed;
}

.message {
  margin-top: 10px;
  padding: 10px;
  border-radius: 6px;
  font-size: 14px;
}

.message.success {
  background: rgba(74, 138, 74, 0.3);
  border: 1px solid #4a8a4a;
  color: #5a9a5a;
}

.message.error {
  background: rgba(138, 74, 74, 0.3);
  border: 1px solid #8a4a4a;
  color: #aa5a5a;
}

.about-text {
  color: #888;
  font-size: 14px;
  line-height: 1.8;
}
</style>