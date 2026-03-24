import { defineStore } from 'pinia'
import axios from 'axios'

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

      const response = await axios.post('/api/auth/login', formData)
      this.token = response.data.access_token
      localStorage.setItem('token', this.token!)

      axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`

      await this.fetchUser()
    },

    async register(username: string, password: string) {
      await axios.post('/api/auth/register', {
        username,
        password,
        tenant_name: 'default'
      })
    },

    async fetchUser() {
      if (!this.token) return

      axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`

      try {
        const response = await axios.get('/api/auth/me')
        this.user = response.data
      } catch (error) {
        this.logout()
      }
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      delete axios.defaults.headers.common['Authorization']
    },

    async initAuth() {
      if (this.token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        await this.fetchUser()
      }
    }
  }
})