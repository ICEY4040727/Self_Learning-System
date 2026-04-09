/**
 * API client for memory facts endpoints
 */
import client from './client'

export interface MemoryFact {
  id: number
  fact_type: string
  content: string
  concept_tags?: string[]
  salience: number
  created_at: string
  recall_count: number
}

export interface MemoryStats {
  total: number
  by_type: Record<string, number>
  avg_salience: number
}

export interface MemoryFactsResponse {
  stats: MemoryStats
  facts: MemoryFact[]
}

export const memoryApi = {
  /**
   * 获取课程关联的记忆事实
   * @param courseId 课程 ID
   * @param statsOnly 是否只返回统计
   */
  getMemoryFacts: (courseId: number, statsOnly = false): Promise<MemoryFactsResponse> =>
    client.get(`/courses/${courseId}/memory-facts`, {
      params: { stats_only: statsOnly },
    }).then(res => res.data),
}
