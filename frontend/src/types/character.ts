// ---- Character ----
import type { CharacterType } from './common'

export interface Sprites {
  default?: string
  happy?: string
  thinking?: string
  concerned?: string
  surprised?: string
}

export interface Character {
  id: number
  name: string
  type: CharacterType
  avatar?: string | null
  personality?: string
  background?: string
  speech_style?: string
  tags?: string[]
  sprites?: Sprites
  color?: string
  accentColor?: string
  symbol?: string
  title?: string
  level?: number
  experience_points?: number
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
  avatar?: string
}

export interface CharacterCreateRequest {
  name: string
  type: 'sage' | 'traveler'
  template_name?: string
  avatar?: string
  personality?: string
  background?: string
  speech_style?: string
  tags?: string[]
  title?: string
}

export interface WorldCharacter {
  id: number
  world_id: number
  character_id: number
  role: 'sage' | 'traveler'
  is_primary: boolean
  character_name: string
  character?: Character
}
