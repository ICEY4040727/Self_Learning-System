// UI Constants extracted from types/index.ts
// 建议：新代码优先从 @/constants/ui 导入，types/index.ts 保留 re-export 兼容
import type { RelationshipStage, Expression } from '@/types'

// Sprite/Image upload constants
export const ALLOWED_SPRITE_STEMS = ['default', 'happy', 'thinking', 'concerned'] as const
export const ALLOWED_SPRITE_MIMES = ['image/png', 'image/jpeg', 'image/webp'] as const
export const MAX_SPRITE_SIZE_BYTES = 2 * 1024 * 1024  // 2 MB

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

// Relationship stage colors
export const STAGE_COLORS: Record<RelationshipStage, { primary: string; glow: string }> = {
  stranger:     { primary: '#94a3b8', glow: 'rgba(148,163,184,0.3)' },
  acquaintance: { primary: '#60a5fa', glow: 'rgba(96,165,250,0.3)'  },
  friend:       { primary: '#ffd700', glow: 'rgba(255,215,0,0.35)'  },
  mentor:       { primary: '#a78bfa', glow: 'rgba(167,139,250,0.35)'},
  partner:      { primary: '#4adf6a', glow: 'rgba(74,223,106,0.35)' },
}

// Emotion colors (Chinese keys)
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

// Expression symbols
export const EXPRESSION_SYMBOLS: Record<Expression, string> = {
  default:   '◡‿◡',
  happy:     '＾‿＾',
  thinking:  '（－_－）',
  concerned: '(ó_ò)',
  surprised: '( ꒪⌓꒪ )',
}

// Expression colors
export const EXPRESSION_COLORS: Record<Expression, string> = {
  default:   '#94a3b8',
  happy:     '#4ade80',
  thinking:  '#60a5fa',
  concerned: '#f97316',
  surprised: '#a78bfa',
}
