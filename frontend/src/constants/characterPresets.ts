/**
 * 角色预设常量
 * 用于 SageCreateFlow 和 TravelerCreateFlow
 */

// ==================== Sage 模板 ====================
export interface SageTemplate {
  key: string
  name: string
  nameEn: string
  desc: string
  icon: string
  color: string
  greeting: string
}

export const SAGE_TEMPLATES: SageTemplate[] = [
  {
    key: 'socratic',
    name: '苏格拉底型',
    nameEn: 'Socratic',
    desc: '擅长通过反问引导思考，层层递进，适合哲学讨论',
    icon: '🤔',
    color: '#f59e0b',
    greeting: '我知道我一无所知。让我们一起来探索真理吧。',
  },
  {
    key: 'einstein',
    name: '爱因斯坦型',
    nameEn: 'Einstein',
    desc: '鼓励大胆假设和实验，适合科学探索',
    icon: '💡',
    color: '#8b5cf6',
    greeting: '想象力比知识更重要。你准备好提出大胆的想法了吗？',
  },
  {
    key: 'aristotle',
    name: '亚里士多德型',
    nameEn: 'Aristotle',
    desc: '百科全书式讲解，体系完整，适合系统学习',
    icon: '📚',
    color: '#10b981',
    greeting: '让我们从基础开始，构建完整的知识体系。',
  },
  {
    key: 'sunzi',
    name: '孙子型',
    nameEn: 'Sun Tzu',
    desc: '策略性思考，引导举一反三，适合方法论学习',
    icon: '⚔️',
    color: '#dc2626',
    greeting: '知己知彼，百战不殆。让我们先理清思路。',
  },
  {
    key: 'yoda',
    name: '尤达型',
    nameEn: 'Yoda',
    desc: '神秘导师风格，言语简短但充满智慧',
    icon: '🌙',
    color: '#06b6d4',
    greeting: '尝试，不尝试。不存在。只有doing。',
  },
  {
    key: 'free',
    name: '自由奔放型',
    nameEn: 'Free Spirit',
    desc: '不受束缚，天马行空，适合创意发散',
    icon: '🦋',
    color: '#ec4899',
    greeting: '规则是用来打破的！让我们一起跳出思维定式。',
  },
]

// ==================== Traveler 预设头像 ====================
export interface AvatarPreset {
  key: string
  emoji: string
  label: string
}

export const TRAVELER_AVATARS: AvatarPreset[] = [
  { key: 'traveler1', emoji: '🧭', label: '探索者' },
  { key: 'traveler2', emoji: '🧙', label: '法师' },
  { key: 'traveler3', emoji: '🧝', label: '精灵' },
  { key: 'traveler4', emoji: '🦸', label: '英雄' },
  { key: 'traveler5', emoji: '🧑‍🎓', label: '学者' },
  { key: 'traveler6', emoji: '🧑‍💻', label: '程序员' },
  { key: 'traveler7', emoji: '🎨', label: '艺术家' },
  { key: 'traveler8', emoji: '🔮', label: '占卜师' },
  { key: 'traveler9', emoji: '✨', label: '冒险家' },
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
  { expression: 'default', emoji: '😊', desc: '默认' },
  { expression: 'smile', emoji: '😄', desc: '微笑' },
  { expression: 'thinking', emoji: '🤔', desc: '思考' },
  { expression: 'serious', emoji: '😐', desc: '严肃' },
  { expression: 'encourage', emoji: '💪', desc: '鼓励' },
]

// ==================== 性格滑块配置 ====================
export interface TraitSlider {
  key: string
  label: string
  leftLabel: string
  leftExample: string
  rightLabel: string
  rightExample: string
  defaultValue: number
}

export const TRAIT_SLIDERS: TraitSlider[] = [
  {
    key: 'strictness',
    label: '严厉度',
    leftLabel: '温和',
    leftExample: '答错也鼓励你慢慢来',
    rightLabel: '严厉',
    rightExample: '答错会直接指出并要求重做',
    defaultValue: 3,
  },
  {
    key: 'pace',
    label: '节奏',
    leftLabel: '慢工细活',
    leftExample: '反复确认，确保理解',
    rightLabel: '快速推进',
    rightExample: '信息密集，不拖沓',
    defaultValue: 5,
  },
  {
    key: 'questioning',
    label: '提问倾向',
    leftLabel: '苏格拉底式',
    leftExample: '通过提问引导你思考',
    rightLabel: '直接讲解',
    rightExample: '直接讲解+举例说明',
    defaultValue: 7,
  },
  {
    key: 'warmth',
    label: '情感温度',
    leftLabel: '克制冷静',
    leftExample: '客观理性，不带情绪',
    rightLabel: '热情外放',
    rightExample: '充满热情，积极鼓励',
    defaultValue: 6,
  },
  {
    key: 'humor',
    label: '幽默感',
    leftLabel: '一本正经',
    leftExample: '严肃认真，专注学习',
    rightLabel: '段子手',
    rightExample: '妙语连珠，轻松愉快',
    defaultValue: 4,
  },
]

// ==================== 说话风格标签 ====================
export const SPEECH_STYLES = [
  '文白夹杂', '口语化', '学术腔', '用比喻',
  '爱讲故事', '偶尔吐槽', '简洁干练', '详细解释',
]
