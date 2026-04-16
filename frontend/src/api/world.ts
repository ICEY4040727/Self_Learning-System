/**
 * World API Module
 * Issue #29 + #32: 统一 API 调用层
 */
import client from './client'
import type { World } from '@/types'

export const worldApi = {
  /**
   * 获取世界列表
   */
  list: (): Promise<World[]> =>
    client.get('/worlds').then(res => res.data),

  /**
   * 获取单个世界详情
   */
  get: (id: number): Promise<World> =>
    client.get(`/worlds/${id}`).then(res => res.data),

  /**
   * 创建新世界
   */
  create: (data: { name: string; description?: string }): Promise<World> =>
    client.post('/worlds', data).then(res => res.data),

  /**
   * 更新世界
   */
  update: (id: number, data: Partial<World>): Promise<World> =>
    client.put(`/worlds/${id}`, data).then(res => res.data),

  /**
   * 删除世界
   */
  delete: (id: number): Promise<void> =>
    client.delete(`/worlds/${id}`),

  /**
   * 获取世界的课程列表
   */
  getCourses: (id: number) =>
    client.get(`/worlds/${id}/courses`).then(res => res.data),

  /**
   * 获取世界的角色列表
   */
  getCharacters: (id: number) =>
    client.get(`/worlds/${id}/characters`).then(res => res.data),

  /**
   * 向世界添加角色
   */
  addCharacter: (worldId: number, characterId: number) =>
    client.post(`/worlds/${worldId}/characters`, { character_id: characterId }),

  /**
   * 从世界移除角色
   */
  removeCharacter: (worldId: number, characterId: number) =>
    client.delete(`/worlds/${worldId}/characters/${characterId}`),

  /**
   * 获取世界的存档列表
   */
  getCheckpoints: (id: number) =>
    client.get(`/worlds/${id}/checkpoints`).then(res => res.data),

  /**
   * 获取世界时间线
   */
  getTimelines: (id: number) =>
    client.get(`/worlds/${id}/timelines`).then(res => res.data),
}
