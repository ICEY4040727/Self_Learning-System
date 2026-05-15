/**
 * World API Module
 * Issue #29 + #32: 统一 API 调用层
 */
import client from './client'
import type { World, WorldCharacter, WorldCharacterContextInput } from '@/types'

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
  create: (data: { name: string; description?: string; background_picture?: string }): Promise<World> =>
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
   * 创建课程
   */
  createCourse: (worldId: number, data: Record<string, any>) =>
    client.post(`/worlds/${worldId}/courses`, data).then(res => res.data),

  /**
   * 获取世界的角色列表
   */
  getCharacters: (id: number) =>
    client.get(`/worlds/${id}/characters`).then(res => res.data),

  /**
   * 向世界添加角色
   */
  addCharacter: (
    worldId: number,
    characterId: number,
    role: 'sage' | 'traveler',
    context: WorldCharacterContextInput = {},
  ): Promise<WorldCharacter> =>
    client.post(`/worlds/${worldId}/characters`, {
      character_id: characterId,
      role,
      ...context,
    }).then(res => res.data),

  /**
   * 生成世界角色上下文
   */
  generateCharacterContext: (
    worldId: number,
    characterId: number,
    role?: 'sage' | 'traveler',
    seedHint?: string,
  ): Promise<WorldCharacterContextInput & { warnings?: string[] }> =>
    client.post(`/worlds/${worldId}/characters/${characterId}/generate-context`, {
      role,
      seed_hint: seedHint,
    }).then(res => res.data),

  /**
   * 更新世界角色上下文
   */
  updateWorldCharacterContext: (
    worldId: number,
    characterId: number,
    context: WorldCharacterContextInput,
  ): Promise<WorldCharacter> =>
    client.patch(`/worlds/${worldId}/characters/${characterId}`, context).then(res => res.data),

  /**
   * 从世界移除角色
   */
  removeCharacter: (worldId: number, characterId: number) =>
    client.delete(`/worlds/${worldId}/characters/${characterId}`),

  /**
   * 设置角色为世界的主角色（自动处理绑定/未绑定状态）
   * 后端 PUT /worlds/{world_id}/characters/{character_id}/set-primary
   */
  setPrimary: (worldId: number, characterId: number) =>
    client.put(`/worlds/${worldId}/characters/${characterId}/set-primary`).then(res => res.data),

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

  /**
   * AI 生成世界设定
   */
  generateWorld: (description: string): Promise<{
    name_suggestion: string
    description: string
    background_picture?: string
    theme_preset?: string
    mood_tags?: string[]
    bgm_suggestion?: string
    world_detail?: string
  }> =>
    client.post('/world/generate', { description }).then(res => res.data),
}
