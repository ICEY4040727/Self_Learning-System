/**
 * stores/settings.ts
 * ──────────────────────────────────────────────────────────────
 * Adaptation §2/#2/#3:
 *   - Only `default_provider` + `api_key` go to the backend.
 *   - Local UI preferences (typewriterOn, etc.) live in localStorage only.
 *   - Provider enum: 'claude' | 'openai' | 'local'  (not 'ollama').
 *     Backend adapter key for Ollama/local models is 'local'.
 * ──────────────────────────────────────────────────────────────
 */
import { defineStore } from 'pinia'
import { ref, watch }  from 'vue'
import client          from '@/api/client'
import type { LLMProvider } from '@/types'

// ---- localStorage keys for local-only preferences ----
const LS_PREFIX        = 'zhiyu_ui_'
const LS_TYPEWRITER    = `${LS_PREFIX}typewriter`
const LS_AUTOSCROLL    = `${LS_PREFIX}autoscroll`
const LS_PARTICLES     = `${LS_PREFIX}particles`
const LS_AUTO_DELAY    = `${LS_PREFIX}auto_delay`

function lsBool(key: string, fallback: boolean): boolean {
  const v = localStorage.getItem(key)
  return v === null ? fallback : v === '1'
}

function lsNumber(key: string, fallback: number): number {
  const v = localStorage.getItem(key)
  return v === null ? fallback : parseFloat(v)
}

export const useSettingsStore = defineStore('settings', () => {
  // ── Backend-synced fields ─────────────────────────────────────
  // Adapted §3: 'local' not 'ollama'
  const provider = ref<LLMProvider>('claude')
  const apiKey   = ref('')

  // ── Local-only UI preferences (localStorage) ─────────────────
  const typewriterOn   = ref(lsBool(LS_TYPEWRITER,  true))
  const autoScrollOn   = ref(lsBool(LS_AUTOSCROLL,  true))
  const particlesOn    = ref(lsBool(LS_PARTICLES,   true))
  const autoModeDelay  = ref(lsNumber(LS_AUTO_DELAY, 2.8))

  // Persist local prefs to localStorage on change
  watch(typewriterOn,  v => localStorage.setItem(LS_TYPEWRITER, v ? '1' : '0'))
  watch(autoScrollOn,  v => localStorage.setItem(LS_AUTOSCROLL, v ? '1' : '0'))
  watch(particlesOn,   v => localStorage.setItem(LS_PARTICLES,  v ? '1' : '0'))
  watch(autoModeDelay, v => localStorage.setItem(LS_AUTO_DELAY, String(v)))

  // ── Actions ───────────────────────────────────────────────────
  // Adapted §2: only read `default_provider` from backend response
  async function fetchSettings() {
    try {
      const { data } = await client.get<{ default_provider: string | null }>('/settings')
      if (data.default_provider) {
        provider.value = data.default_provider as LLMProvider
      }
      // Local preferences are already loaded from localStorage above — don't overwrite
    } catch {
      // Unauthenticated or server error — keep defaults
    }
  }

  // Adapted §2: PUT only `default_provider` + optionally `api_key`
  async function saveSettings() {
    const payload: Record<string, string> = {
      default_provider: provider.value,
    }
    if (apiKey.value.trim()) {
      payload.api_key = apiKey.value.trim()
    }
    await client.put('/settings', payload)
  }

  return {
    // Backend fields
    provider, apiKey,
    // Local-only fields
    typewriterOn, autoScrollOn, particlesOn, autoModeDelay,
    fetchSettings, saveSettings,
  }
})
