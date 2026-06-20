<template>
  <div class="bookshelf-page">
    <!-- Background -->
    <div class="bg-image"></div>
    <div class="bg-gradient"></div>

    <!-- Header -->
    <div class="bookshelf-header font-ui">
      <button class="galgame-hud-btn" @click="router.push('/home')">
        <span>←</span> 返回
      </button>
      <span class="header-title">📚 书 架</span>
      <div style="width:80px;"></div>
    </div>

    <!-- Content -->
    <div class="bookshelf-content galgame-scrollbar">
      <!-- Blueprint Builder -->
      <div class="blueprint-panel">
        <div class="panel-title">学习蓝图</div>
        <div class="panel-row">
          <textarea
            v-model="goalText"
            class="goal-input"
            rows="3"
            placeholder="说明你为什么现在要学这门内容，例如：三个月内掌握并能通过实战检验。"
          />
        </div>
        <div class="panel-actions">
          <span class="panel-hint">已选 {{ selectedBookIds.length }} 本可用教材</span>
          <button class="blueprint-btn" :disabled="drafting || !canBuildDraft" @click="handleBuildDraft">
            {{ drafting ? '生成中...' : '生成教材蓝图' }}
          </button>
        </div>
        <div v-if="draft" class="draft-summary">
          <div class="draft-line">教材：{{ draft.material_analysis?.title || '未命名' }}</div>
          <div class="draft-line">课程：{{ draft.course_blueprint?.course_title || '未命名' }}</div>
          <div class="draft-line">路由：{{ draft.course_blueprint?.route_type || 'unknown' }}</div>
          <div class="draft-line">单元：{{ draft.course_blueprint?.units?.length || 0 }}</div>
          <div class="draft-actions">
            <button class="ghost-btn" :disabled="drafting" @click="handleRegenerateDraft">重新解析</button>
            <button class="blueprint-btn" :disabled="committing" @click="handleCommitDraft">
              {{ committing ? '创建中...' : '创建课程并进入世界层' }}
            </button>
          </div>
        </div>
        <div v-if="draftError" class="draft-error">{{ draftError }}</div>
      </div>

      <!-- Upload Area -->
      <div class="upload-section">
        <div
          class="upload-zone"
          :class="{ dragover: isDragOver, uploading: uploading }"
          @dragover.prevent="isDragOver = true"
          @dragleave.prevent="isDragOver = false"
          @drop.prevent="handleDrop"
          @click="triggerUpload"
        >
          <input
            ref="fileInput"
            type="file"
            :accept="TEXTBOOK_ACCEPT"
            class="hidden-input"
            @change="handleFileSelect"
          />
          <div v-if="!uploading" class="upload-prompt">
            <div class="upload-icon">📖</div>
            <div class="upload-text">将教材拖放到这里，或点击上传</div>
            <div class="upload-hint">{{ TEXTBOOK_UPLOAD_HINT }}</div>
          </div>
          <div v-else class="upload-progress">
            <div class="progress-ring">
              <svg viewBox="0 0 36 36">
                <path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="ring-fill" :stroke-dasharray="`${uploadProgress}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span class="progress-pct">{{ uploadProgress }}%</span>
            </div>
            <div class="upload-text">上传 / 解析中…</div>
          </div>
        </div>
      </div>

      <!-- Book Grid -->
      <div class="book-grid">
        <TransitionGroup name="book-fade">
          <div
            v-for="book in books"
            :key="book.id"
            class="book-card"
            :class="{ error: book.status === 'error', selected: selectedBookIds.includes(book.id) }"
            @click="toggleBook(book)"
          >
            <!-- Book Cover -->
            <div class="book-cover">
              <div class="cover-icon">{{ getFileIcon(book.filename) }}</div>
              <div class="cover-ext">{{ getFileExt(book.filename) }}</div>
            </div>

            <!-- Book Info -->
            <div class="book-info">
              <div class="book-title" :title="book.title || book.filename">
                {{ book.title || book.filename }}
              </div>
              <div class="book-meta">
                <span v-if="book.page_count" class="meta-tag">📄 {{ book.page_count }} 页</span>
                <span class="meta-tag">📦 {{ formatSize(book.file_size) }}</span>
                <span v-if="book.status === 'error'" class="meta-tag error-tag">⚠️ 提取失败</span>
                <span v-else-if="book.is_usable" class="meta-tag ok-tag">已解析</span>
              </div>
              <div v-if="book.error_message" class="book-error">{{ book.error_message }}</div>
            </div>

            <!-- Actions -->
            <div class="book-actions">
              <button class="action-btn delete-btn" @click.stop="handleDelete(book.id)" title="删除">
                🗑️
              </button>
            </div>
            <div v-if="selectedBookIds.includes(book.id)" class="selected-badge">已选</div>
          </div>
        </TransitionGroup>

        <!-- Empty State -->
        <div v-if="!loading && books.length === 0" class="empty-state">
          <div class="empty-icon">📚</div>
          <div class="empty-text">书架空空如也</div>
          <div class="empty-hint">上传教材到书架，创建课程时可直接选用</div>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <Transition name="toast-fade">
      <div v-if="toast" class="toast" :class="toast.type">{{ toast.message }}</div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { bookshelfApi, type BookshelfItem } from '@/courses/api/bookshelf'
import { learningPlanApi, type LearningPlanDraft } from '@/courses/api/learningPlan'
import { TEXTBOOK_ACCEPT, TEXTBOOK_UPLOAD_HINT } from '@/courses/constants/textbooks'

const router = useRouter()

const books = ref<BookshelfItem[]>([])
const loading = ref(true)
const uploading = ref(false)
const uploadProgress = ref(0)
const isDragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const toast = ref<{ message: string; type: 'success' | 'error' } | null>(null)
const selectedBookIds = ref<number[]>([])
const goalText = ref('')
const draft = ref<LearningPlanDraft | null>(null)
const draftError = ref<string | null>(null)
const drafting = ref(false)
const committing = ref(false)

const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  toast.value = { message, type }
  setTimeout(() => { toast.value = null }, 3000)
}

const canBuildDraft = computed(() => {
  return selectedBookIds.value.length > 0 && goalText.value.trim().length > 0
})

const fetchBooks = async () => {
  try {
    books.value = await bookshelfApi.list()
  } catch {
    showToast('加载书架失败', 'error')
  } finally {
    loading.value = false
  }
}

const triggerUpload = () => {
  fileInput.value?.click()
}

const uploadFile = async (file: File) => {
  uploading.value = true
  uploadProgress.value = 0
  try {
    const item = await bookshelfApi.upload(file, (pct) => {
      uploadProgress.value = pct
    })
    await fetchBooks()
    if (item.is_usable) {
      showToast(`"${file.name}" 上传并解析成功`)
    } else {
      showToast(`"${file.name}" 已上传，但解析失败：${item.error_message || '请检查文件内容'}`, 'error')
    }
  } catch (e: any) {
    const msg = getErrorMessage(e, '上传失败')
    showToast(msg, 'error')
  } finally {
    uploading.value = false
  }
}

const toggleBook = (book: BookshelfItem) => {
  if (!book.is_usable) return
  const idx = selectedBookIds.value.indexOf(book.id)
  if (idx >= 0) {
    selectedBookIds.value.splice(idx, 1)
  } else {
    selectedBookIds.value.push(book.id)
  }
}

const handleFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files?.[0]) {
    uploadFile(target.files[0])
    target.value = '' // reset for re-upload
  }
}

const handleDrop = (e: DragEvent) => {
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}

const handleDelete = async (id: number) => {
  try {
    await bookshelfApi.delete(id)
    books.value = books.value.filter(b => b.id !== id)
    showToast('已删除')
  } catch (e: any) {
    showToast(getErrorMessage(e, '删除失败'), 'error')
  }
}

const handleBuildDraft = async () => {
  if (!canBuildDraft.value) return
  drafting.value = true
  draftError.value = null
  try {
    draft.value = await learningPlanApi.createDraft({
      material_ids: selectedBookIds.value,
      goal: goalText.value.trim(),
      course_form: {},
    })
    showToast('教材蓝图已生成')
  } catch (e: any) {
    draftError.value = getErrorMessage(e, '生成蓝图失败')
  } finally {
    drafting.value = false
  }
}

const handleRegenerateDraft = async () => {
  if (!draft.value) return
  drafting.value = true
  draftError.value = null
  try {
    draft.value = await learningPlanApi.regenerateDraft(draft.value.id)
    showToast('蓝图已重新解析')
  } catch (e: any) {
    draftError.value = getErrorMessage(e, '重新解析失败')
  } finally {
    drafting.value = false
  }
}

const handleCommitDraft = async () => {
  if (!draft.value) return
  committing.value = true
  draftError.value = null
  try {
    const result = await learningPlanApi.commitDraft(draft.value.id, {
      course_name: draft.value.course_blueprint?.course_title || undefined,
      description: draft.value.goal,
      target_level: 'understand',
      world_name: draft.value.world_plan?.world?.name || undefined,
      world_description: draft.value.world_plan?.world?.premise || undefined,
    })
    showToast('课程已创建，正在进入世界层')
    router.push(`/home/worlds/${result.world_id}`)
  } catch (e: any) {
    draftError.value = getErrorMessage(e, '创建课程失败')
  } finally {
    committing.value = false
  }
}

function getErrorMessage(error: any, fallback: string): string {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string') return detail.message
    if (Array.isArray(detail.linked_course_ids) && detail.linked_course_ids.length > 0) {
      return `教材仍被课程引用：${detail.linked_course_ids.join(', ')}`
    }
  }
  return error?.message || fallback
}

const getFileIcon = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return '📕'
  if (ext === 'epub') return '📗'
  return '📘'
}

const getFileExt = (filename: string) => {
  return (filename.split('.').pop() || '').toUpperCase()
}

const formatSize = (bytes: number | null) => {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

onMounted(fetchBooks)
</script>

<style scoped>
.bookshelf-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #0a0a1e;
}

.bg-image {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #0f0f2e 0%, #1a1a3e 40%, #0d0d25 100%);
  background-size: cover;
  background-position: center;
  opacity: 0.6;
}

.bg-gradient {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 30% 20%, rgba(255, 215, 0, 0.03) 0%, transparent 50%),
    radial-gradient(ellipse at 70% 60%, rgba(96, 165, 250, 0.03) 0%, transparent 50%),
    linear-gradient(to bottom, rgba(10, 10, 30, 0.1) 0%, rgba(0, 0, 0, 0.3) 100%);
}

/* Header */
.bookshelf-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  z-index: 10;
}

.header-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 16px;
  letter-spacing: 6px;
  color: #ffd700;
  font-weight: 600;
}

.galgame-hud-btn {
  font-family: "Noto Sans SC", sans-serif;
  padding: 6px 16px;
  font-size: 12px;
  letter-spacing: 2px;
  color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.galgame-hud-btn:hover {
  color: #ffd700;
  border-color: rgba(255, 215, 0, 0.4);
  background: rgba(255, 215, 0, 0.08);
}

/* Content */
.bookshelf-content {
  position: relative;
  z-index: 10;
  padding: 0 40px 40px;
  overflow-y: auto;
  height: calc(100vh - 60px);
}

/* Upload Zone */
.upload-section {
  margin-bottom: 32px;
}

.blueprint-panel {
  margin-bottom: 28px;
  padding: 20px;
  border: 1px solid rgba(255, 215, 0, 0.12);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.22);
}

.panel-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  letter-spacing: 3px;
  color: #ffd700;
  margin-bottom: 12px;
}

.panel-row {
  margin-bottom: 12px;
}

.goal-input {
  width: 100%;
  min-height: 88px;
  resize: vertical;
  border-radius: 8px;
  border: 1px solid rgba(255, 215, 0, 0.18);
  background: rgba(0, 0, 0, 0.35);
  color: rgba(255, 255, 255, 0.82);
  padding: 12px 14px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  line-height: 1.6;
}

.panel-actions,
.draft-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-hint {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.blueprint-btn,
.ghost-btn {
  padding: 10px 16px;
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid rgba(255, 215, 0, 0.18);
}

.blueprint-btn {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: #171717;
  font-weight: 600;
}

.ghost-btn {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.72);
}

.blueprint-btn:disabled,
.ghost-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.draft-summary {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.draft-line {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  margin-bottom: 6px;
}

.draft-error {
  margin-top: 10px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: #ef4444;
}

.upload-zone {
  border: 2px dashed rgba(255, 215, 0, 0.2);
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(0, 0, 0, 0.2);
}

.upload-zone:hover,
.upload-zone.dragover {
  border-color: rgba(255, 215, 0, 0.5);
  background: rgba(255, 215, 0, 0.04);
}

.upload-zone.uploading {
  pointer-events: none;
  opacity: 0.8;
}

.hidden-input {
  display: none;
}

.upload-icon {
  font-size: 36px;
  margin-bottom: 12px;
}

.upload-text {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  letter-spacing: 2px;
}

.upload-hint {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  margin-top: 8px;
  letter-spacing: 1px;
}

/* Upload Progress */
.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.progress-ring {
  position: relative;
  width: 64px;
  height: 64px;
}

.progress-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: rgba(255, 215, 0, 0.1);
  stroke-width: 3;
}

.ring-fill {
  fill: none;
  stroke: #ffd700;
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dasharray 0.3s ease;
}

.progress-pct {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #ffd700;
  font-weight: 600;
}

/* Book Grid */
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.book-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.1);
  border-radius: 10px;
  transition: all 0.25s ease;
  position: relative;
}

.book-card:hover {
  border-color: rgba(255, 215, 0, 0.3);
  background: rgba(255, 215, 0, 0.03);
  transform: translateY(-2px);
}

.book-card.selected {
  border-color: rgba(251, 191, 36, 0.8);
  background: rgba(251, 191, 36, 0.08);
}

.book-card.error {
  border-color: rgba(239, 68, 68, 0.2);
}

.book-cover {
  width: 52px;
  height: 68px;
  border-radius: 6px;
  background: rgba(255, 215, 0, 0.08);
  border: 1px solid rgba(255, 215, 0, 0.15);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cover-icon {
  font-size: 20px;
}

.cover-ext {
  font-size: 8px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 1px;
  margin-top: 2px;
}

.book-info {
  flex: 1;
  min-width: 0;
}

.book-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}

.book-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-tag {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.meta-tag.ok-tag {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.meta-tag.error-tag {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.book-error {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(239, 68, 68, 0.7);
  margin-top: 4px;
}

.book-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.selected-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  font-size: 10px;
  font-family: "Noto Sans SC", sans-serif;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  border-color: rgba(255, 215, 0, 0.4);
  background: rgba(255, 215, 0, 0.08);
}

.delete-btn:hover {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.08);
}

/* Empty State */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px 0;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.4;
}

.empty-text {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 3px;
  margin-bottom: 8px;
}

.empty-hint {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.25);
  letter-spacing: 1px;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 24px;
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  letter-spacing: 1px;
  z-index: 9999;
  backdrop-filter: blur(10px);
}

.toast.success {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #10b981;
}

.toast.error {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

/* Scrollbar */
.bookshelf-content::-webkit-scrollbar {
  width: 6px;
}

.bookshelf-content::-webkit-scrollbar-track {
  background: transparent;
}

.bookshelf-content::-webkit-scrollbar-thumb {
  background: rgba(255, 215, 0, 0.15);
  border-radius: 3px;
}

.bookshelf-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 215, 0, 0.3);
}

/* Transitions */
.book-fade-enter-active {
  transition: all 0.3s ease;
}

.book-fade-leave-active {
  transition: all 0.2s ease;
}

.book-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.book-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: opacity 0.25s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
}
</style>

