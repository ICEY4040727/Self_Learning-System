<template>
  <div class="save-load-overlay" @click.self="emit('close')">
  <div class="save-load-panel">
    <div class="panel-header">
      <div class="tabs">
      <button
        :class="{ active: mode === 'save' }"
        @click="mode = 'save'"
      >
        存档
      </button>
      <button
        :class="{ active: mode === 'load' }"
        @click="mode = 'load'"
      >
        读档
      </button>
      </div>
      <button class="close-btn" @click="emit('close')">✕</button>
    </div>

    <div class="save-list">
      <div
        v-for="save in saves"
        :key="save.id"
        class="save-item"
        :class="{ 'save-item-selected': selectedSave?.id === save.id }"
        @click="selectSave(save)"
      >
        <span class="save-name">{{ save.save_name }}</span>
        <span class="save-date">{{ formatDate(save.created_at) }}</span>
      </div>
      <div v-if="saves.length === 0" class="no-saves">
        暂无{{ mode === 'save' ? '存档' : '可读档' }}
      </div>
    </div>

    <div class="actions">
      <input
        v-if="mode === 'save'"
        v-model="newSaveName"
        placeholder="输入存档名称"
        class="save-name-input"
      />
      <button
        v-if="mode === 'save' && newSaveName.trim()"
        class="action-button action-save"
        @click="handleSave"
      >
        确认存档
      </button>
      <button
        v-if="selectedSave && mode === 'load'"
        class="action-button action-load"
        @click="handleLoad"
      >
        确认读档
      </button>
    </div>

    <!-- Toast 通知 -->
    <Transition name="toast">
      <div v-if="toast.show" class="toast" :class="toast.type">
        {{ toast.message }}
      </div>
    </Transition>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { parseApiError } from '@/utils/error'

const props = defineProps<{
  subjectId: number
  sessionId?: number
}>()

const emit = defineEmits<{
  load: [data: any]
  close: []
}>()

const mode = ref<'save' | 'load'>('save')
const saves = ref<any[]>([])
const selectedSave = ref<any>(null)
const newSaveName = ref('')
const toast = reactive({ show: false, message: '', type: 'success' as 'success' | 'error' })

const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  toast.show = true
  toast.message = message
  toast.type = type
  setTimeout(() => { toast.show = false }, 2500)
}

const fetchSaves = async () => {
  try {
    const response = await axios.get('/api/save', {
      params: { subject_id: props.subjectId }
    })
    saves.value = response.data
  } catch (error) {
    showToast(parseApiError(error), 'error')
  }
}

const selectSave = (save: any) => {
  selectedSave.value = save
}

const handleSave = async () => {
  if (!newSaveName.value) return

  try {
    await axios.post('/api/save', {
      subject_id: props.subjectId,
      session_id: props.sessionId,
      save_name: newSaveName.value
    })
    newSaveName.value = ''
    await fetchSaves()
    showToast('存档成功')
  } catch (error) {
    showToast(parseApiError(error), 'error')
  }
}

const handleLoad = async () => {
  if (!selectedSave.value) return

  try {
    const response = await axios.get(`/api/save/${selectedSave.value.id}`)
    emit('load', response.data.data)
    showToast('读档成功')
  } catch (error) {
    showToast(parseApiError(error), 'error')
  }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(fetchSaves)
</script>

<style scoped>
.save-load-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.save-load-panel {
  position: relative;
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 20px;
  width: 90%;
  max-width: 460px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  transition: color var(--transition-fast);
}

.close-btn:hover {
  color: var(--text-primary);
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.tabs button {
  flex: 1;
  padding: 10px;
  background: var(--bg-secondary);
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  transition: all var(--transition-normal);
  font-family: var(--font-ui);
}

.tabs button.active {
  background: var(--border-subtle);
  color: var(--accent-gold);
}

.save-list {
  max-height: 300px;
  overflow-y: auto;
}

.save-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  background: var(--bg-secondary);
  margin-bottom: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
}

.save-item:hover {
  background: rgba(42, 42, 74, 0.8);
}

.save-item-selected {
  border-color: var(--accent-gold);
  background: rgba(42, 42, 74, 0.8);
}

.save-name {
  color: var(--text-primary);
  font-size: 14px;
}

.save-date {
  color: var(--text-muted);
  font-size: 12px;
}

.no-saves {
  text-align: center;
  color: var(--text-muted);
  padding: 40px;
}

.actions {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.save-name-input {
  padding: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  border-radius: 6px;
  font-family: var(--font-ui);
  transition: border-color var(--transition-fast);
}

.save-name-input:focus {
  outline: none;
  border-color: var(--accent-gold);
}

.action-button {
  padding: 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
  font-family: var(--font-ui);
  transition: all var(--transition-normal);
}

.action-save {
  background: linear-gradient(135deg, #4a8a4a, #3a7a3a);
  color: #fff;
}

.action-save:hover {
  box-shadow: 0 0 12px rgba(74, 138, 74, 0.4);
}

.action-load {
  background: linear-gradient(135deg, var(--border-subtle), #3a3a7a);
  color: #fff;
}

.action-load:hover {
  box-shadow: 0 0 12px rgba(74, 74, 138, 0.4);
}

/* Toast */
.toast {
  position: absolute;
  bottom: -40px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  white-space: nowrap;
}

.toast.success {
  background: rgba(74, 138, 74, 0.9);
  color: #fff;
}

.toast.error {
  background: rgba(223, 74, 74, 0.9);
  color: #fff;
}

.toast-enter-active, .toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from, .toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}
</style>
