<template>
  <div class="login-page">
    <!-- Scene background -->
    <div class="scene-bg" :style="{ backgroundImage: `url(${loginBg})` }"></div>
    
    <!-- Combined overlay layer -->
    <div class="scene-overlay"></div>
    
    <!-- Title area - v-motion animation -->
    <div 
      class="title-area"
      v-motion
      :initial="{ opacity: 0, y: -28 }"
      :enter="{ opacity: 1, y: 0 }"
      :transition="{ duration: 900, delay: 150 }"
    >
      <div class="top-rune">✦ &nbsp; ZHĪ YÙ · 愿求知者皆得其道 &nbsp; ✦</div>
      <h1 class="title-text-hover title-text">知遇</h1>
      <div class="subtitle-text">Zhī Yù</div>
      <div class="gold-divider"></div>
    </div>

    <!-- Login panel -->
    <div class="login-panel">
      <!-- Mode tabs -->
      <div class="mode-tabs">
        <button
          v-for="m in (['login', 'register'] as const)"
          :key="m"
          class="mode-tab"
          :class="{ active: mode === m }"
          @click="mode = m; error = ''"
        >
          {{ m === 'login' ? '登 入' : '注 册' }}
        </button>
      </div>

      <!-- Form -->
      <TransitionGroup name="field-list" tag="form" @submit.prevent="handleSubmit" class="form-stack">
        <!-- Username -->
        <div key="username" class="field-group">
          <label class="field-label">用 户 名</label>
          <input
            v-model="username"
            type="text"
            class="galgame-input"
            placeholder="请输入用户名"
            autocomplete="username"
            required
          />
        </div>

        <!-- Password -->
        <div key="password" class="field-group">
          <label class="field-label">密 码</label>
          <div class="pw-wrapper">
            <input
              v-model="password"
              :type="showPw ? 'text' : 'password'"
              class="galgame-input pw-input"
              placeholder="请输入密码"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              required
            />
            <button
              type="button"
              class="pw-toggle"
              @click="showPw = !showPw"
            >
              <component :is="showPw ? EyeOff : Eye" :size="15" />
            </button>
          </div>
        </div>

        <!-- Confirm password (register only) - fast fade out -->
        <Transition name="confirm-fast">
          <div key="confirmPw" v-if="mode === 'register'" class="field-group">
            <label class="field-label">确 认 密 码</label>
            <input
              v-model="confirmPw"
              :type="showPw ? 'text' : 'password'"
              class="galgame-input"
              placeholder="再次输入密码"
              autocomplete="new-password"
            />
          </div>
        </Transition>

        <!-- Error message -->
        <div key="error" v-if="error" class="error-box font-ui">{{ error }}</div>

        <!-- Submit -->
        <button key="submit" type="submit" class="submit-btn" :disabled="loading">
          <span v-if="loading" class="loading-dots">
            <span v-for="i in 3" :key="i" :style="{ animationDelay: `${(i-1) * 0.2}s` }">·</span>
          </span>
          <span v-else>{{ mode === 'login' ? '进 入 学 堂' : '创 建 账 号' }}</span>
        </button>
      </TransitionGroup>

      <!-- Demo hint -->
      <div class="demo-hint font-ui">演示模式：输入任意用户名密码即可进入</div>
    </div>

    <!-- Bottom signature - v-motion delayed animation -->
    <div 
      class="bottom-sig font-ui"
      v-motion
      :initial="{ opacity: 0 }"
      :enter="{ opacity: 1 }"
      :transition="{ delay: 1200, duration: 1000 }"
    >
      ✦ &nbsp; ZHĪ YÙ v{{ version }} &nbsp; ✦
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import loginBg from '@/assets/login-bg.jpg'
import { useRouter } from 'vue-router'
import { Eye, EyeOff } from 'lucide-vue-next'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'

const router = useRouter()
const authStore = useAuthStore()

const version = '1.0.0'

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const confirmPw = ref('')
const showPw = ref(false)
const error = ref('')
const loading = ref(false)

const handleSubmit = async () => {
  error.value = ''
  if (!username.value.trim() || !password.value.trim()) {
    error.value = '请填写用户名和密码'
    return
  }
  if (mode.value === 'register' && password.value !== confirmPw.value) {
    error.value = '两次密码不一致'
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      // OAuth2 password flow — requires FormData
      const formData = new FormData()
      formData.append('username', username.value.trim())
      formData.append('password', password.value)
      const res = await axios.post('/api/auth/login', formData)
      authStore.token = res.data.access_token
      authStore.user = res.data
      // Persist and set axios header
      localStorage.setItem('token', authStore.token!)
      axios.defaults.headers.common['Authorization'] = `Bearer ${authStore.token}`
      router.push('/home')
    } else {
      // Register — JSON payload
      await axios.post('/api/auth/register', {
        username: username.value.trim(),
        password: password.value
      })
      error.value = '注册成功，请登录'
      mode.value = 'login'
    }
  } catch (e: any) {
    error.value = parseApiError(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #0a0a1e;
}

.scene-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center 25%;
}

/* Combined overlay - merges gradient, radial, and glow into one layer */
.scene-overlay {
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(ellipse at 50% 0%, rgba(10,10,30,0.15) 0%, transparent 60%),
    radial-gradient(ellipse at 30% 55%, rgba(255,215,0,0.05) 0%, transparent 55%),
    radial-gradient(ellipse at 70% 35%, rgba(96,165,250,0.04) 0%, transparent 55%),
    linear-gradient(to bottom, rgba(10,10,30,0.25) 0%, rgba(0,0,0,0.45) 100%);
}

.title-area {
  position: relative;
  z-index: 10;
  text-align: center;
  margin-bottom: 40px;
}

.top-rune {
  color: rgba(255,215,0,0.65);
  font-size: 11px;
  letter-spacing: 6px;
  margin-bottom: 12px;
}

.title-text {
  font-family: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
  font-size: 38px;
  letter-spacing: 12px;
  color: #ffd700;
  margin-bottom: 12px;
  transition: text-shadow 0.6s ease;
  text-align: center;
}

.title-text-hover:hover {
  text-shadow: 
    0 0 8px rgba(255,215,0,0.6),
    0 0 16px rgba(255,215,0,0.35);
}

.subtitle-text {
  font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif;
  color: rgba(255,255,255,0.70);
  font-size: 14px;
  letter-spacing: 4px;
}

.gold-divider {
  width: 200px;
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(255,215,0,0.5), transparent);
  margin: 14px auto 0;
}

.login-panel {
  position: relative;
  z-index: 10;
  width: 420px;
  max-width: 92vw;
  min-height: 320px;
  padding: 28px 32px 26px;
  background: rgba(8, 8, 25, 0.35);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-top: none;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  text-align: center;
}

/* Elegant top border with gradient */
.login-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(
    to right,
    transparent 0%,
    rgba(255, 215, 0, 0.6) 20%,
    rgba(255, 215, 0, 0.9) 50%,
    rgba(255, 215, 0, 0.6) 80%,
    transparent 100%
  );
}

/* Elegant fonts for login panel content */
.login-panel .mode-tabs,
.login-panel .mode-tab,
.login-panel .field-label,
.login-panel .galgame-input,
.login-panel .submit-btn,
.login-panel .demo-hint,
.login-panel .error-box {
  font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
}

.mode-tabs {
  display: flex;
  margin-bottom: 28px;
  border-bottom: 1px solid rgba(255,215,0,0.25);
}

.mode-tab {
  flex: 1;
  padding-bottom: 10px;
  font-size: 14px;
  letter-spacing: 5px;
  cursor: pointer;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: rgba(255,255,255,0.50);
  transition: all 0.25s ease;
  margin-bottom: -1px;
}

.mode-tab.active {
  color: #ffd700;
  border-bottom-color: #ffd700;
}

.form-stack {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 16px;
}

.field-label {
  color: rgba(255,255,255,0.60);
  font-size: 12px;
  letter-spacing: 4px;
}

/* Override galgame-input to use gold border instead of dark */
.galgame-input {
  background: rgba(0, 0, 0, 0.40) !important;
  border: 2px solid rgba(255, 215, 0, 0.40) !important;
  border-radius: 0 !important;
  color: rgba(255,255,255,0.90) !important;
  transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
  width: 100%;
  box-sizing: border-box;
  padding: 14px 16px !important;
}

.galgame-input:focus {
  border-color: rgba(255, 215, 0, 0.75) !important;
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.20) !important;
  outline: none !important;
}

.galgame-input::placeholder {
  color: rgba(255,255,255,0.35) !important;
}

/* Password wrapper for proper alignment */
.pw-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.pw-input {
  padding-right: 44px !important;
}

.pw-toggle {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  cursor: pointer;
  color: rgba(255,255,255,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s ease;
  padding: 0;
  height: 100%;
}

.pw-toggle:hover {
  color: rgba(255, 215, 0, 0.75);
}

.error-box {
  color: #ff6b6b;
  font-size: 12px;
  background: rgba(255, 80, 80, 0.12);
  border: 1px solid rgba(255, 80, 80, 0.35);
  padding: 8px 12px;
  letter-spacing: 1px;
}

/* Submit button matching learning interface style */
.submit-btn {
  width: 100%;
  padding: 14px 20px;
  font-size: 14px;
  letter-spacing: 6px;
  margin-top: 4px;
  background: rgba(255,215,0,0.12);
  border: 2px solid rgba(255, 215, 0, 0.50);
  color: #ffd700;
  cursor: pointer;
  transition: all 0.3s ease;
  font-family: inherit;
}

.submit-btn:hover:not(:disabled) {
  background: rgba(255,215,0,0.22);
  border-color: rgba(255, 215, 0, 0.75);
  box-shadow: 0 0 16px rgba(255, 215, 0, 0.18);
}

.submit-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-dots span {
  animation: dotFlash 1.2s ease-in-out infinite;
}

.loading-dots {
  opacity: 0.7;
  letter-spacing: 2px;
}

@keyframes dotFlash {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}

.demo-hint {
  text-align: center;
  margin-top: 20px;
  color: rgba(255,255,255,0.35);
  font-size: 11px;
  letter-spacing: 1px;
}

.bottom-sig {
  position: absolute;
  bottom: 28px;
  color: rgba(255,215,0,0.55);
  font-size: 12px;
  letter-spacing: 4px;
  text-shadow: 0 0 16px rgba(255,215,0,0.25);
}

.error-fade-enter-from,
.error-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.error-fade-enter-active,
.error-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

/* Confirm password field slide transition */
.field-slide-enter-from,
.field-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.field-slide-enter-active,
.field-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

/* TransitionGroup animations for all form fields */
.field-list-move {
  transition: transform 0.7s ease;
}

.field-list-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.field-list-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

.field-list-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.field-list-leave-active {
  transition: opacity 0.25s ease;
}

/* Fast fade for confirm password field - with delayed leave */
.confirm-fast-enter-active {
  transition: opacity 0.05s ease;
}

.confirm-fast-leave-active {
  transition: opacity 0.05s ease 0.25s;
}

.confirm-fast-enter-from,
.confirm-fast-leave-to {
  opacity: 0;
}
</style>
