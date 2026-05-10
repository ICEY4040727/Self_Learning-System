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
            accept=".pdf,.txt,.md,.markdown,.epub"
            class="hidden-input"
            @change="handleFileSelect"
          />
          <div v-if="!uploading" class="upload-prompt">
            <div class="upload-icon">📖</div>
            <div class="upload-text">将教材拖放到这里，或点击上传</div>
            <div class="upload-hint">支持 PDF、TXT、MD、EPUB 格式，最大 50MB</div>
          </div>
          <div v-else class="upload-progress">
            <div class="progress-ring">
              <svg viewBox="0 0 36 36">
                <path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="ring-fill" :stroke-dasharray="`${uploadProgress}, 100`" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span class="progress-pct">{{ uploadProgress }}%</span>
            </div>
            <div class="upload-text">上传中…</div>
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
            :class="{ error: book.status === 'error' }"
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
                <span v-else-if="book.status === 'extracted'" class="meta-tag ok-tag">✅ 已解析</span>
              </div>
              <div v-if="book.error_message" class="book-error">{{ book.error_message }}</div>
            </div>

            <!-- Actions -->
            <div class="book-actions">
              <button class="action-btn delete-btn" @click="handleDelete(book.id)" title="删除">
                🗑️
              </button>
            </div>
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { bookshelfApi, type BookshelfItem } from '@/api/bookshelf'

const router = useRouter()

const books = ref<BookshelfItem[]>([])
const loading = ref(true)
const uploading = ref(false)
const uploadProgress = ref(0)
const isDragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const toast = ref<{ message: string; type: 'success' | 'error' } | null>(null)

const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  toast.value = { message, type }
  setTimeout(() => { toast.value = null }, 3000)
}

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
    await bookshelfApi.upload(file, (pct) => {
      uploadProgress.value = pct
    })
    showToast(`"${file.name}" 上传成功`)
    await fetchBooks()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '上传失败'
    showToast(msg, 'error')
  } finally {
    uploading.value = false
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
  } catch {
    showToast('删除失败', 'error')
  }
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
}

.book-card:hover {
  border-color: rgba(255, 215, 0, 0.3);
  background: rgba(255, 215, 0, 0.03);
  transform: translateY(-2px);
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

