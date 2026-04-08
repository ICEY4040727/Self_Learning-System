import axios from 'axios'
import type {
  MasteryTrendResponse,
  MilestoneEvent,
  RelationshipHistoryResponse,
  UserProfile,
  WorldComparisonItem,
  WorldMasteryTrendItem,
} from '@/types'

// Base URL from env; fallback to same-origin /api
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
})

// Attach Bearer token on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 globally — clear token and redirect to login
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

// ---- UserProfile API ----
export const userProfileApi = {
  /** 获取用户画像 - 直接返回 profile 对象 */
  get: async (): Promise<UserProfile> => {
    const { data } = await client.get('/user/profile')
    // 后端直接返回 profile，不包装 { success, data }
    return data
  },
  
  /** 刷新用户画像 */
  refresh: async (force = false): Promise<UserProfile> => {
    const { data } = await client.post('/user/profile/refresh', { force })
    // refresh 端点仍返回 { success, data } 格式
    return data.data ?? data
  },
}

// ---- Report API ----
export const reportApi = {
  /** 获取跨世界的知识掌握度趋势 */
  getMasteryTrends: (): Promise<{ data: MasteryTrendResponse }> =>
    client.get('/report/mastery-trends'),
  
  /** 获取关系进化历程 */
  getRelationshipHistory: (): Promise<{ data: RelationshipHistoryResponse }> =>
    client.get('/report/relationship-history'),
  
  /** 获取世界对比数据 */
  getWorldComparison: (): Promise<{ data: WorldComparisonItem[] }> =>
    client.get('/report/world-comparison'),
  
  /** 获取里程碑事件 */
  getMilestones: (worldId?: number): Promise<{ data: MilestoneEvent[] }> =>
    client.get('/report/milestones', {
      params: worldId ? { world_id: worldId } : undefined,
    }),
  
  /** 获取单个世界的掌握度趋势 */
  getWorldMasteryTrends: (worldId: number): Promise<{ data: WorldMasteryTrendItem[] }> =>
    client.get(`/report/worlds/${worldId}/mastery-trends`),
}
