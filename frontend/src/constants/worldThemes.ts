/**
 * 世界主题预设常量
 * 用于 CreateWorldModal 3步表单
 */

// ==================== 主题预设 ====================
export interface WorldTheme {
  key: string
  name: string
  nameEn: string
  description: string
  background: string
  themeColor: string
  icon: string
}

export const WORLD_THEMES: WorldTheme[] = [
  {
    key: 'academy',
    name: '学院',
    nameEn: 'Academy',
    description: '知识殿堂，智者云集',
    background: '/themes/academy.jpg',
    themeColor: '#f59e0b',
    icon: '🎓',
  },
  {
    key: 'library',
    name: '图书馆',
    nameEn: 'Library',
    description: '卷帙浩繁，静谧求知',
    background: '/themes/library.jpg',
    themeColor: '#8b5cf6',
    icon: '📚',
  },
  {
    key: 'lab',
    name: '实验室',
    nameEn: 'Laboratory',
    description: '探索未知，验证真理',
    background: '/themes/lab.jpg',
    themeColor: '#10b981',
    icon: '🔬',
  },
  {
    key: 'mountain',
    name: '山林书院',
    nameEn: 'Mountain Academy',
    description: '隐世修行，问道自然',
    background: '/themes/mountain.jpg',
    themeColor: '#06b6d4',
    icon: '⛰️',
  },
  {
    key: 'cyber',
    name: '赛博空间',
    nameEn: 'Cyberspace',
    description: '数字世界，代码织梦',
    background: '/themes/cyber.jpg',
    themeColor: '#ec4899',
    icon: '💻',
  },
  {
    key: 'blank',
    name: '空白画布',
    nameEn: 'Blank Canvas',
    description: '白纸一张，由你书写',
    background: '',
    themeColor: '#6b7280',
    icon: '✨',
  },
]

// ==================== 氛围标签 ====================
export interface MoodTag {
  key: string
  label: string
  icon: string
}

export const MOOD_TAGS: MoodTag[] = [
  { key: 'warm', label: '温暖', icon: '☀️' },
  { key: 'cold', label: '冷峻', icon: '❄️' },
  { key: 'mysterious', label: '神秘', icon: '🌙' },
  { key: 'healing', label: '治愈', icon: '🌿' },
  { key: 'serious', label: '严肃', icon: '📐' },
  { key: 'humorous', label: '幽默', icon: '😄' },
  { key: 'fantasy', label: '童话', icon: '🏰' },
  { key: 'cyberpunk', label: '赛博', icon: '🤖' },
]

// ==================== BGM 预设 ====================
export interface BgmPreset {
  key: string
  label: string
  icon: string
  description: string
}

export const BGM_PRESETS: BgmPreset[] = [
  { key: 'whitenoise', label: '自习室白噪', icon: '📖', description: '专注沉浸' },
  { key: 'rainy_piano', label: '雨夜钢琴', icon: '🌧️', description: '思绪流淌' },
  { key: 'morning_guitar', label: '晨光木吉他', icon: '🌅', description: '清新启程' },
  { key: 'silent', label: '静音', icon: '🤫', description: '安静思考' },
]

// ==================== 辅助函数 ====================
export function getThemeByKey(key: string): WorldTheme | undefined {
  return WORLD_THEMES.find((t) => t.key === key)
}

export function buildScenesPayload(
  themeKey: string,
  moodKeys: string[] = [],
  bgmKey: string = 'silent'
): Record<string, any> {
  const theme = getThemeByKey(themeKey)
  return {
    theme_preset: themeKey,
    background: theme?.background || '',
    theme_color: theme?.themeColor || '#6b7280',
    mood: moodKeys,
    bgm: bgmKey,
  }
}
