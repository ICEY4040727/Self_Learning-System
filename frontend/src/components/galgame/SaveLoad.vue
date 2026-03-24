<template>
  <div class="save-load-panel">
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

    <div class="save-list">
      <div
        v-for="save in saves"
        :key="save.id"
        class="save-item"
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
        v-if="selectedSave && mode === 'save'"
        class="action-button save"
        @click="handleSave"
      >
        确认存档
      </button>
      <button
        v-if="selectedSave && mode === 'load'"
        class="action-button load"
        @click="handleLoad"
      >
        确认读档
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps<{
  subjectId: number
  sessionId?: number
}>()

const emit = defineEmits<{
  loaded: [data: any]
}>()

const mode = ref<'save' | 'load'>('save')
const saves = ref<any[]>([])
const selectedSave = ref<any>(null)
const newSaveName = ref('')

const fetchSaves = async () => {
  try {
    const response = await axios.get('/api/save', {
      params: { subject_id: props.subjectId }
    })
    saves.value = response.data
  } catch (error) {
    console.error('Failed to fetch saves:', error)
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
    alert('存档成功！')
  } catch (error) {
    console.error('Save failed:', error)
    alert('存档失败')
  }
}

const handleLoad = async () => {
  if (!selectedSave.value) return

  try {
    const response = await axios.get(`/api/save/${selectedSave.value.id}`)
    emit('load', response.data.data)
    alert('读档成功！')
  } catch (error) {
    console.error('Load failed:', error)
    alert('读档失败')
  }
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(fetchSaves)
</script>

<style scoped>
.save-load-panel {
  background: rgba(0, 0, 0, 0.9);
  border: 2px solid #4a4a8a;
  border-radius: 12px;
  padding: 20px;
  min-width: 400px;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.tabs button {
  flex: 1;
  padding: 10px;
  background: #2a2a4a;
  border: none;
  color: #aaa;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.3s;
}

.tabs button.active {
  background: #4a4a8a;
  color: #ffd700;
}

.save-list {
  max-height: 300px;
  overflow-y: auto;
}

.save-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  background: #1a1a2e;
  margin-bottom: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.save-item:hover {
  background: #2a2a4a;
}

.no-saves {
  text-align: center;
  color: #666;
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
  background: #1a1a2e;
  border: 1px solid #4a4a8a;
  color: #fff;
  border-radius: 6px;
}

.action-button {
  padding: 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.3s;
}

.action-button.save {
  background: linear-gradient(135deg, #4a8a4a, #3a7a3a);
  color: #fff;
}

.action-button.load {
  background: linear-gradient(135deg, #4a4a8a, #3a3a7a);
  color: #fff;
}
</style>