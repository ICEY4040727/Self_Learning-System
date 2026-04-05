<script setup lang="ts">
/**
 * SettingsPage.vue
 * ──────────────────────────────────────────────────────────────
 * Adaptation §2/#3:
 *   Provider options: 'claude' | 'openai' | 'local'
 *   ('local' maps to LocalAdapter in backend; Ollama/local model key is 'local')
 *
 * Adaptation §2:
 *   PUT /api/settings only sends default_provider + api_key (if non-empty).
 *   typewriterOn / autoScrollOn / particlesOn / autoModeDelay are
 *   local-only preferences stored in localStorage via useSettingsStore.
 * ──────────────────────────────────────────────────────────────
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Eye, EyeOff, Check, Key, Monitor, Info } from 'lucide-vue-next'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore }     from '@/stores/auth'
import ParticleBackground   from '@/components/ParticleBackground.vue'
import type { LLMProvider } from '@/types'

const router   = useRouter()
const settings = useSettingsStore()
const auth     = useAuthStore()

const showKey = ref(false)
const saved   = ref(false)
const error   = ref('')
const BG_URL  = 'https://images.unsplash.com/photo-1675371708731-50d9c04eb530?w=1920&q=80'

// §3: provider labels — 'local' replaces 'ollama' to match backend adapter key
const PROVIDERS: Array<{ value: LLMProvider; label: string }> = [
  { value: 'claude', label: 'Claude'    },
  { value: 'openai', label: 'OpenAI'    },
  { value: 'local',  label: 'Local'     },  // backend: elif provider == "local"
]

onMounted(() => settings.fetchSettings())

async function handleSave() {
  error.value = ''
  try {
    // §2: store.saveSettings() only PUTs {default_provider, api_key} to backend.
    //     Local prefs are already auto-saved to localStorage by the store's watchers.
    await settings.saveSettings()
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? '保存失败'
  }
}

function handleLogout() {
  auth.logout()
  router.push('/')
}
</script>

<template>
  <div
    class="relative w-screen h-screen overflow-hidden"
    style="background:#0a0a1e;"
  >
    <div class="absolute inset-0"
      :style="{ backgroundImage:`url(${BG_URL})`, backgroundSize:'cover',
                backgroundPosition:'center', opacity:0.07 }" />
    <div class="absolute inset-0" style="background:linear-gradient(to bottom,
      rgba(10,10,30,0.96) 0%,rgba(10,10,30,0.99) 100%);" />
    <ParticleBackground :count="14" :gold-ratio="0.5" />

    <!-- Header -->
    <div
      class="absolute top-0 left-0 right-0 flex items-center justify-between font-ui"
      style="padding:16px 24px;border-bottom:1px solid rgba(255,215,0,0.1);z-index:10;"
    >
      <button
        class="flex items-center gap-2 galgame-hud-btn"
        style="font-size:13px;padding:6px 14px;"
        @click="router.push('/home')"
      >
        <ArrowLeft :size="14" /> 返回
      </button>
      <span style="color:#ffd700;font-size:16px;letter-spacing:4px;">系 统 设 置</span>
      <div style="width:80px;" />
    </div>

    <!-- Content -->
    <div
      class="absolute inset-0 overflow-y-auto galgame-scrollbar"
      style="padding-top:72px;padding-bottom:32px;padding-left:24px;padding-right:24px;"
    >
      <div style="max-width:600px;margin:0 auto;" class="flex flex-col gap-5">

        <!-- ── API Settings (backend-synced) ─────────────────── -->
        <div class="galgame-panel" style="padding:22px 26px;">
          <div class="flex items-center gap-2 mb-5">
            <Key :size="15" style="color:#ffd700;" />
            <span class="font-ui" style="color:#ffd700;font-size:14px;letter-spacing:2px;">API 设置</span>
            <span class="font-ui" style="font-size:10px;color:rgba(255,255,255,0.25);margin-left:4px;">
              (同步至服务器)
            </span>
          </div>

          <!-- Provider selector — §3: 'local' not 'ollama' -->
          <div class="flex flex-col gap-2 mb-4">
            <label class="font-ui" style="font-size:12px;color:rgba(255,255,255,0.5);letter-spacing:1px;">
              LLM 提供商
            </label>
            <div class="flex gap-2 flex-wrap">
              <button
                v-for="p in PROVIDERS"
                :key="p.value"
                class="galgame-hud-btn"
                :class="{ active: settings.provider === p.value }"
                style="padding:6px 16px;font-size:12px;"
                @click="settings.provider = p.value"
              >{{ p.label }}</button>
            </div>
          </div>

          <!-- API Key -->
          <div class="flex flex-col gap-2 mb-5">
            <label class="font-ui" style="font-size:12px;color:rgba(255,255,255,0.5);letter-spacing:1px;">
              API Key
            </label>
            <div style="position:relative;">
              <input
                v-model="settings.apiKey"
                class="galgame-input font-mono-code w-full"
                style="padding:10px 40px 10px 14px;font-size:13px;"
                :type="showKey ? 'text' : 'password'"
                placeholder="sk-… 或留空保持不变"
                autocomplete="off"
              />
              <button
                type="button"
                style="position:absolute;right:12px;top:50%;transform:translateY(-50%);
                  color:rgba(255,255,255,0.4);cursor:pointer;"
                @click="showKey = !showKey"
              >
                <EyeOff v-if="showKey" :size="15" />
                <Eye v-else :size="15" />
              </button>
            </div>
            <p class="font-ui" style="font-size:11px;color:rgba(255,255,255,0.25);">
              留空不修改；填写后将加密存储于服务端。
            </p>
          </div>

          <!-- Error -->
          <Transition name="err-fade">
            <p v-if="error" class="font-ui mb-3" style="font-size:12px;color:#ef4444;">{{ error }}</p>
          </Transition>

          <!-- Save -->
          <button
            class="galgame-send-btn font-ui"
            style="padding:10px 32px;font-size:13px;letter-spacing:2px;"
            :style="saved ? { background:'rgba(74,223,106,0.85)', color:'#0a0a1e' } : {}"
            @click="handleSave"
          >
            <span v-if="saved" class="flex items-center gap-2">
              <Check :size="14" /> 已保存
            </span>
            <span v-else>保　存</span>
          </button>
        </div>

        <!-- ── Display Settings (local-only, auto-saved to localStorage) ── -->
        <div class="galgame-panel" style="padding:22px 26px;">
          <div class="flex items-center gap-2 mb-5">
            <Monitor :size="15" style="color:#ffd700;" />
            <span class="font-ui" style="color:#ffd700;font-size:14px;letter-spacing:2px;">显示设置</span>
            <span class="font-ui" style="font-size:10px;color:rgba(255,255,255,0.25);margin-left:4px;">
              (本地偏好)
            </span>
          </div>

          <div class="flex flex-col gap-4">
            <div
              v-for="toggle in [
                { label:'打字机效果',     key:'typewriterOn'  },
                { label:'自动滚动',       key:'autoScrollOn'  },
                { label:'粒子背景',       key:'particlesOn'   },
              ] as const"
              :key="toggle.key"
              class="flex items-center justify-between"
            >
              <span class="font-ui" style="font-size:13px;color:rgba(255,255,255,0.75);">
                {{ toggle.label }}
              </span>
              <button
                style="width:44px;height:24px;border-radius:12px;border:none;cursor:pointer;
                  position:relative;transition:background 0.2s ease;"
                :style="{
                  background: (settings as any)[toggle.key]
                    ? 'rgba(255,215,0,0.85)'
                    : 'rgba(255,255,255,0.15)',
                }"
                @click="(settings as any)[toggle.key] = !(settings as any)[toggle.key]"
              >
                <span
                  style="position:absolute;top:2px;width:20px;height:20px;
                    border-radius:50%;background:#fff;transition:left 0.2s ease;"
                  :style="{ left: (settings as any)[toggle.key] ? '22px' : '2px' }"
                />
              </button>
            </div>

            <!-- Auto-mode delay slider -->
            <div class="flex flex-col gap-2 mt-1">
              <div class="flex justify-between font-ui" style="font-size:12px;color:rgba(255,255,255,0.5);">
                <span>自动模式延迟</span>
                <span style="color:rgba(255,215,0,0.7);">{{ settings.autoModeDelay.toFixed(1) }}s</span>
              </div>
              <input
                v-model.number="settings.autoModeDelay"
                type="range" min="1" max="5" step="0.5"
                style="width:100%;accent-color:#ffd700;cursor:pointer;"
              />
            </div>
          </div>
        </div>

        <!-- ── About ──────────────────────────────────────────── -->
        <div class="galgame-panel" style="padding:22px 26px;">
          <div class="flex items-center gap-2 mb-4">
            <Info :size="15" style="color:#ffd700;" />
            <span class="font-ui" style="color:#ffd700;font-size:14px;letter-spacing:2px;">关于</span>
          </div>
          <p class="font-ui" style="font-size:13px;color:rgba(255,255,255,0.55);line-height:1.8;">
            知遇 · Vue 3 版本<br />
            基于苏格拉底教学法的 AI 对话学习系统<br />
            <span style="color:rgba(255,255,255,0.3);">
              当前用户：{{ auth.user?.username ?? '—' }}
            </span>
          </p>
          <button
            class="galgame-hud-btn mt-4"
            style="color:rgba(239,68,68,0.8);border-color:rgba(239,68,68,0.3);"
            @click="handleLogout"
          >退出登录</button>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.err-fade-enter-from, .err-fade-leave-to { opacity: 0; }
.err-fade-enter-active, .err-fade-leave-active { transition: opacity 0.2s ease; }
</style>
