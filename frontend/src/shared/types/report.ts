// ---- Report / UserProfile ----
import type { RelationshipStage } from './common'

export type MetacognitionDimension = number

export interface MetacognitionTrend {
  current: 'weak' | 'moderate' | 'strong'
  trend: 'improving' | 'stable' | 'unknown'
  evidence_count: number
  latest_evidence?: string
}

export interface PreferenceStability {
  stable: boolean
  consistency?: number
  most_common?: string
  display: string
  status?: 'insufficient_data'
}

export interface LearningStats {
  total_concepts_learned: number
  total_sessions: number
  average_mastery: number
  worlds_explored: number
}

export interface UserProfile {
  user_id: number
  computed_at: string
  metacognition_trend: Record<string, MetacognitionDimension>
  preference_stability: Record<string, PreferenceStability>
  learning_stats: LearningStats
}

export interface MasteryTrendItem {
  concept_name: string
  mastery_level: number
  last_updated: string | null
  world_id: number
  world_name: string
}

export interface MasteryTrendResponse {
  trends: MasteryTrendItem[]
  average_mastery: number
  improved_count: number
  declined_count: number
}

export interface RelationshipEvent {
  id: string
  world_id: number
  world_name: string
  character_name: string
  previous_stage: RelationshipStage
  new_stage: RelationshipStage
  timestamp: string | null
  trigger_reason: string | null
}

export interface RelationshipHistoryResponse {
  events: RelationshipEvent[]
  current_stages: Record<number, RelationshipStage>
}

export interface WorldComparisonItem {
  world_id: number
  world_name: string
  total_sessions: number
  total_concepts: number
  average_mastery: number
  relationship_stage: RelationshipStage
  last_active: string | null
}

export type MilestoneEventType = 'relationship_upgrade' | 'concept_mastered' | 'session_completed'

export interface MilestoneEvent {
  id: string
  type: MilestoneEventType
  title: string
  description: string
  timestamp: string | null
  world_id: number | null
}

export interface WorldMasteryTrendItem {
  date: string
  average_mastery: number
  concepts_learned: number
}
