<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Eye, EyeOff } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import ParticleBackground from '@/components/ParticleBackground.vue'

const router = useRouter()
const auth   = useAuthStore()

const mode      = ref<'login' | 'register'>('login')
const username  = ref('')
const password  = ref('')
const confirmPw = ref('')
const showPw    = ref(false)
const error     = ref('')
const loading   = ref(false)

let errorTimer: ReturnType<typeof setTimeout> | null = null

function setError(msg: string) {
  error.value = msg
  if (errorTimer) clearTimeout(errorTimer)
  errorTimer = setTimeout(() => { error.value = '' }, 3000)
}

async function handleSubmit() {
  if (loading.value) return
  error.value = ''

  if (!username.value.trim() || !password.value.trim()) {
    setError('请填写用户名和密码'); return
  }
  if (mode.value === 'register' && password.value !== confirmPw.value) {
    setError('两次密码不一致'); return
  }

  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(username.value.trim(), password.value)
    } else {
      await auth.register(username.value.trim(), password.value)
    }
    router.push('/home')
  } catch (e: any) {
    setError(e?.response?.data?.detail ?? '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

const BG_URL =
  'https://images.unsplash.com/photo-1663318971958-8e9e1cead755?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=1080&q=80'
</script>

<template>
  <div
    class="relative w-screen h-screen overflow-hidden flex items-center justify-center"
    style="background:#0a0a1e;"
  >
    <!-- Background -->
    <div
      class="absolute inset-0"
      :style="{ backgroundImage:`url(${BG_URL})`, backgroundSize:'cover',
                backgroundPosition:'center', opacity:0.12 }"
    />
    <div class="absolute inset-0" style="background:linear-gradient(to bottom,
      rgba(10,10,30,0.85) 0%,rgba(10,10,30,0.95) 100%);" />
    <ParticleBackground :count="28" :gold-ratio="0.6" />

    <!-- Login panel -->
    <div
      class="galgame-login-panel relative z-10"
      style="width:360px;max-width:90vw;padding:40px 36px 36px;"
    >
      <!-- Title -->
      <div class="text-center mb-8">
        <h1
          class="breathe-glow font-dialogue"
          style="font-size:30px;letter-spacing:8px;color:#ffd700;margin-bottom:6px;"
        >知　遇</h1>
        <p class="font-ui" style="font-size:12px;letter-spacing:3px;color:rgba(255,255,255,0.4);">
          智慧的旅程从这里开始
        </p>
      </div>

      <!-- Toggle -->
      <div class="flex mb-6" style="border-bottom:1px solid rgba(255,215,0,0.15);">
        <button
          v-for="m in (['login','register'] as const)"
          :key="m"
          class="font-ui flex-1 pb-3"
          :style="{
            fontSize: '13px', letterSpacing: '2px',
            color: mode === m ? '#ffd700' : 'rgba(255,255,255,0.4)',
            borderBottom: mode === m ? '2px solid #ffd700' : '2px solid transparent',
            marginBottom: '-1px', transition: 'all 0.2s ease',
            cursor: 'pointer',
          }"
          @click="mode = m; error = ''"
        >{{ m === 'login' ? '登 录' : '注 册' }}</button>
      </div>

      <!-- Form -->
      <form class="flex flex-col gap-3" @submit.prevent="handleSubmit">
        <input
          v-model="username"
          class="galgame-input font-ui"
          style="padding:10px 14px;font-size:14px;width:100%;"
          placeholder="用户名"
          autocomplete="username"
        />
        <div style="position:relative;">
          <input
            v-model="password"
            class="galgame-input font-ui"
            style="padding:10px 40px 10px 14px;font-size:14px;width:100%;"
            :type="showPw ? 'text' : 'password'"
            placeholder="密码"
            autocomplete="current-password"
          />
          <button
            type="button"
            style="position:absolute;right:12px;top:50%;transform:translateY(-50%);
              color:rgba(255,255,255,0.4);cursor:pointer;"
            @click="showPw = !showPw"
          >
            <EyeOff v-if="showPw" :size="16" />
            <Eye v-else :size="16" />
          </button>
        </div>

        <!-- Register: confirm password -->
        <Transition name="form-slide">
          <input
            v-if="mode === 'register'"
            v-model="confirmPw"
            class="galgame-input font-ui"
            style="padding:10px 14px;font-size:14px;width:100%;"
            type="password"
            placeholder="确认密码"
          />
        </Transition>

        <!-- Error -->
        <Transition name="error-fade">
          <p
            v-if="error"
            class="font-ui"
            style="font-size:12px;color:#df4a4a;letter-spacing:1px;"
          >{{ error }}</p>
        </Transition>

        <!-- Submit -->
        <button
          type="submit"
          class="galgame-send-btn font-ui mt-2"
          style="padding:12px;font-size:14px;letter-spacing:3px;width:100%;"
          :disabled="loading"
        >
          {{ loading ? '进入中…' : (mode === 'login' ? '踏入旅途' : '开启旅程') }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.form-slide-enter-from { opacity: 0; transform: translateY(-8px); max-height: 0; }
.form-slide-enter-active { transition: opacity 0.25s ease, transform 0.25s ease, max-height 0.25s ease; max-height: 60px; }
.form-slide-leave-to { opacity: 0; transform: translateY(-8px); max-height: 0; }
.form-slide-leave-active { transition: opacity 0.2s ease, max-height 0.2s ease; }
.error-fade-enter-from, .error-fade-leave-to { opacity: 0; }
.error-fade-enter-active, .error-fade-leave-active { transition: opacity 0.2s ease; }
</style>
