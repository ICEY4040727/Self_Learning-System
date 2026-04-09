<template>
  <div class="timeline-tree">
    <div v-if="loading" class="hint">时间线加载中...</div>
    <div v-else-if="errorMessage" class="error">{{ errorMessage }}</div>
    <div v-else-if="sessions.length === 0" class="hint">当前世界暂无会话</div>

    <div
      v-for="session in orderedSessions"
      :key="session.id"
      class="session-node"
      :style="{ marginLeft: `${sessionDepth(session.id) * 20}px` }"
    >
      <div class="session-card">
        <div class="session-title">
          <strong>#{{ session.id }}</strong>
          <span v-if="session.branch_name">分支：{{ session.branch_name }}</span>
          <span v-else>主线</span>
        </div>
        <div class="session-meta">
          课程 {{ session.course_id }} · 阶段 {{ session.relationship_stage }}
        </div>
        <div class="session-meta secondary">
          开始于 {{ formatDate(session.started_at) }}
          <span v-if="session.parent_checkpoint_id != null"> · 来源存档 #{{ session.parent_checkpoint_id }}</span>
        </div>
      </div>

      <div v-if="checkpointsBySession.get(session.id)?.length" class="checkpoint-list">
        <button
          v-for="checkpoint in checkpointsBySession.get(session.id)"
          :key="checkpoint.id"
          class="checkpoint-pill"
          @click="$emit('branch', { id: checkpoint.id, save_name: checkpoint.save_name })"
        >
          {{ checkpoint.save_name }} · #{{ checkpoint.message_index }} · {{ formatDate(checkpoint.created_at) }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import client from '@/api/client'
import { parseApiError } from '@/utils/error'

interface TimelineSession {
  id: number
  course_id: number
  parent_checkpoint_id: number | null
  branch_name: string | null
  started_at: string
  relationship_stage: string
}

interface TimelineCheckpoint {
  id: number
  session_id: number | null
  save_name: string
  message_index: number
  created_at: string
}

const props = defineProps<{
  worldId: number
}>()

defineEmits<{
  branch: [checkpoint: { id: number; save_name: string }]
}>()

const sessions = ref<TimelineSession[]>([])
const checkpoints = ref<TimelineCheckpoint[]>([])
const loading = ref(false)
const errorMessage = ref('')


const fetchTimeline = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await client.get(`/worlds/${props.worldId}/timelines`)
    
    sessions.value = Array.isArray(data.sessions) ? data.sessions : []
    checkpoints.value = Array.isArray(data.checkpoints) ? data.checkpoints : []
  } catch (error) {
    errorMessage.value = parseApiError(error)
  } finally {
    loading.value = false
  }
}

const checkpointsBySession = computed(() => {
  const map = new Map<number, TimelineCheckpoint[]>()
  for (const checkpoint of checkpoints.value) {
    if (checkpoint.session_id == null) continue
    const list = map.get(checkpoint.session_id) || []
    list.push(checkpoint)
    map.set(checkpoint.session_id, list)
  }
  for (const [key, list] of map.entries()) {
    map.set(
      key,
      [...list].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
    )
  }
  return map
})

const checkpointToSession = computed(() => {
  const map = new Map<number, number>()
  for (const checkpoint of checkpoints.value) {
    if (checkpoint.session_id != null) {
      map.set(checkpoint.id, checkpoint.session_id)
    }
  }
  return map
})

const orderedSessions = computed(() =>
  [...sessions.value].sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime()),
)

const sessionDepthMap = computed(() => {
  const depthMemo = new Map<number, number>()
  const sessionById = new Map(sessions.value.map((session) => [session.id, session]))

  const computeDepth = (id: number, stack: Set<number>): number => {
    if (depthMemo.has(id)) return depthMemo.get(id) || 0
    if (stack.has(id)) return 0
    stack.add(id)
    const session = sessionById.get(id)
    if (!session || session.parent_checkpoint_id == null) {
      depthMemo.set(id, 0)
      stack.delete(id)
      return 0
    }
    const parentSessionId = checkpointToSession.value.get(session.parent_checkpoint_id)
    if (parentSessionId == null) {
      depthMemo.set(id, 1)
      stack.delete(id)
      return 1
    }
    const depth = computeDepth(parentSessionId, stack) + 1
    depthMemo.set(id, depth)
    stack.delete(id)
    return depth
  }

  for (const session of sessions.value) {
    if (!depthMemo.has(session.id)) {
      computeDepth(session.id, new Set<number>())
    }
  }

  return depthMemo
})

const sessionDepth = (sessionId: number): number => sessionDepthMap.value.get(sessionId) || 0

const formatDate = (value: string): string => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

watch(
  () => props.worldId,
  () => {
    if (props.worldId) void fetchTimeline()
  },
)

onMounted(() => {
  if (props.worldId) void fetchTimeline()
})
</script>

<style scoped>
.timeline-tree {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.session-node {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-card {
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-world-card);
  padding: 10px 12px;
}

.session-title {
  display: flex;
  gap: 8px;
  color: var(--text-primary);
  font-size: 13px;
}

.session-meta {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.session-meta.secondary {
  margin-top: 2px;
  color: rgba(170, 170, 170, 0.7);
}

.checkpoint-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.checkpoint-pill {
  border: 1px solid var(--border-subtle);
  background: rgba(42, 42, 74, 0.65);
  color: var(--text-secondary);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
}

.checkpoint-pill:hover {
  border-color: var(--accent-gold);
  color: var(--accent-gold);
}

.hint {
  color: var(--text-muted);
  font-size: 13px;
}

.error {
  color: #ff8b8b;
  font-size: 13px;
}
</style>
