// ---- Shared Type Aliases ----
export type CharacterType     = 'sage' | 'traveler'
export type Expression        = 'default' | 'happy' | 'thinking' | 'concerned' | 'surprised'
export type RelationshipStage = 'stranger' | 'acquaintance' | 'friend' | 'mentor' | 'partner'
export type DialogMode        = 'speaking' | 'input' | 'choices' | 'waiting'
export type ConceptType       = 'knowledge' | 'misconception' | 'skill' | 'episode'
export type BloomLevel        = 'remember' | 'understand' | 'apply' | 'analyze' | 'evaluate' | 'create'
export type LLMProvider       = 'claude' | 'openai' | 'deepseek' | 'local'

/** Chinese labels for emotion types (from backend dynamic_analyzer) */
export const EMOTION_TYPE_ZH: Record<string, string> = {
  curiosity:    '好奇',
  confusion:    '困惑',
  frustration:  '挫败',
  excitement:   '兴奋',
  satisfaction: '满足',
  boredom:      '无聊',
  anxiety:      '焦虑',
  neutral:      '中性',
}
