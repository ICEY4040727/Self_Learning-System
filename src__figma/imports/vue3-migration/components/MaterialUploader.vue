<script setup lang="ts">
/**
 * MaterialUploader.vue
 * ──────────────────────────────────────────────────────────────
 * 课程教材上传组件
 *
 * 功能：
 *   - 拖拽 / 点击上传（.txt .md .pdf .docx，≤ 10 MB）
 *   - 客户端预校验 → XMLHttpRequest 带进度
 *   - 列出已上传教材 + 提取状态徽标（pending / processing / ready / error）
 *   - 3s 轮询刷新 pending 教材状态（由 store 管理）
 * ──────────────────────────────────────────────────────────────
 */
import { ref } from 'vue'
import { Trash2, FileText, AlertCircle, CheckCircle, Loader, Upload } from 'lucide-vue-next'
import { useCourseDesignStore } from '@/stores/course_design'
import type { CourseMaterial } from '@/types'

const store   = useCourseDesignStore()
const isDragging = ref(false)
const errors     = ref<string[]>([])

// ── Drag & Drop ───────────────────────────────────────────────
function onDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}
function onDragLeave() { isDragging.value = false }
async function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  const files = Array.from(e.dataTransfer?.files ?? [])
  await uploadFiles(files)
}

// ── Click upload ──────────────────────────────────────────────
function openFilePicker() {
  const input = document.createElement('input')
  input.type     = 'file'
  input.multiple = true
  input.accept   = '.txt,.md,.pdf,.docx'
  input.onchange = async (e) => {
    const files = Array.from((e.target as HTMLInputElement).files ?? [])
    await uploadFiles(files)
  }
  input.click()
}

async function uploadFiles(files: File[]) {
  errors.value = []
  for (const file of files) {
    try {
      await store.uploadMaterial(file)
    } catch (err: any) {
      errors.value.push(`「${file.name}」：${err.message}`)
    }
  }
}

// ── Helpers ───────────────────────────────────────────────────
function formatSize(bytes: number): string {
  if (bytes < 1024)        return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function statusLabel(s: CourseMaterial['extraction_status']): string {
  return { pending: '等待提取', processing: '提取中', ready: '就绪', error: '提取失败' }[s] ?? s
}

function statusColor(s: CourseMaterial['extraction_status']): string {
  return {
    pending:    'rgba(148,163,184,0.8)',
    processing: 'rgba(96,165,250,0.9)',
    ready:      'rgba(74,223,106,0.9)',
    error:      'rgba(239,68,68,0.9)',
  }[s] ?? 'white'
}
</script>

<template>
  <div class="flex flex-col gap-4">

    <!-- Drop zone -->
    <div
      :style="{
        border: `1px dashed ${isDragging ? 'rgba(255,215,0,0.7)' : 'rgba(255,215,0,0.22)'}`,
        background: isDragging ? 'rgba(255,215,0,0.06)' : 'transparent',
        padding: '32px',
        textAlign: 'center',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
      }"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
      @click="openFilePicker"
    >
      <Upload :size="28" style="color:rgba(255,215,0,0.5);margin:0 auto 12px;" />
      <div class="font-ui" style="color:rgba(255,255,255,0.7);font-size:14px;margin-bottom:4px;">
        拖放教材文件到此处，或<span style="color:#ffd700;"> 点击选择</span>
      </div>
      <div class="font-ui" style="color:rgba(255,255,255,0.3);font-size:11px;letter-spacing:1px;">
        支持 .txt · .md · .pdf · .docx　≤ 10 MB
      </div>
    </div>

    <!-- Upload errors -->
    <div v-for="(err, i) in errors" :key="i"
      style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);
        padding:8px 14px;display:flex;gap:8px;align-items:center;">
      <AlertCircle :size="14" style="color:#ef4444;flex-shrink:0;" />
      <span class="font-ui" style="font-size:12px;color:rgba(255,100,100,0.9);">{{ err }}</span>
    </div>

    <!-- Uploading progress -->
    <div
      v-for="uf in store.uploadingFiles"
      :key="uf.id"
      style="border:1px solid rgba(255,215,0,0.15);padding:10px 14px;"
    >
      <div class="flex items-center justify-between mb-2">
        <span class="font-ui" style="font-size:12px;color:rgba(255,255,255,0.7);">{{ uf.name }}</span>
        <span class="font-ui" style="font-size:11px;color:rgba(255,215,0,0.7);">{{ uf.progress }}%</span>
      </div>
      <div style="height:2px;background:rgba(255,255,255,0.08);">
        <div :style="{
          height:'100%', width:`${uf.progress}%`,
          background:'linear-gradient(90deg,#ffd700,#4adf6a)',
          transition:'width 0.3s ease',
        }" />
      </div>
    </div>

    <!-- Materials list -->
    <div v-if="store.materials.length > 0" class="flex flex-col gap-2">
      <div class="font-ui" style="font-size:11px;color:rgba(255,215,0,0.6);letter-spacing:2px;margin-bottom:4px;">
        已上传教材（{{ store.materials.length }}）
      </div>
      <div
        v-for="mat in store.materials"
        :key="mat.id"
        style="border:1px solid rgba(255,215,0,0.1);padding:10px 14px;
          display:flex;align-items:center;gap:12px;"
      >
        <FileText :size="16" style="color:rgba(255,215,0,0.5);flex-shrink:0;" />

        <div class="flex-1 min-w-0">
          <div class="font-ui" style="font-size:13px;color:rgba(255,255,255,0.85);
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
            {{ mat.original_filename }}
          </div>
          <div class="font-ui" style="font-size:10px;color:rgba(255,255,255,0.35);margin-top:2px;">
            {{ formatSize(mat.file_size) }}
            · {{ new Date(mat.created_at).toLocaleDateString('zh-CN') }}
          </div>
        </div>

        <!-- Extraction status badge -->
        <div class="flex items-center gap-1 flex-shrink-0">
          <Loader
            v-if="mat.extraction_status === 'processing'"
            :size="11"
            :style="{ color: statusColor(mat.extraction_status), animation: 'spin 1s linear infinite' }"
          />
          <CheckCircle
            v-else-if="mat.extraction_status === 'ready'"
            :size="11"
            :style="{ color: statusColor(mat.extraction_status) }"
          />
          <AlertCircle
            v-else-if="mat.extraction_status === 'error'"
            :size="11"
            :style="{ color: statusColor(mat.extraction_status) }"
          />
          <span class="font-ui" :style="{ fontSize:'10px', color: statusColor(mat.extraction_status) }">
            {{ statusLabel(mat.extraction_status) }}
          </span>
        </div>

        <!-- Error tooltip -->
        <div v-if="mat.extraction_status === 'error' && mat.error_message"
          :title="mat.error_message"
          style="max-width:180px;font-size:10px;color:rgba(239,68,68,0.7);
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          {{ mat.error_message }}
        </div>

        <!-- Delete -->
        <button
          class="flex-shrink-0"
          style="color:rgba(255,255,255,0.25);cursor:pointer;transition:color 0.15s ease;"
          @mouseenter="($event.target as HTMLElement).style.color='rgba(239,68,68,0.8)'"
          @mouseleave="($event.target as HTMLElement).style.color='rgba(255,255,255,0.25)'"
          @click.stop="store.deleteMaterial(mat.id)"
        >
          <Trash2 :size="14" />
        </button>
      </div>
    </div>

    <div v-else-if="!store.loadingMaterials && store.uploadingFiles.length === 0"
      class="font-ui"
      style="font-size:12px;color:rgba(255,255,255,0.25);text-align:center;padding:16px 0;">
      暂无教材，请上传课程资料
    </div>
  </div>
</template>

<style scoped>
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
