<template>
  <div class="archive-page">
    <div class="archive-bg-image"></div>
    <div class="archive-bg-overlay"></div>

    <header class="archive-header">
      <button class="galgame-btn galgame-menu-item back-btn" @click="router.push('/home')">← 返回</button>
      <h1>档 案 管 理</h1>
      <span class="header-spacer"></span>
    </header>

    <main class="archive-content galgame-scrollbar">
      <section class="toolbar-row">
        <div class="course-filter">
          <span>课程筛选</span>
          <select v-model="selectedCourseFilter" class="galgame-input" @change="fetchProgress">
            <option value="">全部课程</option>
            <option v-for="course in courses" :key="course.id" :value="String(course.id)">
              {{ course.name }}
            </option>
          </select>
        </div>
        <button class="galgame-btn galgame-btn-primary diary-trigger" @click="openDiaryDialog">写日记</button>
      </section>

      <p v-if="errorMessage" class="error-banner">{{ errorMessage }}</p>

      <section class="archive-panel emotion-panel galgame-panel">
        <div class="panel-header">
          <h2>情感轨迹</h2>
          <span>{{ selectedCourseName || '全部课程' }}</span>
        </div>
        <EmotionTrajectory :course-id="selectedCourseId" />
      </section>

      <div class="archive-grid">
        <section class="archive-panel galgame-panel">
          <div class="panel-header">
            <h2>学习进度</h2>
            <span>{{ progressList.length }} 条</span>
          </div>

          <div class="card-list">
            <article v-for="prog in progressList" :key="prog.id" class="record-card">
              <div class="record-head">
                <strong>{{ prog.topic }}</strong>
                <span class="record-mastery">{{ prog.mastery_level }}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: `${prog.mastery_level}%` }"></div>
              </div>
              <p class="record-meta">下次复习：{{ prog.next_review ? formatDateTime(prog.next_review) : '未安排' }}</p>
            </article>

            <p v-if="progressList.length === 0" class="empty-text">暂无进度记录</p>
          </div>
        </section>

        <section class="archive-panel galgame-panel">
          <div class="panel-header">
            <h2>存档与分叉</h2>
            <span>{{ saves.length }} 条</span>
          </div>

          <div class="card-list">
            <article v-for="save in saves" :key="save.id" class="record-card save-card">
              <div class="record-head">
                <strong>{{ save.save_name }}</strong>
                <span>#{{ save.id }}</span>
              </div>
              <p class="record-meta">{{ formatDateTime(save.created_at) }}</p>
              <div class="save-actions">
                <button
                  class="galgame-btn galgame-menu-item"
                  :disabled="saveActionId === save.id"
                  @click="loadSave(save.id)"
                >
                  {{ saveActionId === save.id ? '分叉中...' : '读档分叉' }}
                </button>
                <button
                  class="galgame-btn galgame-menu-item danger"
                  :disabled="saveActionId === save.id"
                  @click="deleteSave(save.id)"
                >
                  删除
                </button>
              </div>
            </article>

            <p v-if="saves.length === 0" class="empty-text">暂无存档</p>
          </div>
        </section>
      </div>

      <section class="archive-panel galgame-panel">
        <div class="panel-header">
          <h2>学习日记</h2>
          <span>{{ diaries.length }} 篇</span>
        </div>

        <div class="card-list">
          <article v-for="diary in sortedDiaries" :key="diary.id" class="record-card">
            <div class="record-head">
              <strong>{{ courseNameMap.get(diary.course_id) || `课程 #${diary.course_id}` }}</strong>
              <span>{{ formatDateTime(diary.date) }}</span>
            </div>
            <p class="diary-content">{{ diary.content }}</p>
            <p v-if="diary.reflection" class="record-meta reflection">反思：{{ diary.reflection }}</p>
          </article>

          <p v-if="diaries.length === 0" class="empty-text">暂无学习日记</p>
        </div>
      </section>
    </main>

    <div v-if="showDiaryDialog" class="dialog-overlay" @click.self="showDiaryDialog = false">
      <div class="dialog-panel galgame-panel">
        <h3>写学习日记</h3>
        <label class="field">
          <span>选择课程</span>
          <select v-model="diaryForm.course_id" class="galgame-input">
            <option v-for="course in courses" :key="course.id" :value="course.id">
              {{ course.name }}
            </option>
          </select>
        </label>
        <label class="field">
          <span>今日学习内容</span>
          <textarea v-model="diaryForm.content" class="galgame-input" rows="4" placeholder="今天学了什么？"></textarea>
        </label>
        <label class="field">
          <span>反思总结</span>
          <textarea
            v-model="diaryForm.reflection"
            class="galgame-input"
            rows="3"
            placeholder="有什么收获或困惑？"
          ></textarea>
        </label>
        <div class="dialog-actions">
          <button class="galgame-btn galgame-menu-item" @click="showDiaryDialog = false">取消</button>
          <button class="galgame-btn galgame-btn-primary" :disabled="diarySubmitting" @click="createDiary">
            {{ diarySubmitting ? '保存中...' : '保存日记' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'
import { buildLearningRoute } from '@/utils/navigation'
import EmotionTrajectory from '@/components/EmotionTrajectory.vue'

const router = useRouter()
const authStore = useAuthStore()

interface Diary {
  id: number
  course_id: number
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

interface Course {
  id: number
  name: string
}

interface BranchResponse {
  course_id?: number
  world_id?: number
  session_id?: number
}

const diaries = ref<Diary[]>([])
const progressList = ref<Progress[]>([])
const saves = ref<Save[]>([])
const courses = ref<Course[]>([])
const selectedCourseFilter = ref('')

const showDiaryDialog = ref(false)
const diarySubmitting = ref(false)
const saveActionId = ref<number | null>(null)
const errorMessage = ref('')

const diaryForm = ref({
  course_id: null as number | null,
  content: '',
  reflection: '',
})

const selectedCourseId = computed(() => {
  const parsed = Number(selectedCourseFilter.value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
})

const courseNameMap = computed(() => new Map(courses.value.map((course) => [course.id, course.name])))

const selectedCourseName = computed(() =>
  selectedCourseId.value ? courseNameMap.value.get(selectedCourseId.value) : undefined,
)

const sortedDiaries = computed(() =>
  [...diaries.value].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()),
)

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })

const formatDateTime = (dateStr: string) => {
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return dateStr
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const toPositiveInt = (value: unknown): number | undefined => {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

const showError = (error: unknown) => {
  errorMessage.value = parseApiError(error)
  setTimeout(() => {
    errorMessage.value = ''
  }, 4000)
}

const fetchDiaries = async () => {
  try {
    const response = await axios.get('/api/learning_diary', { headers: headers() })
    diaries.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    showError(error)
  }
}

const fetchProgress = async () => {
  try {
    const response = await axios.get('/api/progress', {
      params: { course_id: selectedCourseId.value },
      headers: headers(),
    })
    progressList.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    showError(error)
  }
}

const fetchSaves = async () => {
  try {
    const response = await axios.get('/api/save', { headers: headers() })
    saves.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    showError(error)
  }
}

const fetchCourses = async () => {
  try {
    const response = await axios.get('/api/courses', { headers: headers() })
    courses.value = Array.isArray(response.data) ? response.data : []
    if (!diaryForm.value.course_id && courses.value.length > 0) {
      diaryForm.value.course_id = courses.value[0].id
    }
  } catch (error) {
    showError(error)
  }
}

const openDiaryDialog = () => {
  if (courses.value.length === 0) {
    showError(new Error('暂无课程，无法创建日记'))
    return
  }
  if (!diaryForm.value.course_id) {
    diaryForm.value.course_id = courses.value[0].id
  }
  showDiaryDialog.value = true
}

const createDiary = async () => {
  if (!diaryForm.value.course_id || !diaryForm.value.content.trim()) {
    showError(new Error('请填写课程与学习内容'))
    return
  }

  diarySubmitting.value = true
  try {
    await axios.post(
      '/api/learning_diary',
      {
        course_id: diaryForm.value.course_id,
        content: diaryForm.value.content.trim(),
        reflection: diaryForm.value.reflection.trim() || undefined,
        date: new Date().toISOString(),
      },
      { headers: headers() },
    )
    showDiaryDialog.value = false
    diaryForm.value = {
      course_id: diaryForm.value.course_id,
      content: '',
      reflection: '',
    }
    await fetchDiaries()
  } catch (error) {
    showError(error)
  } finally {
    diarySubmitting.value = false
  }
}

const loadSave = async (saveId: number) => {
  saveActionId.value = saveId
  try {
    const response = await axios.post<BranchResponse>(`/api/checkpoints/${saveId}/branch`, {}, { headers: headers() })
    const data = response.data
    const courseId = toPositiveInt(data.course_id)
    if (!courseId) throw new Error('分叉结果缺少课程信息')
    router.push(buildLearningRoute(courseId, {
      worldId: toPositiveInt(data.world_id),
      sessionId: toPositiveInt(data.session_id),
    }))
  } catch (error) {
    showError(error)
  } finally {
    saveActionId.value = null
  }
}

const deleteSave = async (saveId: number) => {
  const confirmed = window.confirm('确定要删除这个存档吗？')
  if (!confirmed) return

  saveActionId.value = saveId
  try {
    await axios.delete(`/api/save/${saveId}`, { headers: headers() })
    await fetchSaves()
  } catch (error) {
    showError(error)
  } finally {
    saveActionId.value = null
  }
}

onMounted(async () => {
  await Promise.all([fetchCourses(), fetchDiaries(), fetchProgress(), fetchSaves()])
})
</script>

<style scoped>
.archive-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: var(--bg-primary);
}

.archive-bg-image {
  position: absolute;
  inset: 0;
  opacity: 0.08;
  background-image: url('https://images.unsplash.com/photo-1675371708731-50d9c04eb530?w=1920&q=80');
  background-size: cover;
  background-position: center;
}

.archive-bg-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(10, 10, 30, 0.95) 0%, rgba(10, 10, 30, 0.98) 100%);
}

.archive-header {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
}

.archive-header h1 {
  color: var(--accent-gold);
  letter-spacing: 4px;
  font-size: 18px;
}

.header-spacer {
  width: 80px;
}

.back-btn {
  font-size: 13px;
  padding: 6px 14px;
}

.archive-content {
  position: relative;
  z-index: 2;
  height: calc(100vh - 68px);
  overflow-y: auto;
  padding: 20px 24px 24px;
}

.toolbar-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
}

.course-filter {
  display: flex;
  align-items: center;
  gap: 10px;
}

.course-filter span {
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
}

.course-filter select {
  min-width: 220px;
  padding: 8px 10px;
}

.diary-trigger {
  padding: 8px 14px;
}

.error-banner {
  margin-bottom: 12px;
  padding: 8px 10px;
  border: 1px solid rgba(223, 74, 74, 0.5);
  background: rgba(223, 74, 74, 0.15);
  color: #ffb3b3;
  font-size: 13px;
}

.archive-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.archive-panel {
  margin-bottom: 14px;
  padding: 16px 18px;
}

.panel-header {
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h2 {
  color: var(--accent-gold);
  font-size: 15px;
  letter-spacing: 1px;
}

.panel-header span {
  color: rgba(255, 255, 255, 0.35);
  font-size: 12px;
}

.emotion-panel {
  padding-bottom: 14px;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.record-card {
  border: 1px solid rgba(74, 74, 138, 0.7);
  background: rgba(0, 0, 0, 0.28);
  border-radius: var(--radius-world-card);
  padding: 10px 12px;
}

.record-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.record-head strong {
  color: var(--text-primary);
  font-size: 14px;
}

.record-head span {
  color: rgba(255, 255, 255, 0.42);
  font-size: 12px;
}

.record-mastery {
  color: #6fcf97 !important;
  font-weight: 600;
}

.record-meta {
  margin-top: 6px;
  color: rgba(255, 255, 255, 0.48);
  font-size: 12px;
}

.progress-bar {
  margin-top: 8px;
  height: 6px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.1);
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #ffd700, #6fcf97);
}

.save-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.save-actions button {
  font-size: 12px;
  padding: 6px 10px;
}

.danger {
  border-color: rgba(223, 74, 74, 0.6);
  color: #ff9a9a;
}

.danger:hover:not(:disabled) {
  border-color: rgba(223, 74, 74, 1);
  color: #ffc1c1;
}

.diary-content {
  margin-top: 8px;
  color: rgba(240, 240, 255, 0.78);
  white-space: pre-wrap;
  line-height: 1.7;
  font-size: 14px;
}

.reflection {
  border-top: 1px solid rgba(74, 74, 138, 0.6);
  padding-top: 6px;
}

.empty-text {
  text-align: center;
  color: rgba(255, 255, 255, 0.45);
  padding: 18px 0;
  font-size: 13px;
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.72);
}

.dialog-panel {
  width: min(92vw, 560px);
  padding: 18px;
  border-radius: var(--radius-modal);
}

.dialog-panel h3 {
  color: var(--accent-gold);
  font-size: 16px;
  margin-bottom: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.field span {
  color: rgba(255, 255, 255, 0.65);
  font-size: 13px;
}

.field select,
.field textarea {
  width: 100%;
  padding: 9px 10px;
}

.field textarea {
  resize: vertical;
}

.dialog-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 980px) {
  .archive-grid {
    grid-template-columns: 1fr;
  }

  .toolbar-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .course-filter {
    width: 100%;
  }

  .course-filter select {
    flex: 1;
    min-width: 0;
  }
}
</style>
