import client from '@/shared/api/client'

export interface LearningPlanDraft {
  id: number
  user_id: number
  material_ids: number[]
  goal: string
  course_form?: Record<string, any> | null
  material_analysis?: Record<string, any> | null
  knowledge_blueprint?: Record<string, any> | null
  course_blueprint?: Record<string, any> | null
  world_plan?: Record<string, any> | null
  character_plan?: Record<string, any> | null
  stage: string
  committed_world_id?: number | null
  committed_course_id?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface LearningPlanCommitResponse {
  draft_id: number
  world_id: number
  course_id: number
  lesson_count: number
  linked_textbook_count: number
}

export const learningPlanApi = {
  createDraft: (payload: { material_ids: number[]; goal: string; course_form?: Record<string, any> | null }) =>
    client.post('/learning-plans/drafts', payload).then(res => res.data as LearningPlanDraft),
  getDraft: (draftId: number) =>
    client.get(`/learning-plans/drafts/${draftId}`).then(res => res.data as LearningPlanDraft),
  updateDraft: (draftId: number, payload: { goal?: string; course_form?: Record<string, any> | null; material_ids?: number[] }) =>
    client.put(`/learning-plans/drafts/${draftId}`, payload).then(res => res.data as LearningPlanDraft),
  regenerateDraft: (draftId: number) =>
    client.post(`/learning-plans/drafts/${draftId}/regenerate`).then(res => res.data as LearningPlanDraft),
  commitDraft: (draftId: number, payload: {
    course_name?: string | null
    description?: string | null
    target_level?: string | null
    world_name?: string | null
    world_description?: string | null
    commit_world?: boolean
  }) =>
    client.post(`/learning-plans/drafts/${draftId}/commit`, payload).then(res => res.data as LearningPlanCommitResponse),
  updateWorldLayer: (draftId: number, payload: Record<string, any>) =>
    client.put(`/learning-plans/drafts/${draftId}/world`, payload).then(res => res.data as LearningPlanDraft),
}
