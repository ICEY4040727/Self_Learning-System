/**
 * 课程学科预设常量
 * 用于 CreateCourseModal 4步表单
 */

// ==================== 学科预设 ====================
export interface CourseDomain {
  key: string
  name: string
  icon: string
  color: string
  description: string
}

export const COURSE_DOMAINS: CourseDomain[] = [
  {
    key: 'math',
    name: '数学',
    icon: '📐',
    color: '#3b82f6',
    description: '代数/几何/微积分',
  },
  {
    key: 'language',
    name: '语言',
    icon: '🗣️',
    color: '#8b5cf6',
    description: '英语/日语/古文',
  },
  {
    key: 'programming',
    name: '编程',
    icon: '💻',
    color: '#10b981',
    description: 'Python/JavaScript/算法',
  },
  {
    key: 'art',
    name: '艺术',
    icon: '🎨',
    color: '#ec4899',
    description: '绘画/音乐/设计',
  },
  {
    key: 'history',
    name: '历史',
    icon: '📜',
    color: '#f59e0b',
    description: '中外历史/文化',
  },
  {
    key: 'science',
    name: '科学',
    icon: '🔬',
    color: '#06b6d4',
    description: '物理/化学/生物',
  },
  {
    key: 'philosophy',
    name: '哲学',
    icon: '🤔',
    color: '#6366f1',
    description: '思想/伦理/逻辑',
  },
  {
    key: 'custom',
    name: '自定义',
    icon: '✨',
    color: '#6b7280',
    description: '自由设定',
  },
]

// ==================== 水平标签 ====================
export interface LevelOption {
  key: string
  label: string
  description: string
}

export const CURRENT_LEVELS: LevelOption[] = [
  { key: 'none', label: '完全陌生', description: '从未接触过' },
  { key: 'heard', label: '听说过', description: '知道基本概念' },
  { key: 'tried', label: '用过一点', description: '有过实践经历' },
  { key: 'basic', label: '已有基础', description: '掌握基础知识' },
]

export const TARGET_LEVELS: LevelOption[] = [
  { key: 'understand', label: '看懂入门', description: '能理解基本内容' },
  { key: 'applier', label: '能独立应用', description: '可独立解决问题' },
  { key: 'teacher', label: '能教别人', description: '深入理解可传授' },
  { key: 'expert', label: '达到专业水准', description: '接近专家水平' },
]

// ==================== 学习动机 ====================
export interface MotivationOption {
  key: string
  label: string
  icon: string
}

export const MOTIVATIONS: MotivationOption[] = [
  { key: 'interest', label: '出于兴趣', icon: '💡' },
  { key: 'exam', label: '考试所需', icon: '📝' },
  { key: 'work', label: '工作所需', icon: '💼' },
  { key: 'problem', label: '解决问题', icon: '🎯' },
  { key: 'companion', label: '陪伴学习', icon: '👨‍👩‍👧' },
]

// ==================== 学习节奏 ====================
export interface PaceOption {
  key: string
  label: string
  description: string
}

export const PACES: PaceOption[] = [
  { key: 'chill', label: '佛系', description: '轻松自在' },
  { key: 'normal', label: '正常', description: '稳步推进' },
  { key: 'sprint', label: '冲刺', description: '高强度学习' },
]

// ==================== 每周时长预设 ====================
export const WEEKLY_MINUTES_OPTIONS = [30, 90, 180]

// ==================== 辅助函数 ====================
export function getDomainByKey(key: string): CourseDomain | undefined {
  return COURSE_DOMAINS.find((d) => d.key === key)
}

export function getLevelLabel(key: string, isTarget: boolean = false): string {
  const list = isTarget ? TARGET_LEVELS : CURRENT_LEVELS
  return list.find((l) => l.key === key)?.label || key
}

export function buildMetaPayload(form: {
  domain: string
  currentLevel: string
  targetLevel: string
  motivation: string
  motivationDetail?: string
  pace: string
  weeklyMinutes?: number
  sageIds?: number[]
}): Record<string, any> {
  const meta: Record<string, any> = {}
  
  if (form.domain) meta.domain = form.domain
  if (form.currentLevel) meta.current_level = form.currentLevel
  if (form.targetLevel) meta.target_level = form.targetLevel
  if (form.motivation) meta.motivation = form.motivation
  if (form.motivationDetail) meta.motivation_detail = form.motivationDetail
  if (form.pace) meta.pace = form.pace
  if (form.weeklyMinutes) meta.weekly_minutes = form.weeklyMinutes
  if (form.sageIds?.length) meta.sage_ids = form.sageIds
  
  return meta
}
