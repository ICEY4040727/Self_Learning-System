/**
 * Characters Composable
 * Issue #29: 统一 API 调用层
 */
import { ref } from 'vue'
import { characterApi } from '@/api/character'
import { FALLBACK_CHARACTERS } from '@/constants/characterPresets'
import type { Character } from '@/types'

export function useCharacters() {
  const characters = ref<Character[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchCharacters() {
    loading.value = true
    error.value = null
    try {
      const data = await characterApi.list()
      characters.value = data.map((c: any) => ({
        ...c,
        avatar: c.avatar || c.avatar_url,
      }))
      if (characters.value.length === 0) {
        characters.value = FALLBACK_CHARACTERS as Character[]
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取角色列表失败'
      characters.value = FALLBACK_CHARACTERS as Character[]
    } finally {
      loading.value = false
    }
  }

  async function deleteCharacter(id: number) {
    try {
      await characterApi.delete(id)
      characters.value = characters.value.filter(c => c.id !== id)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '删除角色失败'
      throw e
    }
  }

  async function createCharacter(data: any) {
    try {
      const newChar = await characterApi.create(data)
      characters.value.push(newChar)
      return newChar
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '创建角色失败'
      throw e
    }
  }

  return {
    characters,
    loading,
    error,
    fetchCharacters,
    deleteCharacter,
    createCharacter,
  }
}
