// ============================================================
//  Shared Types — re-export hub
//  Domain types split into separate files for maintainability.
//  All existing `import from '@/types'` continue to work.
// ============================================================

// Common type aliases
export type {
  CharacterType,
  Expression,
  RelationshipStage,
  DialogMode,
  ConceptType,
  BloomLevel,
  LLMProvider,
} from './common'

export { EMOTION_TYPE_ZH } from './common'

// Auth
export type { User } from './auth'

// Character
export type {
  Sprites,
  Character,
  CharacterFormData,
  CharacterCreateRequest,
  WorldCharacter,
  WorldCharacterContextInput,
} from './character'

// World / Course
export type { World, Course } from './world'

// Learning / Chat / Session
export type {
  Checkpoint,
  Session,
  Timeline,
  HistoryMessage,
  Message,
  ChatRequest,
  ChatResponse,
  StartLearningResponse,
  BranchResponse,
  DiaryCreatePayload,
} from './learning'

// Knowledge Graph
export type {
  KnowledgeNode,
  KnowledgeEdge,
  KnowledgeGraph,
} from './knowledge'

// Archive
export type {
  DiaryEntry,
  ProgressItem,
  EmotionDataPoint,
} from './archive'

// Report / UserProfile
export type {
  MetacognitionDimension,
  MetacognitionTrend,
  PreferenceStability,
  LearningStats,
  UserProfile,
  MasteryTrendItem,
  MasteryTrendResponse,
  RelationshipEvent,
  RelationshipHistoryResponse,
  WorldComparisonItem,
  MilestoneEventType,
  MilestoneEvent,
  WorldMasteryTrendItem,
} from './report'
