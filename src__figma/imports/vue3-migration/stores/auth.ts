import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import client from '@/api/client'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // ── State ────────────────────────────────────────────────────
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user  = ref<User | null>(null)

  // ── Getters ──────────────────────────────────────────────────
  const isLoggedIn = computed(() => !!token.value)

  // ── Actions ──────────────────────────────────────────────────
  async function login(username: string, password: string) {
    // FastAPI OAuth2PasswordRequestForm — must be FormData
    const form = new FormData()
    form.append('username', username)
    form.append('password', password)
    const { data } = await client.post('/auth/login', form)
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    await fetchMe()
  }

  async function register(username: string, password: string) {
    await client.post('/auth/register', { username, password })
    await login(username, password)
  }

  async function fetchMe() {
    const { data } = await client.get('/auth/me')
    user.value = data as User
  }

  function logout() {
    token.value = null
    user.value  = null
    localStorage.removeItem('access_token')
  }

  return { token, user, isLoggedIn, login, register, fetchMe, logout }
})
