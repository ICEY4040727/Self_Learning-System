import { defineStore } from 'pinia'
import client from '@/api/client'

interface User {
  id: number
  username: string
  role: string
  encrypted_api_key?: string
  default_provider?: string
}

interface AuthState {
  token: string | null
  user: User | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('token'),
    user: null
  }),

  getters: {
    isAuthenticated: (state) => !!state.token
  },

  actions: {
    async login(username: string, password: string) {
      const formData = new FormData()
      formData.append('username', username)
      formData.append('password', password)

      const { data } = await client.post('/auth/login', formData)
      this.token = data.access_token
      localStorage.setItem('token', this.token!)

      await this.fetchUser()
    },

    async register(username: string, password: string) {
      await client.post('/auth/register', {
        username,
        password,
        tenant_name: 'default'
      })
    },

    async fetchUser() {
      if (!this.token) return

      try {
        const { data } = await client.get('/auth/me')
        this.user = data
      } catch (error) {
        this.logout()
      }
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
    },

    async initAuth() {
      if (this.token) {
        await this.fetchUser()
      }
    }
  }
})
