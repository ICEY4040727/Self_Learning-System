// ---- Archive ----
export interface DiaryEntry {
  id: number
  course_id: number
  date: string
  content: string
  reflection?: string
}

export interface ProgressItem {
  id: number
  topic: string
  mastery_level: number
  next_review: string
}

export interface EmotionDataPoint {
  index: number
  timestamp: string
  emotion_type: string
  valence: number
  arousal: number
  confidence: number
}
