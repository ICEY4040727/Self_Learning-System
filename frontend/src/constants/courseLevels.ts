// Course levels and related constants

export const CURRENT_LEVEL_OPTIONS = [
  { value: 'none', label: '完全陌生', order: 0 },
  { value: 'heard', label: '听说过', order: 1 },
  { value: 'tried', label: '用过一点', order: 2 },
  { value: 'basic', label: '已有基础', order: 3 },
]

export const TARGET_LEVEL_OPTIONS = [
  { value: 'understand', label: '看懂入门', order: 0 },
  { value: 'applier', label: '能独立应用', order: 1 },
  { value: 'teacher', label: '能教别人', order: 2 },
  { value: 'expert', label: '达到专业水准', order: 3 },
]

export const RELATIONSHIP_STAGE_LABELS: Record<string, string> = {
  stranger: '陌生人',
  acquaintance: '相识',
  friend: '朋友',
  mentor: '导师',
  partner: '伙伴',
}

export const RELATIONSHIP_STAGE_ICONS: Record<string, string> = {
  stranger: '👤',
  acquaintance: '🧑‍🤝‍🧑',
  friend: '👥',
  mentor: '🎓',
  partner: '🤝',
}

export const MOTIVATION_LABELS: Record<string, string> = {
  interest: '兴趣探索',
  exam: '考试备考',
  work: '工作所需',
  problem_solving: '解决问题',
  companion: '陪伴学习',
}

export const DOMAIN_ICONS: Record<string, string> = {
  programming: '💻',
  language: '🗣️',
  mathematics: '📐',
  science: '🔬',
  history: '📜',
  art: '🎨',
  music: '🎵',
  business: '💼',
  default: '📚',
}

export function getLevelIndex(level: string, isTarget: boolean): number {
  const options = isTarget ? TARGET_LEVEL_OPTIONS : CURRENT_LEVEL_OPTIONS
  const found = options.find(o => o.value === level)
  return found ? found.order : 0
}

export function getLevelLabel(level: string, isTarget: boolean): string {
  const options = isTarget ? TARGET_LEVEL_OPTIONS : CURRENT_LEVEL_OPTIONS
  const found = options.find(o => o.value === level)
  return found ? found.label : level
}
