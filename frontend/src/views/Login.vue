<template>
  <div class="login-page">
    <div class="login-container">
      <h1 class="title">苏格拉底学习系统</h1>
      <p class="subtitle">基于苏格拉底教学法的个性化学习系统</p>

      <div class="form">
        <input
          v-model="username"
          type="text"
          placeholder="用户名"
          class="input"
        />
        <input
          v-model="password"
          type="password"
          placeholder="密码"
          class="input"
          @keyup.enter="handleLogin"
        />

        <div class="buttons">
          <button class="btn primary" @click="handleLogin">
            登录
          </button>
          <button class="btn secondary" @click="handleRegister">
            注册
          </button>
        </div>

        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')

const handleLogin = async () => {
  error.value = ''
  try {
    await authStore.login(username.value, password.value)
    router.push('/home')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '登录失败'
  }
}

const handleRegister = async () => {
  error.value = ''
  try {
    await authStore.register(username.value, password.value)
    alert('注册成功，请登录')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '注册失败'
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.login-container {
  text-align: center;
  padding: 40px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 20px;
  border: 2px solid #4a4a8a;
  max-width: 400px;
  width: 100%;
}

.title {
  font-size: 28px;
  color: #ffd700;
  margin-bottom: 10px;
}

.subtitle {
  color: #aaa;
  margin-bottom: 30px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.input {
  padding: 15px;
  background: #1a1a2e;
  border: 1px solid #4a4a8a;
  border-radius: 8px;
  color: #fff;
  font-size: 16px;
}

.input:focus {
  outline: none;
  border-color: #ffd700;
}

.buttons {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.btn {
  flex: 1;
  padding: 15px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn.primary {
  background: linear-gradient(135deg, #ffd700, #ff8c00);
  color: #1a1a2e;
  font-weight: bold;
}

.btn.primary:hover {
  transform: scale(1.02);
}

.btn.secondary {
  background: #2a2a4a;
  color: #fff;
}

.btn.secondary:hover {
  background: #3a3a5a;
}

.error {
  color: #ff6b6b;
  margin-top: 10px;
}
</style>