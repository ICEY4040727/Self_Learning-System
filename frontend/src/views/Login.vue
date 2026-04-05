<template>
  <div class="login-page">
    <div class="scene-layer"></div>
    <div class="particle-layer" aria-hidden="true">
      <span
        v-for="particle in particles"
        :key="particle.id"
        class="particle"
        :class="particle.tone"
        :style="particle.style"
      ></span>
    </div>

    <div class="login-container galgame-login-panel">
      <h1 class="title">苏 格 拉 底 学 习 系 统</h1>
      <p class="subtitle">基于苏格拉底教学法的个性化学习系统</p>

      <div class="form">
        <!-- Username -->
        <div class="field">
          <input
            v-model="username"
            type="text"
            :placeholder="isRegisterMode ? '用户名（3-50 字符，字母数字下划线）' : '用户名'"
            class="input galgame-input"
            :class="{ 'input-error': usernameError }"
            @blur="validateUsername"
          />
          <p v-if="usernameError" class="field-error">{{ usernameError }}</p>
        </div>

        <!-- Password -->
        <div class="field">
          <input
            v-model="password"
            type="password"
            :placeholder="isRegisterMode ? '密码（至少 8 位）' : '密码'"
            class="input galgame-input"
            :class="{ 'input-error': passwordError }"
            @input="validatePassword"
            @keyup.enter="isRegisterMode ? handleRegister() : handleLogin()"
          />
          <p v-if="passwordError" class="field-error">{{ passwordError }}</p>
          <div v-if="isRegisterMode && password" class="password-strength">
            <div class="strength-bar">
              <div class="strength-fill" :class="strengthClass" :style="{ width: passwordStrength + '%' }"></div>
            </div>
            <span class="strength-label">{{ strengthLabel }}</span>
          </div>
        </div>

        <!-- Buttons -->
        <div class="buttons" v-if="!isRegisterMode">
          <button class="btn primary galgame-btn" @click="handleLogin" :disabled="isLoading">
            {{ isLoading ? '登录中...' : '登录' }}
          </button>
        </div>
        <div class="buttons" v-else>
          <button class="btn primary galgame-btn" @click="handleRegister" :disabled="isLoading || !isFormValid">
            {{ isLoading ? '注册中...' : '注册' }}
          </button>
        </div>

        <!-- Toggle -->
        <p class="toggle-text">
          <template v-if="!isRegisterMode">
            没有账号？<a class="toggle-link" @click="switchMode">注册新账号</a>
          </template>
          <template v-else>
            已有账号？<a class="toggle-link" @click="switchMode">返回登录</a>
          </template>
        </p>

        <!-- Error -->
        <p v-if="error" class="error">{{ error }}</p>

        <!-- Toast -->
        <Transition name="toast">
          <div v-if="toast" class="toast-success">{{ toast }}</div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const isLoading = ref(false)
const isRegisterMode = ref(false)
const toast = ref('')
const usernameError = ref('')
const passwordError = ref('')

type ParticleTone = 'gold' | 'blue'
interface LoginParticle {
  id: number
  tone: ParticleTone
  style: Record<string, string>
}

const particles: LoginParticle[] = Array.from({ length: 28 }, (_value, index) => {
  const tone: ParticleTone = index < 17 ? 'gold' : 'blue' // ~60% gold
  const left = (index * 37) % 100
  const top = (index * 19) % 100
  return {
    id: index,
    tone,
    style: {
      left: `${left}%`,
      top: `${top}%`,
      animationDuration: `${8 + (index % 5) * 1.4}s`,
      animationDelay: `${(index % 7) * 0.45}s`,
      opacity: `${0.18 + (index % 4) * 0.08}`,
      width: `${2 + (index % 3)}px`,
      height: `${2 + (index % 3)}px`,
    },
  }
})

const validateUsername = () => {
  if (!isRegisterMode.value) { usernameError.value = ''; return }
  if (!username.value) { usernameError.value = ''; return }
  if (username.value.length < 3) {
    usernameError.value = '用户名至少 3 个字符'
  } else if (username.value.length > 50) {
    usernameError.value = '用户名不能超过 50 个字符'
  } else if (!/^[a-zA-Z0-9_-]+$/.test(username.value)) {
    usernameError.value = '只能包含字母、数字、下划线和横杠'
  } else {
    usernameError.value = ''
  }
}

const validatePassword = () => {
  if (!isRegisterMode.value) { passwordError.value = ''; return }
  if (!password.value) { passwordError.value = ''; return }
  if (password.value.length < 8) {
    passwordError.value = `还需要 ${8 - password.value.length} 个字符`
  } else {
    passwordError.value = ''
  }
}

const passwordStrength = computed(() => {
  const p = password.value
  if (!p) return 0
  let score = 0
  if (p.length >= 8) score += 30
  if (p.length >= 12) score += 20
  if (/[A-Z]/.test(p)) score += 15
  if (/[0-9]/.test(p)) score += 15
  if (/[^a-zA-Z0-9]/.test(p)) score += 20
  return Math.min(100, score)
})

const strengthClass = computed(() => {
  if (passwordStrength.value < 40) return 'weak'
  if (passwordStrength.value < 70) return 'medium'
  return 'strong'
})

const strengthLabel = computed(() => {
  if (passwordStrength.value < 40) return '弱'
  if (passwordStrength.value < 70) return '中'
  return '强'
})

const isFormValid = computed(() => {
  return username.value.length >= 3
    && password.value.length >= 8
    && !usernameError.value
    && !passwordError.value
})

const switchMode = () => {
  isRegisterMode.value = !isRegisterMode.value
  error.value = ''
  usernameError.value = ''
  passwordError.value = ''
  password.value = ''
}

const showToast = (msg: string) => {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, 3000)
}

const getPostLoginRedirect = () => {
  const redirect = route.query.redirect
  if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')) {
    return redirect
  }
  return '/home'
}

const handleLogin = async () => {
  error.value = ''
  isLoading.value = true
  try {
    await authStore.login(username.value, password.value)
    password.value = ''
    router.replace(getPostLoginRedirect())
  } catch (e: any) {
    error.value = parseApiError(e)
  } finally {
    isLoading.value = false
  }
}

const handleRegister = async () => {
  validateUsername()
  validatePassword()
  if (usernameError.value || passwordError.value) return

  error.value = ''
  isLoading.value = true
  try {
    await authStore.register(username.value, password.value)
    isRegisterMode.value = false
    password.value = ''
    showToast('注册成功，请登录')
  } catch (e: any) {
    error.value = parseApiError(e)
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.scene-layer {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 50% 25%, rgba(67, 57, 123, 0.26) 0%, rgba(10, 10, 30, 0.94) 62%),
    linear-gradient(180deg, #09091a 0%, #070714 100%);
}

.particle-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.particle {
  position: absolute;
  border-radius: 50%;
  animation: floatParticle linear infinite;
}

.particle.gold {
  background: rgba(255, 215, 0, 0.95);
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.42);
}

.particle.blue {
  background: rgba(96, 165, 250, 0.95);
  box-shadow: 0 0 8px rgba(96, 165, 250, 0.36);
}

.login-container {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 42px 36px;
  width: min(92vw, 420px);
}

.title {
  font-family: var(--font-dialogue);
  font-size: 24px;
  color: var(--accent-gold);
  letter-spacing: 6px;
  margin-bottom: 8px;
  animation: titleGlow 3s ease-in-out infinite;
}

@keyframes titleGlow {
  0%, 100% { text-shadow: 0 0 10px rgba(255, 215, 0, 0.3); }
  50% { text-shadow: 0 0 25px rgba(255, 215, 0, 0.5); }
}

.subtitle {
  color: var(--text-muted);
  font-size: 13px;
  margin-bottom: 30px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  text-align: left;
}

.input {
  width: 100%;
  padding: 14px;
  color: var(--text-primary);
  font-size: 15px;
  font-family: var(--font-ui);
  box-sizing: border-box;
}

.input::placeholder {
  color: var(--text-muted);
}

.input-error {
  border-color: var(--emotion-negative);
}

.field-error {
  color: var(--emotion-negative);
  font-size: 12px;
  margin-top: 4px;
}

/* Password strength */
.password-strength {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.strength-bar {
  flex: 1;
  height: 4px;
  background: var(--bg-secondary);
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 2px;
  transition: all var(--transition-normal);
}

.strength-fill.weak { background: var(--emotion-negative); }
.strength-fill.medium { background: var(--accent-orange); }
.strength-fill.strong { background: var(--emotion-positive); }

.strength-label {
  font-size: 11px;
  color: var(--text-muted);
  min-width: 16px;
}

/* Buttons */
.buttons {
  margin-top: 6px;
}

.btn {
  width: 100%;
  padding: 14px;
  font-size: 16px;
  font-family: var(--font-ui);
  transition: all var(--transition-normal);
}

.btn.primary {
  background: linear-gradient(135deg, var(--accent-gold), var(--accent-orange));
  color: var(--bg-primary);
  font-weight: bold;
}

.btn.primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* Toggle */
.toggle-text {
  font-size: 13px;
  color: var(--text-muted);
}

.toggle-link {
  color: var(--accent-gold);
  cursor: pointer;
  text-decoration: none;
  transition: opacity var(--transition-fast);
}

.toggle-link:hover {
  opacity: 0.8;
}

/* Error + Toast */
.error {
  color: var(--emotion-negative);
  font-size: 13px;
}

.toast-success {
  background: rgba(74, 138, 74, 0.9);
  color: #fff;
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 13px;
}

.toast-enter-active, .toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from, .toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
