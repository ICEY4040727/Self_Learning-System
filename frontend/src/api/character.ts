import client from './client'
import type {
  Character,
  CharacterCreateRequest,
  CharacterFormData,
} from '@/types'

/**
 * Character API
 * 角色管理 API
 */
export const characterApi = {
  /**
   * 获取角色列表
   */
  list: (): Promise<Character[]> =>
    client.get('/character').then(res => res.data),

  /**
   * 创建角色
   * sage 类型会自动创建关联的 TeacherPersona
   */
  create: (data: CharacterCreateRequest): Promise<Character> =>
    client.post('/character', data).then(res => res.data),

  /**
   * 获取单个角色
   */
  get: (id: number): Promise<Character> =>
    client.get(`/character/${id}`).then(res => res.data),

  /**
   * 更新角色
   */
  update: (id: number, data: Partial<CharacterCreateRequest>): Promise<Character> =>
    client.put(`/character/${id}`, data).then(res => res.data),

  /**
   * 删除角色
   */
  delete: (id: number): Promise<void> =>
    client.delete(`/character/${id}`),

  /**
   * 上传角色头像
   */
  uploadAvatar: (id: number, file: File): Promise<{ avatar: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    return client.post(`/character/${id}/avatar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data)
  },

  /**
   * 获取角色统计
   */
  getStats: (): Promise<{
    total_characters: number
    sage_count: number
    traveler_count: number
    active_worlds: number
  }> =>
    client.get('/character/stats').then(res => res.data),

  /**
   * 角色升级
   */
  levelup: (id: number, experiencePoints: number): Promise<{
    id: number
    level: number
    experience_points: number
    message: string
  }> =>
    client.post(`/character/${id}/levelup`, { experience_points: experiencePoints }).then(res => res.data),
}

/**
 * 将 CharacterFormData 转换为 CharacterCreateRequest
 */
export function formDataToCreateRequest(formData: CharacterFormData): CharacterCreateRequest {
  return {
    name: formData.name,
    type: formData.type,
    template_name: formData.template_name,
    avatar: formData.avatar,
    personality: formData.personality,
    background: formData.background,
    speech_style: formData.speech_style,
    tags: formData.tags,
    title: formData.title,
  }
}
