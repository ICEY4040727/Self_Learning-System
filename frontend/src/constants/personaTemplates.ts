/**
 * Persona 角色模板常量
 * 用于 CreatePersonaModal 3步表单 + LLM生成
 */

// ==================== 角色模板预设 ====================
export interface PersonaTemplate {
  key: string
  name: string
  icon: string
  description: string
  traits: string[]
}

export const PERSONA_TEMPLATES: PersonaTemplate[] = [
  {
    key: 'socrates',
    name: '苏格拉底型',
    icon: '🧘',
    description: '耐心追问，启发思考',
    traits: ['耐心', '追问型', '启发型'],
  },
  {
    key: 'einstein',
    name: '爱因斯坦型',
    icon: '💡',
    description: '鼓励探索，激发好奇',
    traits: ['鼓励型', '探索型', '启发型'],
  },
  {
    key: 'aristotle',
    name: '亚里士多德型',
    icon: '📚',
    description: '严谨体系，博学多才',
    traits: ['严谨', '体系化', '百科全书'],
  },
  {
    key: 'sunzi',
    name: '孙子型',
    icon: '⚔️',
    description: '策略引导，举一反三',
    traits: ['策略性', '举一反三', '引导型'],
  },
  {
    key: 'custom',
    name: '自定义',
    icon: '✨',
    description: '自由设定你的导师',
    traits: [],
  },
]

// ==================== 性格滑块配置 ====================
export interface TraitSlider {
  key: string
  name: string
  min: number
  max: number
  default: number
  minLabel: string
  maxLabel: string
}

export const TRAIT_SLIDERS: TraitSlider[] = [
  { key: 'strictness', name: '严格程度', min: 1, max: 10, default: 5, minLabel: '温和', maxLabel: '严格' },
  { key: 'pace', name: '教学节奏', min: 1, max: 10, default: 5, minLabel: '缓慢', maxLabel: '紧凑' },
  { key: 'questioning', name: '提问频率', min: 1, max: 10, default: 5, minLabel: '讲解为主', maxLabel: '提问为主' },
  { key: 'warmth', name: '温暖程度', min: 1, max: 10, default: 6, minLabel: '冷静', maxLabel: '热情' },
  { key: 'humor', name: '幽默程度', min: 1, max: 10, default: 4, minLabel: '严肃', maxLabel: '幽默' },
]

// ==================== 头像预设 ====================
export const AVATAR_OPTIONS = ['☉', '☽', '★', '✧', '❋', '⬡', '⬢', '◈', '◉']

// ==================== 颜色预设 ====================
export const COLOR_OPTIONS = [
  '#ffd700', '#f59e0b', '#10b981', '#3b82f6',
  '#8b5cf6', '#ec4899', '#ef4444', '#06b6d4',
]

// ==================== 辅助函数 ====================
export function getTemplateByKey(key: string): PersonaTemplate | undefined {
  return PERSONA_TEMPLATES.find((t) => t.key === key)
}

export function buildTraitsPayload(sliders: Record<string, number>): Record<string, number> {
  return { ...sliders }
}

export function buildCharacterPayload(form: {
  name: string
  title: string
  avatar: string
  color: string
  templateKey: string
  description: string
  traits: Record<string, number>
}): Record<string, any> {
  const template = getTemplateByKey(form.templateKey)
  const tags = template?.traits || []
  
  return {
    name: form.name,
    type: 'sage',
    avatar: form.avatar,
    title: form.title,
    tags,
    template_name: form.templateKey,
    traits: form.traits,
    personality: form.description,
  }
}
