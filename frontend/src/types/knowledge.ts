// ---- Knowledge Graph ----
import type { ConceptType } from './common'

export interface KnowledgeNode {
  id: string
  name: string
  type: ConceptType
  mastery: number
  status: string
  x?: number
  y?: number
}

export interface KnowledgeEdge {
  source: string
  target: string
  type: string
}

export interface KnowledgeGraph {
  nodes: KnowledgeNode[]
  edges: KnowledgeEdge[]
}
