/**
 * stores/settings.ts
 * ──────────────────────────────────────────────────────────────
 * Adaptation §2/#2/#3:
 *   - Provider, key, model, base URL, and LLM params go to the backend.
 *   - Local UI preferences (typewriterOn, etc.) live in localStorage only.
 *   - Provider enum: 'claude' | 'openai' | 'local'  (not 'ollama').
 *     Backend adapter key for Ollama/local models is 'local'.
 * ──────────────────────────────────────────────────────────────
 */
import { defineStore } from 'pinia'
import { ref, watch }  from 'vue'
import client          from '@/shared/api/client'
import type { LLMProvider } from '@/shared/types'

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

const LS_TEMPERATURE = `${LS_PREFIX}temperature`
const LS_MAX_TOKENS   = `${LS_PREFIX}max_tokens`

export const useSettingsStore = defineStore('settings', () => {
  // ── Backend-synced fields ─────────────────────────────────────
  // Adapted §3: 'local' not 'ollama'
  const provider = ref<LLMProvider>('claude')
  const apiKey   = ref('')
  const model    = ref('')
  const baseUrl  = ref('')
  const apiKeyConfigured = ref(false)
  const providerSettings = ref<Record<string, {
    api_key_configured: boolean
    model: string | null
    base_url: string | null
  }>>({})
  const settingsVersion = ref(0)

  // ── Local-only UI preferences (localStorage) ─────────────────
  const typewriterOn   = ref(lsBool(LS_TYPEWRITER,  true))
  const autoScrollOn   = ref(lsBool(LS_AUTOSCROLL,  true))
  const particlesOn    = ref(lsBool(LS_PARTICLES,   true))
  const autoModeDelay  = ref(lsNumber(LS_AUTO_DELAY, 2.8))
  const temperature    = ref(lsNumber(LS_TEMPERATURE, 0.7))
  const maxTokens      = ref(lsNumber(LS_MAX_TOKENS, 2048))

  // Persist local prefs to localStorage on change
  watch(typewriterOn,  v => localStorage.setItem(LS_TYPEWRITER, v ? '1' : '0'))
  watch(autoScrollOn,  v => localStorage.setItem(LS_AUTOSCROLL, v ? '1' : '0'))
  watch(particlesOn,   v => localStorage.setItem(LS_PARTICLES,  v ? '1' : '0'))
  watch(autoModeDelay, v => localStorage.setItem(LS_AUTO_DELAY, String(v)))
  watch(temperature,    v => localStorage.setItem(LS_TEMPERATURE, String(v)))
  watch(maxTokens,      v => localStorage.setItem(LS_MAX_TOKENS, String(v)))

  function applyProviderSettings(nextProvider: LLMProvider) {
    provider.value = nextProvider
    const snapshot = providerSettings.value[nextProvider]
    apiKey.value = ''
    apiKeyConfigured.value = snapshot?.api_key_configured ?? false
    model.value = snapshot?.model ?? ''
    baseUrl.value = snapshot?.base_url ?? ''
  }

  // ── Actions ───────────────────────────────────────────────────
  // Read backend-synced LLM settings; UI-only prefs remain local.
  async function fetchSettings() {
    try {
      const { data } = await client.get<{
        version: number
        default_provider: string | null
        api_key_configured: boolean
        temperature: number | null
        max_tokens: number | null
        model: string | null
        base_url: string | null
        provider_settings?: Record<string, {
          api_key_configured: boolean
          model: string | null
          base_url: string | null
        }>
      }>('/settings')
      settingsVersion.value = data.version ?? 0
      providerSettings.value = data.provider_settings ?? {}
      if (data.default_provider) {
        applyProviderSettings(data.default_provider as LLMProvider)
      } else {
        applyProviderSettings(provider.value)
      }
      apiKeyConfigured.value = data.api_key_configured
      if (typeof data.temperature === 'number') {
        temperature.value = data.temperature
      }
      if (typeof data.max_tokens === 'number') {
        maxTokens.value = data.max_tokens
      }
      if (!model.value && data.model) {
        model.value = data.model
      }
      if (!baseUrl.value && data.base_url) {
        baseUrl.value = data.base_url
      }
      // Local preferences are already loaded from localStorage above — don't overwrite
    } catch {
      // Unauthenticated or server error — keep defaults
    }
  }

  // Save backend-synced LLM settings.
  async function saveSettings() {
    const payload: Record<string, string | number> = {
      version: settingsVersion.value,
      default_provider: provider.value,
      temperature: temperature.value,
      max_tokens: maxTokens.value,
      model: model.value.trim(),
      base_url: baseUrl.value.trim(),
    }
    const submittedApiKey = apiKey.value.trim()
    if (submittedApiKey) {
      payload.api_key = submittedApiKey
    }
    const { data } = await client.put<{ message: string; version: number }>('/settings', payload)
    if (typeof data.version === 'number') {
      settingsVersion.value = data.version
    }
    if (submittedApiKey) {
      apiKeyConfigured.value = true
    }
    apiKey.value = ''
    providerSettings.value[provider.value] = {
      api_key_configured: apiKeyConfigured.value,
      model: model.value.trim() || null,
      base_url: baseUrl.value.trim() || null,
    }
  }

  async function clearApiKey() {
    const { data } = await client.put<{ message: string; version: number }>('/settings', {
      version: settingsVersion.value,
      default_provider: provider.value,
      clear_api_key: true,
    })
    if (typeof data.version === 'number') {
      settingsVersion.value = data.version
    }
    apiKey.value = ''
    apiKeyConfigured.value = false
    providerSettings.value[provider.value] = {
      api_key_configured: false,
      model: model.value.trim() || null,
      base_url: baseUrl.value.trim() || null,
    }
  }

  async function testConnection() {
    const payload: Record<string, string | number> = {
      default_provider: provider.value,
      temperature: temperature.value,
      max_tokens: maxTokens.value,
      model: model.value.trim(),
      base_url: baseUrl.value.trim(),
    }
    const submittedApiKey = apiKey.value.trim()
    if (submittedApiKey) {
      payload.api_key = submittedApiKey
    }
    const { data } = await client.post<{
      ok: boolean
      provider: string
      model: string | null
      base_url: string | null
      message: string
    }>('/settings/test-connection', payload)
    return data
  }

  async function fetchAvailableModels() {
    const payload: Record<string, string> = {
      default_provider: provider.value,
      model: model.value.trim(),
      base_url: baseUrl.value.trim(),
    }
    const submittedApiKey = apiKey.value.trim()
    if (submittedApiKey) {
      payload.api_key = submittedApiKey
    }
    const { data } = await client.post<{
      provider: string
      base_url: string | null
      source: string
      models: string[]
      message: string | null
    }>('/settings/models', payload)
    return data
  }

  return {
    // Backend fields
    provider, apiKey, model, baseUrl, apiKeyConfigured, providerSettings, settingsVersion,
    // Local-only fields
    typewriterOn, autoScrollOn, particlesOn, autoModeDelay,
    temperature, maxTokens,
    applyProviderSettings, fetchSettings, saveSettings, clearApiKey, testConnection, fetchAvailableModels,
  }
})
