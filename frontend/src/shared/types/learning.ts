// ---- Learning / Chat / Session ----
import type { RelationshipStage, Expression } from './common'
import type { Sprites } from './character'

export interface Checkpoint {
  id: number
  world_id: number
  session_id: number
  save_name: string
  message_index: number
  created_at: string
}

export interface Session {
  id: number
  course_id: number
  parent_checkpoint_id: number | null
  branch_name: string | null
  started_at: string
  relationship_stage: RelationshipStage
}

export interface Timeline {
  sessions: Session[]
  checkpoints: Checkpoint[]
}

export interface HistoryMessage {
  id: number
  sender_type: 'assistant' | 'user' | 'system'
  content: string
  timestamp: string
}

export interface Message extends HistoryMessage {
  emotion?: string
  expression_hint?: Expression
}

export interface ChatRequest {
  message: string
}

export interface ChatResponse {
  type: 'text' | 'tool_request' | 'choice'
  reply: string
  choices?: string[] | null
  emotion?: Record<string, unknown> | null
  relationship_stage?: RelationshipStage | null
  relationship?: { dimensions: Record<string, number>; stage: RelationshipStage } | null
  relationship_events?: Array<{
    type: string
    new_stage?: RelationshipStage
    special_dialogue?: string
  }> | null
  expression_hint?: Expression | null
  memory_extracted_count?: number
  // Phase 3: 叙事事件 & 成就
  narrative_events?: Array<{
    event_type: string
    description: string
    scene?: string
  }> | null
  new_achievements?: Array<{
    id: string
    name: string
    description: string
    icon?: string
  }> | null
}

export interface StartLearningResponse {
  session_id: number
  is_new: boolean
  teacher_persona: string | null
  course: string
  relationship_stage: RelationshipStage
  relationship: { dimensions: Record<string, number>; stage: RelationshipStage }
  greeting: string
  background_picture?: string
  sage: {
    id: number | null
    name: string | null
    title: string | null
    symbol: string | null
    avatar: string | null
    color: string | null
    sprites: Sprites | null
  } | null
  sage_sprites: Sprites | null
  traveler_sprites: Sprites | null
  character_sprites: Sprites | null
}

export interface BranchResponse {
  session_id: number
  course_id: number
  world_id: number
  parent_checkpoint_id: number | null
  branch_name: string | null
}

export interface DiaryCreatePayload {
  course_id: number
  date: string
  content: string
  reflection?: string
}

