// ---- Character ----
import type { CharacterType } from './common'

export interface CharacterLLMSettings {
  provider?: string
  model?: string
  base_url?: string
  temperature?: number
  max_tokens?: number
}

export interface Sprites {
  default?: string
  happy?: string
  thinking?: string
  concerned?: string
  surprised?: string
  color?: string
  accentColor?: string
}

export interface Character {
  id: number
  name: string
  type: CharacterType
  avatar?: string | null
  personality?: string
  background?: string
  speech_style?: string
  greeting?: string
  tags?: string[]
  sprites?: Sprites
  color?: string
  accentColor?: string
  symbol?: string
  title?: string
  level?: number
  experience_points?: number
  traits?: Record<string, number>
  template_name?: string
  system_prompt_template?: string
  is_active?: boolean
  llm_settings?: CharacterLLMSettings
}

export interface CharacterFormData {
  name: string
  title?: string
  type: 'sage' | 'traveler'
  template_name: string
  tags: string[]
  background?: string
  personality?: string
  speech_style?: string
  greeting?: string
  avatar?: string
  sprites?: Sprites
  traits?: Record<string, number>
  system_prompt_template?: string
  is_active?: boolean
  llm_settings?: CharacterLLMSettings
}

export interface CharacterCreateRequest {
  name: string
  type: 'sage' | 'traveler'
  template_name?: string
  avatar?: string
  personality?: string
  background?: string
  speech_style?: string
  greeting?: string
  tags?: string[]
  title?: string
  sprites?: Sprites
  traits?: Record<string, number>
  system_prompt_template?: string
  is_active?: boolean
  llm_settings?: CharacterLLMSettings
}

export interface WorldCharacter {
  id: number
  world_id: number
  character_id: number
  role: 'sage' | 'traveler'
  is_primary: boolean
  world_title?: string | null
  world_background?: string | null
  relationship_seed?: string | null
  world_greeting?: string | null
  character_name: string
  character?: Character
}

export interface WorldCharacterContextInput {
  world_title?: string | null
  world_background?: string | null
  relationship_seed?: string | null
  world_greeting?: string | null
}
