<template>
  <div class="knowledge-graph-panel">
    <div class="toolbar">
      <label>
        checkpoint_time
        <input v-model="checkpointInput" type="datetime-local" />
      </label>
      <button @click="fetchGraph" :disabled="loading">{{ loading ? '加载中...' : '刷新图谱' }}</button>
    </div>
    <div v-if="edgeTypes.length > 0" class="legend">
      <span v-for="type in edgeTypes" :key="type" class="legend-item">
        <span
          class="legend-line"
          :style="{
            borderTopColor: edgeStroke(type),
            borderTopStyle: edgeDash(type) === 'none' ? 'solid' : 'dashed',
            borderTopWidth: `${edgeWidth(type)}px`,
          }"
        ></span>
        {{ type }}
      </span>
    </div>

    <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
    <svg ref="svgRef" class="graph-svg"></svg>

    <div v-if="selectedNode" class="node-detail">
      <h4>{{ selectedNode.name || selectedNode.id }}</h4>
      <p>状态：{{ selectedNode.status }}</p>
      <p>掌握度：{{ Math.round((selectedNode.mastery || 0) * 100) }}%</p>
      <p>类型：{{ selectedNode.type || 'knowledge' }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import axios from 'axios'
import * as d3 from 'd3'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'

interface GraphNode {
  id: string
  name: string
  mastery: number
  status: string
  type: string
}

interface GraphEdge {
  source: string
  target: string
  type: string
}

interface GraphPayload {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const props = defineProps<{
  worldId: number
  sessionId?: number | null
}>()

const authStore = useAuthStore()
const svgRef = ref<SVGSVGElement | null>(null)
const graph = ref<GraphPayload>({ nodes: [], edges: [] })
const selectedNode = ref<GraphNode | null>(null)
const checkpointInput = ref('')
const loading = ref(false)
const errorMessage = ref('')

const statusColor = (status: string) => {
  if (status === 'mastered') return '#4adf6a'
  if (status === 'learning') return '#60a5fa'
  if (status === 'confused') return '#df4a4a'
  return '#888'
}

const edgeStroke = (type: string) => {
  if (type === 'prerequisite') return '#ffb347'
  if (type === 'causes') return '#ff7b7b'
  if (type === 'example_of') return '#7dc7ff'
  return '#9a9ad6'
}

const edgeWidth = (type: string) => {
  if (type === 'prerequisite') return 2
  if (type === 'causes') return 1.8
  return 1.2
}

const edgeDash = (type: string) => (type === 'example_of' ? '4,3' : 'none')

const edgeTypes = ref<string[]>([])

const toCheckpointIso = (): string | undefined => {
  if (!checkpointInput.value) return undefined
  const parsed = new Date(checkpointInput.value)
  if (Number.isNaN(parsed.getTime())) return undefined
  return parsed.toISOString()
}

const fetchGraph = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await axios.get(`/api/worlds/${props.worldId}/knowledge-graph`, {
      headers: { Authorization: `Bearer ${authStore.token}` },
      params: {
        checkpoint_time: toCheckpointIso(),
        session_id: props.sessionId ?? undefined,
      },
    })
    graph.value = {
      nodes: Array.isArray(response.data?.nodes) ? response.data.nodes : [],
      edges: Array.isArray(response.data?.edges) ? response.data.edges : [],
    }
    edgeTypes.value = [...new Set(graph.value.edges.map((edge) => edge.type || 'related_to'))]
    renderGraph()
  } catch (error) {
    errorMessage.value = parseApiError(error)
  } finally {
    loading.value = false
  }
}

const renderGraph = () => {
  if (!svgRef.value) return
  const width = svgRef.value.clientWidth || 900
  const height = 420
  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()
  svg.attr('viewBox', `0 0 ${width} ${height}`)

  const nodes: GraphNode[] = graph.value.nodes.map((node) => ({ ...node }))
  const links = graph.value.edges.map((edge) => ({ ...edge }))

  const simulation = d3
    .forceSimulation(nodes as d3.SimulationNodeDatum[])
    .force(
      'link',
      d3.forceLink(links as d3.SimulationLinkDatum<d3.SimulationNodeDatum>[]).id((d: any) => d.id).distance(90),
    )
    .force('charge', d3.forceManyBody().strength(-260))
    .force('center', d3.forceCenter(width / 2, height / 2))

  const link = svg
    .append('g')
    .attr('stroke-opacity', 0.6)
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', (d) => edgeStroke(d.type || 'related_to'))
    .attr('stroke-width', (d) => edgeWidth(d.type || 'related_to'))
    .attr('stroke-dasharray', (d) => edgeDash(d.type || 'related_to'))

  const node = svg
    .append('g')
    .selectAll('circle')
    .data(nodes)
    .join('circle')
    .attr('r', (d) => 8 + Math.max(0, Math.min(16, (d.mastery || 0) * 16)))
    .attr('fill', (d) => statusColor(d.status))
    .attr('stroke', '#fff')
    .attr('stroke-width', 0.8)
    .style('cursor', 'pointer')
    .on('click', (_event, d) => {
      selectedNode.value = d
    })
    .call(
      d3
        .drag<SVGCircleElement, GraphNode>()
        .on('start', (event, d: any) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d: any) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d: any) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        }) as any,
    )

  const labels = svg
    .append('g')
    .selectAll('text')
    .data(nodes)
    .join('text')
    .attr('font-size', 11)
    .attr('fill', '#eee')
    .text((d) => d.name || d.id)

  simulation.on('tick', () => {
    link
      .attr('x1', (d: any) => d.source.x ?? 0)
      .attr('y1', (d: any) => d.source.y ?? 0)
      .attr('x2', (d: any) => d.target.x ?? 0)
      .attr('y2', (d: any) => d.target.y ?? 0)

    node.attr('cx', (d: any) => d.x ?? 0).attr('cy', (d: any) => d.y ?? 0)
    labels.attr('x', (d: any) => (d.x ?? 0) + 10).attr('y', (d: any) => (d.y ?? 0) + 4)
  })
}

watch(
  () => [props.worldId, props.sessionId] as const,
  () => {
    void fetchGraph()
  },
)

onMounted(() => {
  void fetchGraph()
})
</script>

<style scoped>
.knowledge-graph-panel {
  background: rgba(0, 0, 0, 0.86);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 12px;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}

.toolbar label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--text-secondary);
  font-size: 12px;
}

.toolbar input,
.toolbar button {
  background: rgba(20, 20, 30, 0.9);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  border-radius: 6px;
  padding: 6px 8px;
}

.toolbar button {
  cursor: pointer;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  background: rgba(24, 24, 38, 0.85);
  border: 1px solid rgba(74, 74, 138, 0.5);
  border-radius: 999px;
  padding: 3px 8px;
}

.legend-line {
  display: inline-block;
  width: 18px;
  height: 0;
  border-top-color: currentColor;
}

.graph-svg {
  width: 100%;
  height: 420px;
  border: 1px solid rgba(74, 74, 138, 0.5);
  border-radius: 8px;
  background: radial-gradient(circle at 40% 25%, #1f1f38 0%, #121225 100%);
}

.node-detail {
  margin-top: 10px;
  border-top: 1px solid rgba(74, 74, 138, 0.5);
  padding-top: 10px;
  color: var(--text-secondary);
  font-size: 13px;
}

.node-detail h4 {
  margin-bottom: 6px;
  color: var(--accent-gold);
}

.error {
  color: #ff7a7a;
  margin-bottom: 8px;
  font-size: 13px;
}
</style>
