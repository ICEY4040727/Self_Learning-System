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

const syncAxiosAuthHeader = (token: string | null) => {
  if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete axios.defaults.headers.common['Authorization']
  }
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
      const accessToken = response.data.access_token as string | undefined
      if (!accessToken) {
        throw new Error('登录响应缺少 access_token')
      }

      this.token = accessToken
      localStorage.setItem('token', accessToken)
      syncAxiosAuthHeader(accessToken)
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
      if (!this.token) {
        this.user = null
        syncAxiosAuthHeader(null)
        return null
      }
      syncAxiosAuthHeader(this.token)

      try {
        const response = await axios.get('/api/auth/me')
        this.user = response.data
        return this.user
      } catch (error) {
        this.logout()
        throw error
      }
    },

    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
      syncAxiosAuthHeader(null)
    },

    async initAuth() {
      if (this.token) {
        syncAxiosAuthHeader(this.token)
        try {
          await this.fetchUser()
        } catch {
          // token is stale/invalid, fetchUser already called logout()
        }
      }
    }
  }
})
