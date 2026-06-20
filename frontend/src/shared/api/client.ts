import axios from 'axios'
import type {
} from '@/shared/types'

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim()
  if (!trimmed) return '/api'
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed
}

function resolveApiBaseUrl(): string {
  const runtimeBaseUrl = window.__SLS_RUNTIME_CONFIG__?.apiBaseUrl
  if (runtimeBaseUrl) return normalizeBaseUrl(runtimeBaseUrl)

  const envBaseUrl = import.meta.env.VITE_API_BASE_URL
  if (envBaseUrl) return normalizeBaseUrl(envBaseUrl)

  return '/api'
}

const client = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 15000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/'
    }
    return Promise.reject(err)
  },
)

export default client
