import { defineStore } from 'pinia'
import { ref } from 'vue'
import client from '@/api/client'
import type {
  World, Course, Checkpoint, Timeline, WorldCharacter, Character,
} from '@/types'

export const useWorldStore = defineStore('world', () => {
  // ── State ────────────────────────────────────────────────────
  const worlds          = ref<World[]>([])
  const selectedWorld   = ref<World | null>(null)
  const selectedCourse  = ref<Course | null>(null)
  const timelines       = ref<Timeline | null>(null)
  const checkpoints     = ref<Checkpoint[]>([])
  const loading         = ref(false)
  const error           = ref<string | null>(null)

  // ── Worlds ───────────────────────────────────────────────────
  async function fetchWorlds() {
    loading.value = true
    try {
      const { data } = await client.get('/worlds')
      worlds.value = data as World[]
    } finally {
      loading.value = false
    }
  }

  async function createWorld(payload: { name: string; description: string }) {
    const { data } = await client.post('/worlds', payload)
    worlds.value.push(data as World)
    return data as World
  }

  // ── Courses ──────────────────────────────────────────────────
  async function fetchCourses(worldId: number) {
    const { data } = await client.get(`/worlds/${worldId}/courses`)
    if (selectedWorld.value?.id === worldId) {
      selectedWorld.value = { ...selectedWorld.value, courses: data as Course[] }
    }
    return data as Course[]
  }

  async function createCourse(worldId: number, payload: Partial<Course>) {
    const { data } = await client.post(`/worlds/${worldId}/courses`, payload)
    if (selectedWorld.value?.id === worldId) {
      const courses = selectedWorld.value.courses ?? []
      selectedWorld.value = { ...selectedWorld.value, courses: [...courses, data as Course] }
    }
    return data as Course
  }

  async function deleteCourse(courseId: number) {
    await client.delete(`/courses/${courseId}`)
  }

  // ── World characters ─────────────────────────────────────────
  async function fetchWorldCharacters(worldId: number): Promise<WorldCharacter[]> {
    const { data } = await client.get(`/worlds/${worldId}/characters`)
    return data as WorldCharacter[]
  }

  async function bindCharacterToWorld(
    worldId: number,
    characterId: number,
    role: 'sage' | 'traveler',
    isPrimary = false,
  ) {
    const { data } = await client.post(`/worlds/${worldId}/characters`, {
      character_id: characterId,
      role,
      is_primary: isPrimary,
    })
    return data as WorldCharacter
  }

  // ── Characters ───────────────────────────────────────────────
  async function fetchCharacters(): Promise<Character[]> {
    const { data } = await client.get('/character')
    return data as Character[]
  }

  async function createCharacter(payload: Partial<Character>) {
    const { data } = await client.post('/character', payload)
    return data as Character
  }

  async function deleteCharacter(characterId: number) {
    await client.delete(`/character/${characterId}`)
  }

  // ── Timelines ────────────────────────────────────────────────
  async function fetchTimelines(worldId: number) {
    const { data } = await client.get(`/worlds/${worldId}/timelines`)
    timelines.value = data as Timeline
  }

  // ── Checkpoints ──────────────────────────────────────────────
  async function fetchCheckpoints(worldId: number) {
    const { data } = await client.get(`/worlds/${worldId}/checkpoints`)
    checkpoints.value = data as Checkpoint[]
  }

  // Branch from checkpoint → returns new session info
  async function branchCheckpoint(checkpointId: number) {
    const { data } = await client.post(`/checkpoints/${checkpointId}/branch`)
    return data as { session_id: number; course_id: number; world_id: number }
  }

  // ── Select helpers ───────────────────────────────────────────
  function selectWorld(world: World) {
    selectedWorld.value = world
    selectedCourse.value = null
    timelines.value = null
    checkpoints.value = []
  }

  function selectCourse(course: Course) {
    selectedCourse.value = course
  }

  function reset() {
    worlds.value         = []
    selectedWorld.value  = null
    selectedCourse.value = null
    timelines.value      = null
    checkpoints.value    = []
  }

  return {
    worlds, selectedWorld, selectedCourse, timelines, checkpoints, loading, error,
    fetchWorlds, createWorld,
    fetchCourses, createCourse, deleteCourse,
    fetchWorldCharacters, bindCharacterToWorld,
    fetchCharacters, createCharacter, deleteCharacter,
    fetchTimelines, fetchCheckpoints, branchCheckpoint,
    selectWorld, selectCourse, reset,
  }
})
