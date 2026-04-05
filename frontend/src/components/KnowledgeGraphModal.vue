<script setup lang="ts">
import { ref, computed } from 'vue'
import type { KnowledgeNode, KnowledgeGraph } from '@/types'

const props = defineProps<{
  isOpen: boolean
  worldName: string
  graph: KnowledgeGraph
}>()

const emit = defineEmits<{ (e: 'close'): void }>()

const selectedNode = ref<KnowledgeNode | null>(null)

const SVG_W = 800, SVG_H = 460

// Layout: simple force-free positioning — use x/y from backend or fallback grid
const nodes = computed(() => {
  return props.graph.nodes.map((n, i) => ({
    ...n,
    cx: n.x ?? 80 + (i % 6) * 120,
    cy: n.y ?? 80 + Math.floor(i / 6) * 100,
  }))
})

const edges = computed(() => props.graph.edges)

function nodeColor(n: KnowledgeNode) {
  if (n.type === 'misconception') return '#ef4444'
  if (n.mastery >= 0.65) return '#4adf6a'
  if (n.mastery >= 0.40) return '#ffd700'
  if (n.mastery >= 0.20) return '#f97316'
  return '#94a3b8'
}

function nodeLabel(n: KnowledgeNode) {
  if (n.type === 'misconception') return '⚠ 误解'
  if (n.mastery >= 0.65) return '已掌握'
  if (n.mastery >= 0.40) return '学习中'
  if (n.mastery >= 0.20) return '初识'
  return '未接触'
}

function getEdgePoints(edge: { source: string; target: string }) {
  const src = nodes.value.find(n => n.id === edge.source)
  const tgt = nodes.value.find(n => n.id === edge.target)
  if (!src || !tgt) return null
  return { x1: src.cx, y1: src.cy, x2: tgt.cx, y2: tgt.cy }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="panel-in">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-40 flex items-center justify-center"
        style="background:rgba(0,0,0,0.75);"
        @click="emit('close')"
      >
        <div
          class="galgame-panel flex flex-col"
          style="width:860px;max-width:95vw;max-height:90vh;border-radius:16px;overflow:hidden;"
          @click.stop
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between font-ui flex-shrink-0"
            style="padding:14px 20px;border-bottom:1px solid rgba(255,215,0,0.15);"
          >
            <div>
              <span style="color:#ffd700;font-size:15px;letter-spacing:2px;">📊 知识网络</span>
              <span style="color:rgba(255,255,255,0.4);font-size:12px;margin-left:10px;">— {{ worldName }}</span>
            </div>
            <button style="color:rgba(255,255,255,0.5);cursor:pointer;" @click="emit('close')">
              ✕
            </button>
          </div>

          <!-- Body -->
          <div class="flex flex-1 overflow-hidden">
            <!-- SVG Graph -->
            <div class="flex-1 overflow-auto" style="padding:20px;">
              <template v-if="nodes.length === 0">
                <div style="color:rgba(255,255,255,0.3);text-align:center;margin-top:60px;">
                  暂无知识节点
                </div>
              </template>
              <svg
                v-else
                :width="SVG_W" :height="SVG_H"
                style="max-width:100%;"
              >
                <!-- Edges -->
                <g v-for="(edge, i) in edges" :key="i">
                  <template v-if="getEdgePoints(edge)">
                    <line
                      :x1="getEdgePoints(edge)!.x1"
                      :y1="getEdgePoints(edge)!.y1"
                      :x2="getEdgePoints(edge)!.x2"
                      :y2="getEdgePoints(edge)!.y2"
                      stroke="rgba(255,215,0,0.3)"
                      stroke-width="1"
                    />
                    <text
                      :x="(getEdgePoints(edge)!.x1 + getEdgePoints(edge)!.x2) / 2"
                      :y="(getEdgePoints(edge)!.y1 + getEdgePoints(edge)!.y2) / 2 - 4"
                      fill="rgba(255,255,255,0.3)"
                      font-size="9"
                      text-anchor="middle"
                      font-family="'Noto Sans SC', sans-serif"
                    >{{ edge.type }}</text>
                  </template>
                </g>

                <!-- Nodes -->
                <g
                  v-for="node in nodes"
                  :key="node.id"
                  style="cursor:pointer;"
                  @click="selectedNode = selectedNode?.id === node.id ? null : node"
                >
                  <circle
                    :cx="node.cx" :cy="node.cy"
                    :r="selectedNode?.id === node.id ? 14 : 10"
                    :fill="nodeColor(node)"
                    :fill-opacity="0.85"
                    :stroke="selectedNode?.id === node.id ? '#ffd700' : 'rgba(255,255,255,0.2)'"
                    :stroke-width="selectedNode?.id === node.id ? 2 : 1"
                    style="transition:all 0.2s ease;"
                  />
                  <text
                    :x="node.cx" :y="node.cy + 24"
                    fill="rgba(255,255,255,0.8)"
                    font-size="11"
                    text-anchor="middle"
                    font-family="'Noto Sans SC', sans-serif"
                  >{{ node.name }}</text>
                </g>
              </svg>
            </div>

            <!-- Node detail panel -->
            <Transition name="detail-slide">
              <div
                v-if="selectedNode"
                class="galgame-scrollbar"
                style="
                  width:200px;flex-shrink:0;
                  border-left:1px solid rgba(255,215,0,0.15);
                  padding:20px 16px;overflow-y:auto;
                "
              >
                <div class="font-ui" style="color:#ffd700;font-size:14px;margin-bottom:12px;">
                  {{ selectedNode.name }}
                </div>
                <div class="flex flex-col gap-2">
                  <div style="font-size:11px;color:rgba(255,255,255,0.5);">类型</div>
                  <div style="font-size:13px;color:rgba(255,255,255,0.85);">
                    {{ selectedNode.type }}
                  </div>
                  <div style="font-size:11px;color:rgba(255,255,255,0.5);margin-top:8px;">状态</div>
                  <div :style="{ fontSize:'13px', color: nodeColor(selectedNode) }">
                    {{ nodeLabel(selectedNode) }}
                  </div>
                  <div style="font-size:11px;color:rgba(255,255,255,0.5);margin-top:8px;">掌握度</div>
                  <div style="height:4px;background:rgba(255,255,255,0.1);border-radius:2px;overflow:hidden;">
                    <div
                      :style="{
                        height: '100%',
                        width: `${Math.round(selectedNode.mastery * 100)}%`,
                        background: nodeColor(selectedNode),
                      }"
                    />
                  </div>
                  <div style="font-size:12px;color:rgba(255,255,255,0.6);">
                    {{ Math.round(selectedNode.mastery * 100) }}%
                  </div>
                </div>
              </div>
            </Transition>
          </div>

          <!-- Legend -->
          <div
            class="flex items-center gap-6 flex-shrink-0 font-ui"
            style="padding:12px 20px;border-top:1px solid rgba(255,215,0,0.1);font-size:11px;"
          >
            <span v-for="([label, color]) in [
              ['已掌握','#4adf6a'],['学习中','#ffd700'],
              ['初识','#f97316'],['未接触','#94a3b8'],['误解','#ef4444'],
            ]" :key="label" class="flex items-center gap-1">
              <span :style="{ display:'inline-block',width:'8px',height:'8px',borderRadius:'50%',background: color }" />
              <span style="color:rgba(255,255,255,0.6);">{{ label }}</span>
            </span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.panel-in-enter-from { opacity: 0; transform: scale(0.96) translateY(8px); }
.panel-in-enter-active { transition: opacity 0.3s ease-out, transform 0.3s ease-out; }
.panel-in-leave-to { opacity: 0; }
.panel-in-leave-active { transition: opacity 0.2s ease-in; }
.detail-slide-enter-from { opacity: 0; transform: translateX(20px); }
.detail-slide-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.detail-slide-leave-to { opacity: 0; transform: translateX(20px); }
.detail-slide-leave-active { transition: opacity 0.15s ease; }
</style>
