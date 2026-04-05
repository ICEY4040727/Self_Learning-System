import type { LocationQueryRaw } from 'vue-router'

interface LearningQueryInput {
  worldId?: number | null
  sessionId?: number | null
}

const isPositiveInteger = (value: number | null | undefined): value is number =>
  value != null && Number.isInteger(value) && value > 0

export const parseQueryNumber = (value: unknown): number | undefined => {
  const normalized = Array.isArray(value) ? value[0] : value
  if (typeof normalized !== 'string' && typeof normalized !== 'number') return undefined
  const parsed = Number(normalized)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

export const buildLearningRoute = (courseId: number, queryInput: LearningQueryInput = {}) => {
  const query: LocationQueryRaw = {}
  if (isPositiveInteger(queryInput.worldId)) query.worldId = String(queryInput.worldId)
  if (isPositiveInteger(queryInput.sessionId)) query.sessionId = String(queryInput.sessionId)

  return {
    path: `/learning/${courseId}`,
    query,
  }
}
