// ============================================================
//  Shared Types — mirrors backend contract (UI迁移书.md §2)
//  Adapted per: vue3_migration_contract_adaptation.md
// ============================================================

export type CharacterType   = 'sage' | 'traveler'
export type Expression      = 'default' | 'happy' | 'thinking' | 'concerned' | 'surprised'
export type RelationshipStage = 'stranger' | 'acquaintance' | 'friend' | 'mentor' | 'partner'
export type DialogMode      = 'speaking' | 'input' | 'choices' | 'waiting'
export type ConceptType     = 'knowledge' | 'misconception' | 'skill' | 'episode'
export type BloomLevel      = 'remember' | 'understand' | 'apply' | 'analyze' | 'evaluate' | 'create'

// §2 adaptation #2/#3: only 'local' (not 'ollama') matches backend adapter key
// 后端支持的 provider: claude, openai, deepseek, local (对应 ollama)
export type LLMProvider = 'claude' | 'openai' | 'deepseek' | 'local'

// ---- Auth ----
export interface User {
  id: number
  username: string
  role: string
}

// ---- Character / World ----
export interface Sprites {
  default?: string
  happy?: string
  thinking?: string
  concerned?: string
  surprised?: string
}

export interface Character {
  id: number
  name: string
  type: CharacterType
  avatar?: string | null
  personality?: string
  background?: string
  speech_style?: string
  tags?: string[]
  sprites?: Sprites
  // UI-side display helpers (from world-character binding)
  color?: string
  accentColor?: string
  symbol?: string
  title?: string
  level?: number
  experience_points?: number
}

// Character 创建表单数据
export interface CharacterFormData {
  name: string
  title?: string
  type: 'sage' | 'traveler'
  template_name: string  // 人格模板名称
  tags: string[]         // 特质标签
  background?: string    // 背景故事
  personality?: string   // 性格特点
  speech_style?: string  // 说话风格
  avatar?: string
}

// Character API 请求类型
export interface CharacterCreateRequest {
  name: string
  type: 'sage' | 'traveler'
  template_name?: string
  avatar?: string
  personality?: string
  background?: string
  speech_style?: string
  tags?: string[]
  title?: string
}

export interface WorldCharacter {
  id: number
  world_id: number
  character_id: number
  role: 'sage' | 'traveler'
  is_primary: boolean
  character_name: string
  character?: Character
}

export interface Course {
  id: number
  world_id: number
  name: string
  description: string
  target_level: string
  icon?: string
  progress?: number
  next_review?: string
}

export interface World {
  id: number
  name: string
  description: string
  scenes?: {
    background?: string
    menu_background?: string
  }
  characters?: WorldCharacter[]
  courses?: Course[]
}

// ---- Checkpoint / Timeline ----
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

// §2 adaptation #5: history endpoint returns only these 4 fields
export interface HistoryMessage {
  id: number
  sender_type: 'assistant' | 'user' | 'system'
  content: string
  timestamp: string
}

// Frontend-extended message (adds UI-only fields after receiving from chat endpoint)
export interface Message extends HistoryMessage {
  emotion?: string           // extracted from ChatResponse.emotion dict
  expression_hint?: Expression
}

// §2 adaptation #3: request body field is `message`, not `content`
export interface ChatRequest {
  message: string            // min_length=1, max_length=5000
}

// §2 adaptation #3:
//   - `type` can be 'text' | 'tool_request' | 'choice'
//   - `emotion` is a dict (object), NOT a plain string
//   - `choices` is optional (null when type != 'choice')
export interface ChatResponse {
  type: 'text' | 'tool_request' | 'choice'
  reply: string
  choices?: string[] | null
  emotion?: Record<string, unknown> | null   // e.g. {emotion_type:'curiosity', valence:0.7, …}
  relationship_stage?: RelationshipStage | null
  relationship?: { dimensions: Record<string, number>; stage: RelationshipStage } | null
  relationship_events?: Array<{
    type: string
    new_stage?: RelationshipStage
    special_dialogue?: string
  }> | null
  expression_hint?: Expression | null
  memory_extracted_count?: number   // 本次会话提取的记忆数量 (#192)
}

// §2 adaptation #4: start endpoint returns teacher_persona as string (name), not object
export interface StartLearningResponse {
  session_id: number
  teacher_persona: string | null        // just the persona name string
  course: string                        // course name string
  relationship_stage: RelationshipStage
  relationship: { dimensions: Record<string, number>; stage: RelationshipStage }
  greeting: string
  scenes: { background?: string; menu_background?: string }
  sage_sprites: Sprites | null
  traveler_sprites: Sprites | null
  character_sprites: Sprites | null     // legacy alias for sage_sprites
}

// §2 adaptation #5: branch returns session_id + course_id + world_id
export interface BranchResponse {
  session_id: number
  course_id: number
  world_id: number
  parent_checkpoint_id: number | null
  branch_name: string | null
}

// §2 adaptation #6: diary create requires course_id; date is datetime string
export interface DiaryCreatePayload {
  course_id: number                     // required — backend validates ownership
  date: string                          // ISO 8601 datetime string
  content: string
  reflection?: string
}

// ---- Knowledge Graph ----
export interface KnowledgeNode {
  id: string
  name: string
  type: ConceptType
  mastery: number
  status: string
  x?: number
  y?: number
}

export interface KnowledgeEdge {
  source: string
  target: string
  type: string
}

export interface KnowledgeGraph {
  nodes: KnowledgeNode[]
  edges: KnowledgeEdge[]
}

// ---- Archive ----
export interface DiaryEntry {
  id: number
  course_id: number
  date: string
  content: string
  reflection?: string
}

export interface ProgressItem {
  id: number
  topic: string
  mastery_level: number
  next_review: string
}

export interface EmotionDataPoint {
  index: number
  timestamp: string
  emotion_type: string
  valence: number
  arousal: number
  confidence: number
}

// §2 adaptation #8: sprite upload — ALLOWED_EXPRESSIONS & MIME
export const ALLOWED_SPRITE_STEMS = ['default', 'happy', 'thinking', 'concerned'] as const
export const ALLOWED_SPRITE_MIMES = ['image/png', 'image/jpeg', 'image/webp'] as const
export const MAX_SPRITE_SIZE_BYTES = 2 * 1024 * 1024  // 2 MB

// ---- UserProfile (学习报告) ----

// 元认知维度数值 (0-1)
export type MetacognitionDimension = number

export interface MetacognitionTrend {
  current: 'weak' | 'moderate' | 'strong'
  trend: 'improving' | 'stable' | 'unknown'
  evidence_count: number
  latest_evidence?: string
}

export interface PreferenceStability {
  stable: boolean
  consistency?: number  // 布尔值偏好 (0-1)
  most_common?: string  // 枚举值偏好
  display: string
  status?: 'insufficient_data'  // 数据不足时
}

export interface LearningStats {
  total_concepts_learned: number
  total_sessions: number
  average_mastery: number  // 0-1
  worlds_explored: number
}

export interface UserProfile {
  user_id: number
  computed_at: string
  metacognition_trend: Record<string, MetacognitionDimension>
  preference_stability: Record<string, PreferenceStability>
  learning_stats: LearningStats
}

// MSKT 维度中文映射
export const MSKT_LABELS: Record<string, string> = {
  planning: '规划',
  monitoring: '监控',
  regulating: '调节',
  reflecting: '反思',
}

// 偏好维度中文映射
export const PREFERENCE_LABELS: Record<string, string> = {
  visual_examples: '视觉化学习',
  analogy_based: '类比学习',
  step_by_step: '步骤优先',
  pace: '学习节奏',
}

// MSKT 等级颜色
export const MSKT_VALUE_COLORS: Record<string, string> = {
  weak: '#ef4444',     // 红色
  moderate: '#fbbf24', // 黄色
  strong: '#4ade80',  // 绿色
}

// 趋势方向颜色
export const TREND_COLORS: Record<string, string> = {
  improving: '#4ade80',  // 绿色
  stable: '#fbbf24',    // 黄色
  unknown: '#94a3b8',   // 灰色
}

// ---- UI Constants ----
export const STAGE_COLORS: Record<RelationshipStage, { primary: string; glow: string }> = {
  stranger:     { primary: '#94a3b8', glow: 'rgba(148,163,184,0.3)' },
  acquaintance: { primary: '#60a5fa', glow: 'rgba(96,165,250,0.3)'  },
  friend:       { primary: '#ffd700', glow: 'rgba(255,215,0,0.35)'  },
  mentor:       { primary: '#a78bfa', glow: 'rgba(167,139,250,0.35)'},
  partner:      { primary: '#4adf6a', glow: 'rgba(74,223,106,0.35)' },
}

export const EMOTION_COLORS: Record<string, string> = {
  '好奇': '#60a5fa',
  '兴奋': '#ffd700',
  '困惑': '#f97316',
  '满足': '#4adf6a',
  '沮丧': '#ef4444',
  '期待': '#a78bfa',
  '思考': '#94a3b8',
  '中性': '#aaaaaa',
  '……': '#aaaaaa',
}

// §2 adaptation #3: map backend emotion_type keys → Chinese display labels
export const EMOTION_TYPE_ZH: Record<string, string> = {
  curiosity:    '好奇',
  excitement:   '兴奋',
  confusion:    '困惑',
  satisfaction: '满足',
  frustration:  '沮丧',
  anticipation: '期待',
  thinking:     '思考',
  neutral:      '中性',
  happy:        '兴奋',
  sad:          '沮丧',
}

export const EXPRESSION_SYMBOLS: Record<Expression, string> = {
  default:   '◡‿◡',
  happy:     '＾‿＾',
  thinking:  '（－_－）',
  concerned: '(ó_ò)',
  surprised: '( ꒪⌓꒪ )',
}

export const EXPRESSION_COLORS: Record<Expression, string> = {
  default:   '#94a3b8',
  happy:     '#4ade80',
  thinking:  '#60a5fa',
  concerned: '#f97316',
  surprised: '#a78bfa',
}

// =============================================================================
// Report Types - 学习报告相关类型
// =============================================================================

// 知识掌握度趋势
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

// 关系进化历程
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

// 世界对比
export interface WorldComparisonItem {
  world_id: number
  world_name: string
  total_sessions: number
  total_concepts: number
  average_mastery: number
  relationship_stage: RelationshipStage
  last_active: string | null
}

// 里程碑事件
export type MilestoneEventType = 'relationship_upgrade' | 'concept_mastered' | 'session_completed'

export interface MilestoneEvent {
  id: string
  type: MilestoneEventType
  title: string
  description: string
  timestamp: string | null
  world_id: number | null
}

// 单世界掌握度趋势
export interface WorldMasteryTrendItem {
  date: string
  average_mastery: number
  concepts_learned: number
}

// 阶段升级类型映射
export const MILESTONE_TYPE_LABELS: Record<MilestoneEventType, string> = {
  relationship_upgrade: '关系进阶',
  concept_mastered: '概念掌握',
  session_completed: '会话完成',
}

export const MILESTONE_TYPE_ICONS: Record<MilestoneEventType, string> = {
  relationship_upgrade: '🎭',
  concept_mastered: '📚',
  session_completed: '✅',
}

