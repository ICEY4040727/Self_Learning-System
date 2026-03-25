<template>
  <div class="archive-page">
    <header class="header">
      <button class="back-btn" @click="router.push('/home')">← 返回</button>
      <h1>档案管理</h1>
    </header>

    <main class="main">
      <!-- 学习日记 -->
      <section class="section">
        <div class="section-header">
          <h2>学习日记</h2>
          <button class="add-btn" @click="showDiaryDialog = true">+ 写日记</button>
        </div>

        <div class="diary-list">
          <div v-for="diary in diaries" :key="diary.id" class="diary-card">
            <div class="diary-date">{{ formatDate(diary.date) }}</div>
            <p class="diary-content">{{ diary.content }}</p>
            <p v-if="diary.reflection" class="diary-reflection">
              反思: {{ diary.reflection }}
            </p>
          </div>
          <p v-if="diaries.length === 0" class="empty-text">暂无学习日记</p>
        </div>
      </section>

      <!-- 进度追踪 -->
      <section class="section">
        <div class="section-header">
          <h2>学习进度</h2>
          <select v-model="selectedSubjectFilter" @change="fetchProgress">
            <option value="">全部科目</option>
            <option v-for="subj in subjects" :key="subj.id" :value="subj.id">
              {{ subj.name }}
            </option>
          </select>
        </div>

        <div class="progress-list">
          <div v-for="prog in progressList" :key="prog.id" class="progress-card">
            <div class="progress-header">
              <h3>{{ prog.topic }}</h3>
              <span class="mastery">{{ prog.mastery_level }}/100</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: prog.mastery_level + '%' }"></div>
            </div>
            <p class="next-review">
              下次复习: {{ prog.next_review ? formatDate(prog.next_review) : '未安排' }}
            </p>
          </div>
          <p v-if="progressList.length === 0" class="empty-text">暂无进度记录</p>
        </div>
      </section>

      <!-- 情感轨迹 -->
      <section class="section">
        <EmotionTrajectory />
      </section>

      <!-- 存档管理 -->
      <section class="section">
        <div class="section-header">
          <h2>游戏存档</h2>
        </div>

        <div class="save-list">
          <div v-for="save in saves" :key="save.id" class="save-card">
            <div class="save-info">
              <h3>{{ save.save_name }}</h3>
              <p>{{ formatDate(save.created_at) }}</p>
            </div>
            <div class="save-actions">
              <button @click="loadSave(save.id)">读档</button>
              <button class="delete" @click="deleteSave(save.id)">删除</button>
            </div>
          </div>
          <p v-if="saves.length === 0" class="empty-text">暂无存档</p>
        </div>
      </section>

      <!-- 写日记对话框 -->
      <div v-if="showDiaryDialog" class="dialog-overlay" @click.self="showDiaryDialog = false">
        <div class="dialog">
          <h3>写学习日记</h3>
          <div class="form-group">
            <label>选择科目</label>
            <select v-model="diaryForm.subject_id">
              <option v-for="subj in subjects" :key="subj.id" :value="subj.id">
                {{ subj.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>今日学习内容</label>
            <textarea v-model="diaryForm.content" rows="4" placeholder="今天学了什么？"></textarea>
          </div>
          <div class="form-group">
            <label>反思总结</label>
            <textarea v-model="diaryForm.reflection" rows="3" placeholder="有什么收获或困惑？"></textarea>
          </div>
          <div class="dialog-actions">
            <button @click="showDiaryDialog = false">取消</button>
            <button class="primary" @click="createDiary">保存</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import EmotionTrajectory from '@/components/EmotionTrajectory.vue'

const router = useRouter()
const authStore = useAuthStore()

interface Diary {
  id: number
  subject_id: number
  date: string
  content: string
  reflection?: string
}

interface Progress {
  id: number
  topic: string
  mastery_level: number
  next_review?: string
}

interface Save {
  id: number
  save_name: string
  created_at: string
}

interface Subject {
  id: number
  name: string
}

const diaries = ref<Diary[]>([])
const progressList = ref<Progress[]>([])
const saves = ref<Save[]>([])
const subjects = ref<Subject[]>([])
const selectedSubjectFilter = ref('')

const showDiaryDialog = ref(false)
const diaryForm = ref({
  subject_id: null as number | null,
  content: '',
  reflection: ''
})

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const fetchDiaries = async () => {
  try {
    const response = await axios.get('/api/learning_diary', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    diaries.value = response.data
  } catch (error) {
    console.error('Failed to fetch diaries:', error)
  }
}

const fetchProgress = async () => {
  try {
    const params = selectedSubjectFilter.value ? `?subject_id=${selectedSubjectFilter.value}` : ''
    const response = await axios.get(`/api/progress${params}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    progressList.value = response.data
  } catch (error) {
    console.error('Failed to fetch progress:', error)
  }
}

const fetchSaves = async () => {
  try {
    const response = await axios.get('/api/save', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    saves.value = response.data
  } catch (error) {
    console.error('Failed to fetch saves:', error)
  }
}

const fetchSubjects = async () => {
  try {
    const response = await axios.get('/api/subjects', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    subjects.value = response.data
  } catch (error) {
    console.error('Failed to fetch subjects:', error)
  }
}

const createDiary = async () => {
  if (!diaryForm.value.subject_id || !diaryForm.value.content) return
  try {
    await axios.post('/api/learning_diary', {
      ...diaryForm.value,
      date: new Date().toISOString()
    }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    showDiaryDialog.value = false
    diaryForm.value = { subject_id: null, content: '', reflection: '' }
    fetchDiaries()
  } catch (error) {
    console.error('Failed to create diary:', error)
  }
}

const loadSave = async (saveId: number) => {
  router.push('/home')
}

const deleteSave = async (saveId: number) => {
  if (!confirm('确定要删除这个存档吗？')) return
  try {
    await axios.delete(`/api/save/${saveId}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    fetchSaves()
  } catch (error) {
    console.error('Failed to delete save:', error)
  }
}

onMounted(() => {
  fetchDiaries()
  fetchProgress()
  fetchSaves()
  fetchSubjects()
})
</script>

<style scoped>
.archive-page {
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
}

.header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
}

.header h1 {
  color: #ffd700;
}

.back-btn {
  padding: 8px 16px;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.back-btn:hover {
  background: #3a3a5a;
  border-color: #ffd700;
}

.section {
  margin-bottom: 30px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid #4a4a8a;
  border-radius: 12px;
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section h2 {
  color: #ffd700;
}

.section select {
  padding: 8px 12px;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  border-radius: 6px;
  color: #fff;
}

.add-btn {
  padding: 8px 16px;
  background: #4a8a4a;
  border: none;
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
}

.add-btn:hover {
  background: #5a9a5a;
}

.diary-list, .progress-list, .save-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.diary-card, .progress-card, .save-card {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #4a4a8a;
  border-radius: 8px;
  padding: 15px;
}

.diary-date {
  color: #ffd700;
  font-size: 14px;
  margin-bottom: 8px;
}

.diary-content {
  color: #fff;
  line-height: 1.6;
}

.diary-reflection {
  color: #888;
  font-size: 14px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #4a4a8a;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-header h3 {
  color: #fff;
}

.mastery {
  color: #4a8a4a;
  font-weight: bold;
}

.progress-bar {
  height: 8px;
  background: #2a2a4a;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4a8a4a, #5a9a5a);
  transition: width 0.3s;
}

.next-review {
  color: #888;
  font-size: 12px;
}

.save-info h3 {
  color: #fff;
  margin-bottom: 5px;
}

.save-info p {
  color: #888;
  font-size: 14px;
}

.save-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.save-actions button {
  padding: 6px 12px;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
}

.save-actions button:hover {
  background: #3a3a5a;
}

.save-actions button.delete {
  border-color: #8a4a4a;
}

.save-actions button.delete:hover {
  background: #8a4a4a;
}

.empty-text {
  color: #888;
  text-align: center;
  padding: 20px;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  border-radius: 12px;
  padding: 30px;
  width: 90%;
  max-width: 500px;
}

.dialog h3 {
  color: #ffd700;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  color: #fff;
  margin-bottom: 8px;
}

.form-group select, .form-group textarea {
  width: 100%;
  padding: 10px;
  background: #1a1a2e;
  border: 1px solid #4a4a8a;
  border-radius: 6px;
  color: #fff;
}

.form-group textarea {
  resize: vertical;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.dialog-actions button {
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  background: #2a2a4a;
  border: 1px solid #4a4a8a;
  color: #fff;
}

.dialog-actions button.primary {
  background: #4a8a4a;
  border: none;
}

.dialog-actions button.primary:hover {
  background: #5a9a5a;
}
</style>