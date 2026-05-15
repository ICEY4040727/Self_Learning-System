// ---- World / Course ----
import type { WorldCharacter } from './character'

export interface Course {
  id: number
  world_id: number
  name: string
  description: string
  target_level: string
  icon?: string
  progress?: number
  next_review?: string
}

export interface World {
  id: number
  name: string
  description: string
  background_picture?: string
  scenes?: {
    background?: string
    background_picture?: string
    menu_background?: string
  }
  characters?: WorldCharacter[]
  courses?: Course[]
}
