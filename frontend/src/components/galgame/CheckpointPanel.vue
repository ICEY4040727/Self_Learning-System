<template>
  <div class="checkpoint-overlay" @click.self="$emit('close')">
    <div class="checkpoint-panel">
      <div class="header">
        <h3>Checkpoint</h3>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>

      <div class="tabs">
        <button :class="{ active: mode === 'commit' }" @click="mode = 'commit'">COMMIT</button>
        <button :class="{ active: mode === 'branch' }" @click="mode = 'branch'">BRANCH</button>
      </div>

      <div v-if="errorMessage" class="error">{{ errorMessage }}</div>

      <div class="list">
        <button
          v-for="checkpoint in checkpoints"
          :key="checkpoint.id"
          class="checkpoint-item"
          :class="{ selected: selectedCheckpointId === checkpoint.id }"
          @click="selectedCheckpointId = checkpoint.id"
        >
          <span>{{ checkpoint.save_name }}</span>
          <small>{{ formatDate(checkpoint.created_at) }}</small>
        </button>
        <div v-if="checkpoints.length === 0" class="empty">暂无 checkpoint</div>
      </div>

      <div class="actions">
        <template v-if="mode === 'commit'">
          <input v-model="saveName" placeholder="checkpoint 名称" />
          <button class="primary" :disabled="!saveName.trim() || pending" @click="commitCheckpoint">
            {{ pending ? '提交中...' : '创建 Checkpoint' }}
          </button>
        </template>
        <template v-else>
          <input v-model="branchName" placeholder="分支名称（可选）" />
          <button class="primary" :disabled="!selectedCheckpointId || pending" @click="branchFromCheckpoint">
            {{ pending ? '分叉中...' : '从选中 Checkpoint 分叉' }}
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'

interface CheckpointItem {
  id: number
  world_id: number
  session_id: number | null
  save_name: string
  message_index: number
  created_at: string
}

interface BranchResult {
  session_id: number
  course_id: number
  world_id: number
  parent_checkpoint_id: number
  branch_name: string
}

const props = defineProps<{
  worldId: number
  sessionId?: number
}>()

const emit = defineEmits<{
  close: []
  branched: [payload: BranchResult]
  committed: [payload: CheckpointItem]
}>()

const authStore = useAuthStore()
const mode = ref<'commit' | 'branch'>('commit')
const checkpoints = ref<CheckpointItem[]>([])
const selectedCheckpointId = ref<number | null>(null)
const saveName = ref('')
const branchName = ref('')
const pending = ref(false)
const errorMessage = ref('')

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })

const fetchCheckpoints = async () => {
  try {
    const response = await axios.get(`/api/worlds/${props.worldId}/checkpoints`, { headers: headers() })
    checkpoints.value = Array.isArray(response.data) ? response.data : []
    if (checkpoints.value.length > 0 && selectedCheckpointId.value == null) {
      selectedCheckpointId.value = checkpoints.value[0].id
    }
  } catch (error) {
    errorMessage.value = parseApiError(error)
  }
}

const commitCheckpoint = async () => {
  pending.value = true
  errorMessage.value = ''
  try {
    const response = await axios.post(
      '/api/checkpoints',
      {
        world_id: props.worldId,
        session_id: props.sessionId,
        save_name: saveName.value.trim(),
      },
      { headers: headers() },
    )
    saveName.value = ''
    await fetchCheckpoints()
    emit('committed', response.data as CheckpointItem)
  } catch (error) {
    errorMessage.value = parseApiError(error)
  } finally {
    pending.value = false
  }
}

const branchFromCheckpoint = async () => {
  if (!selectedCheckpointId.value) return
  pending.value = true
  errorMessage.value = ''
  try {
    const response = await axios.post(
      `/api/checkpoints/${selectedCheckpointId.value}/branch`,
      { branch_name: branchName.value.trim() || undefined },
      { headers: headers() },
    )
    emit('branched', response.data as BranchResult)
  } catch (error) {
    errorMessage.value = parseApiError(error)
  } finally {
    pending.value = false
  }
}

const formatDate = (value: string): string => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  void fetchCheckpoints()
})
</script>

<style scoped>
.checkpoint-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.66);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.checkpoint-panel {
  width: min(560px, 92vw);
  background: rgba(10, 10, 20, 0.96);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 14px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.header h3 {
  color: var(--accent-gold);
}

.close-btn {
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.tabs button {
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}

.tabs button.active {
  color: var(--accent-gold);
  border-color: var(--accent-gold);
}

.list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 250px;
  overflow-y: auto;
}

.checkpoint-item {
  border: 1px solid rgba(74, 74, 138, 0.5);
  background: rgba(24, 24, 38, 0.9);
  color: var(--text-primary);
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  cursor: pointer;
}

.checkpoint-item small {
  color: var(--text-muted);
}

.checkpoint-item.selected {
  border-color: var(--accent-gold);
}

.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.actions input {
  flex: 1;
  border: 1px solid var(--border-subtle);
  background: rgba(24, 24, 38, 0.9);
  border-radius: 8px;
  color: var(--text-primary);
  padding: 8px 10px;
}

.primary {
  border: 1px solid #4a8a4a;
  background: #2f6f2f;
  border-radius: 8px;
  color: #fff;
  padding: 8px 12px;
  cursor: pointer;
  white-space: nowrap;
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: #ff8b8b;
  font-size: 13px;
  margin-bottom: 8px;
}

.empty {
  color: var(--text-muted);
  font-size: 13px;
  padding: 8px 0;
}
</style>
