/**
 * 角色预设常量 — 唯一权威数据源
 *
 * SageCreateFlow / CreatePersonaModal / 未来所有角色创建流程
 * 均从此文件获取模板、滑块、颜色等预设数据。
 */

// ==================== Sage 模板 ====================
export interface SageTemplate {
  key: string          // 唯一标识，存入后端 template_name
  name: string         // 中文显示名
  nameEn: string       // 英文显示名
  desc: string         // 详细描述（5步流程用）
  shortDesc: string    // 简短描述（3步紧凑卡片用）
  icon: string         // emoji
  color: string        // 主题色 hex
  greeting: string     // 初次见面台词
  tags: string[]       // 性格标签（用于 payload 的 tags 字段）
}

export const SAGE_TEMPLATES: SageTemplate[] = [
  {
    key: 'socratic',
    name: '苏格拉底型',
    nameEn: 'Socratic',
    desc: '擅长通过反问引导思考，层层递进，适合哲学讨论',
    shortDesc: '耐心追问，启发思考',
    icon: '',
    color: '#f59e0b',
    greeting: '我知道我一无所知。让我们一起来探索真理吧。',
    tags: ['耐心', '追问型', '启发型'],
  },
  {
    key: 'einstein',
    name: '爱因斯坦型',
    nameEn: 'Einstein',
    desc: '鼓励大胆假设和实验，适合科学探索',
    shortDesc: '鼓励探索，激发好奇',
    icon: '',
    color: '#8b5cf6',
    greeting: '想象力比知识更重要。你准备好提出大胆的想法了吗？',
    tags: ['鼓励型', '探索型', '启发型'],
  },
  {
    key: 'aristotle',
    name: '亚里士多德型',
    nameEn: 'Aristotle',
    desc: '百科全书式讲解，体系完整，适合系统学习',
    shortDesc: '严谨体系，博学多才',
    icon: '',
    color: '#10b981',
    greeting: '让我们从基础开始，构建完整的知识体系。',
    tags: ['严谨', '体系化', '百科全书'],
  },
  {
    key: 'sunzi',
    name: '孙子型',
    nameEn: 'Sun Tzu',
    desc: '策略性思考，引导举一反三，适合方法论学习',
    shortDesc: '策略引导，举一反三',
    icon: '',
    color: '#dc2626',
    greeting: '知己知彼，百战不殆。让我们先理清思路。',
    tags: ['策略性', '举一反三', '引导型'],
  },
  {
    key: 'yoda',
    name: '尤达型',
    nameEn: 'Yoda',
    desc: '神秘导师风格，言语简短但充满智慧',
    shortDesc: '神秘导师，言简意深',
    icon: '',
    color: '#06b6d4',
    greeting: '尝试，不尝试。不存在。只有doing。',
    tags: ['神秘', '简洁', '智慧型'],
  },
  {
    key: 'free',
    name: '自由奔放型',
    nameEn: 'Free Spirit',
    desc: '不受束缚，天马行空，适合创意发散',
    shortDesc: '天马行空，创意发散',
    icon: '',
    color: '#ec4899',
    greeting: '规则是用来打破的！让我们一起跳出思维定式。',
    tags: ['自由', '创意', '发散型'],
  },
  {
    key: 'custom',
    name: '自定义',
    nameEn: 'Custom',
    desc: '从零开始，完全按你的想法塑造导师',
    shortDesc: '自由设定你的导师',
    icon: '*',
    color: '#ffd700',
    greeting: '你好，期待我们的学习之旅。',
    tags: [],
  },
]

// ==================== 降级用角色数据（API 失败时的 fallback） ====================
export interface FallbackCharacter {
  id: number
  name: string
  title: string
  type: 'sage' | 'traveler'
  color: string
}

export const FALLBACK_CHARACTERS: FallbackCharacter[] = [
  { id: 1, name: '苏格拉底', title: '哲学之父', type: 'sage', color: 'rgba(245, 158, 11, 0.35)' },
  { id: 2, name: '柏拉图', title: '理念论者', type: 'sage', color: 'rgba(139, 92, 246, 0.35)' },
  { id: 3, name: '亚里士多德', title: '百科全书', type: 'sage', color: 'rgba(16, 185, 129, 0.35)' },
  { id: 4, name: '孙子', title: '兵圣', type: 'sage', color: 'rgba(220, 38, 38, 0.35)' },
  { id: 101, name: '旅者', title: '求知者', type: 'traveler', color: 'rgba(59, 130, 246, 0.35)' },
  { id: 102, name: '行者', title: '探索者', type: 'traveler', color: 'rgba(6, 182, 212, 0.35)' },
]

// ==================== Traveler 预设头像 ====================
export interface AvatarPreset {
  key: string
  emoji: string
  label: string
}

export const TRAVELER_AVATARS: AvatarPreset[] = [
  { key: 'traveler1', emoji: '', label: '探索者' },
  { key: 'traveler2', emoji: '', label: '法师' },
  { key: 'traveler3', emoji: '', label: '精灵' },
  { key: 'traveler4', emoji: '', label: '英雄' },
  { key: 'traveler5', emoji: '', label: '学者' },
  { key: 'traveler6', emoji: '', label: '程序员' },
  { key: 'traveler7', emoji: '', label: '艺术家' },
  { key: 'traveler8', emoji: '', label: '占卜师' },
  { key: 'traveler9', emoji: '*', label: '冒险家' },
]

// ==================== Traveler 性格标签 ====================
export const TRAVELER_TRAITS = [
  '好奇', '谨慎', '急性子', '慢热', '视觉型', '听觉型',
  '完美主义', '半途而废星人', '逻辑思维', '发散思维',
  '专注认真', '天马行空', '脚踏实地', '追求效率',
]

// ==================== 颜色主题 ====================
export const CHARACTER_COLORS = [
  { key: 'gold', color: 'rgba(245, 158, 11, 0.6)', name: '金色' },
  { key: 'purple', color: 'rgba(139, 92, 246, 0.6)', name: '紫色' },
  { key: 'green', color: 'rgba(16, 185, 129, 0.6)', name: '绿色' },
  { key: 'red', color: 'rgba(220, 38, 38, 0.6)', name: '红色' },
  { key: 'blue', color: 'rgba(59, 130, 246, 0.6)', name: '蓝色' },
  { key: 'cyan', color: 'rgba(6, 182, 212, 0.6)', name: '青色' },
]

// ==================== 表情/立绘 Sprites ====================
export interface SpriteConfig {
  expression: string
  emoji: string
  desc: string
}

export const DEFAULT_SPRITES: SpriteConfig[] = [
  { expression: 'default', emoji: '', desc: '默认' },
  { expression: 'smile', emoji: '', desc: '微笑' },
  { expression: 'thinking', emoji: '', desc: '思考' },
  { expression: 'serious', emoji: '', desc: '严肃' },
  { expression: 'encourage', emoji: '', desc: '鼓励' },
]

// ==================== 性格滑块配置 ====================
export interface TraitSlider {
  key: string
  label: string         // 显示名称
  min: number           // 最小值
  max: number           // 最大值
  defaultValue: number  // 默认值
  leftLabel: string     // 左端标签（简洁版）
  leftExample: string   // 左端示例（详细版）
  rightLabel: string    // 右端标签（简洁版）
  rightExample: string  // 右端示例（详细版）
}

export const TRAIT_SLIDERS: TraitSlider[] = [
  {
    key: 'strictness',
    label: '严厉度',
    min: 0, max: 10, defaultValue: 3,
    leftLabel: '温和',
    leftExample: '答错也鼓励你慢慢来',
    rightLabel: '严厉',
    rightExample: '答错会直接指出并要求重做',
  },
  {
    key: 'pace',
    label: '节奏',
    min: 0, max: 10, defaultValue: 5,
    leftLabel: '慢工细活',
    leftExample: '反复确认，确保理解',
    rightLabel: '快速推进',
    rightExample: '信息密集，不拖沓',
  },
  {
    key: 'questioning',
    label: '提问倾向',
    min: 0, max: 10, defaultValue: 7,
    leftLabel: '苏格拉底式',
    leftExample: '通过提问引导你思考',
    rightLabel: '直接讲解',
    rightExample: '直接讲解+举例说明',
  },
  {
    key: 'warmth',
    label: '情感温度',
    min: 0, max: 10, defaultValue: 6,
    leftLabel: '克制冷静',
    leftExample: '客观理性，不带情绪',
    rightLabel: '热情外放',
    rightExample: '充满热情，积极鼓励',
  },
  {
    key: 'humor',
    label: '幽默感',
    min: 0, max: 10, defaultValue: 4,
    leftLabel: '一本正经',
    leftExample: '严肃认真，专注学习',
    rightLabel: '段子手',
    rightExample: '妙语连珠，轻松愉快',
  },
]

// ==================== 说话风格标签 ====================
export const SPEECH_STYLES = [
  '文白夹杂', '口语化', '学术腔', '用比喻',
  '爱讲故事', '偶尔吐槽', '简洁干练', '详细解释',
]

// ==================== 头像预设（紧凑创建流程用） ====================
export const AVATAR_OPTIONS = ['', '', '', '', '', '⬡', '⬢', '◈', '◉']

// ==================== 颜色预设（紧凑创建流程用） ====================
export const COLOR_OPTIONS = [
  '#ffd700', '#f59e0b', '#10b981', '#3b82f6',
  '#8b5cf6', '#ec4899', '#ef4444', '#06b6d4',
]

// ==================== 工具函数 ====================
export function getSageTemplate(key: string): SageTemplate | undefined {
  return SAGE_TEMPLATES.find(t => t.key === key)
}

export function buildSagePayload(form: {
  name: string
  title: string
  avatar: string
  color: string
  templateKey: string
  description: string
  traits: Record<string, number>
}): Record<string, any> {
  const template = getSageTemplate(form.templateKey)
  return {
    name: form.name,
    type: 'sage',
    avatar: form.avatar,
    title: form.title,
    tags: template?.tags || [],
    template_name: form.templateKey,
    traits: form.traits,
    personality: form.description,
  }
}
