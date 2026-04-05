/**
 * stores/course_design.ts
 * ──────────────────────────────────────────────────────────────
 * 课程设计 Pinia Store
 *
 * 管理：
 *   - 教材上传 / 列表 / 删除
 *   - AI 课时切分触发 + 进度轮询
 *   - 学习单元 列表 / 编辑 / 状态更新 / 删除
 *   - 上传前客户端校验（MIME / 大小）
 * ──────────────────────────────────────────────────────────────
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import client from '@/api/client'
import type {
  CourseMaterial, LearningUnit, GenerateUnitsResponse, ExtractionStatus,
} from '@/types'
import {
  ALLOWED_MATERIAL_TYPES, MAX_MATERIAL_SIZE_BYTES,
} from '@/types'

// ── Types ─────────────────────────────────────────────────────
interface UploadingFile {
  id:       string        // temp client-side id
  name:     string
  progress: number        // 0-100
  error?:   string
}

interface GenerateOptions {
  materialIds:      number[]
  targetUnitCount:  number
  overwrite:        boolean
}

// ── Store ─────────────────────────────────────────────────────
export const useCourseDesignStore = defineStore('courseDesign', () => {

  // ── State ────────────────────────────────────────────────────
  const courseId          = ref<number | null>(null)
  const materials         = ref<CourseMaterial[]>([])
  const units             = ref<LearningUnit[]>([])
  const uploadingFiles    = ref<UploadingFile[]>([])

  const generating        = ref(false)
  const generateWarnings  = ref<string[]>([])
  const loadingMaterials  = ref(false)
  const loadingUnits      = ref(false)
  const error             = ref<string | null>(null)

  // Polling for pending/processing materials
  let pollingTimer: ReturnType<typeof setInterval> | null = null

  // ── Computed ─────────────────────────────────────────────────
  const readyMaterials    = computed(() => materials.value.filter(m => m.extraction_status === 'ready'))
  const pendingMaterials  = computed(() => materials.value.filter(m =>
    m.extraction_status === 'pending' || m.extraction_status === 'processing',
  ))
  const draftUnits        = computed(() => units.value.filter(u => u.status === 'draft'))
  const readyUnits        = computed(() => units.value.filter(u => u.status === 'ready'))
  const totalEstimatedMin = computed(() =>
    units.value.reduce((sum, u) => sum + u.estimated_minutes, 0)
  )

  // ── Init ──────────────────────────────────────────────────────
  async function init(_courseId: number) {
    courseId.value = _courseId
    error.value    = null
    await Promise.all([fetchMaterials(), fetchUnits()])
    _startPollingIfNeeded()
  }

  function dispose() {
    _stopPolling()
    courseId.value       = null
    materials.value      = []
    units.value          = []
    uploadingFiles.value = []
    generateWarnings.value = []
  }

  // ── Materials ─────────────────────────────────────────────────
  async function fetchMaterials() {
    if (!courseId.value) return
    loadingMaterials.value = true
    try {
      const { data } = await client.get<{ materials: CourseMaterial[]; total: number }>(
        `/courses/${courseId.value}/materials`,
      )
      materials.value = data.materials
      _startPollingIfNeeded()
    } finally {
      loadingMaterials.value = false
    }
  }

  /**
   * 上传前客户端校验 + XMLHttpRequest 上传（带进度）
   */
  async function uploadMaterial(file: File): Promise<void> {
    // Client-side pre-validation (mirror backend constraints)
    if (!ALLOWED_MATERIAL_TYPES.includes(file.type as any)) {
      throw new Error(
        `不支持的文件类型 "${file.type}"。请上传 .txt / .md / .pdf / .docx 文件。`
      )
    }
    if (file.size > MAX_MATERIAL_SIZE_BYTES) {
      throw new Error(
        `文件超过 10 MB 限制（当前 ${(file.size / 1024 / 1024).toFixed(1)} MB）。`
      )
    }

    const tempId: string = `upload-${Date.now()}`
    uploadingFiles.value.push({ id: tempId, name: file.name, progress: 0 })

    return new Promise((resolve, reject) => {
      const formData = new FormData()
      formData.append('file', file)

      const xhr = new XMLHttpRequest()
      const token = localStorage.getItem('access_token')

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const item = uploadingFiles.value.find(f => f.id === tempId)
          if (item) item.progress = Math.round((e.loaded / e.total) * 100)
        }
      })

      xhr.addEventListener('load', async () => {
        uploadingFiles.value = uploadingFiles.value.filter(f => f.id !== tempId)
        if (xhr.status === 201) {
          const mat = JSON.parse(xhr.responseText) as CourseMaterial
          materials.value.unshift(mat)
          _startPollingIfNeeded()
          resolve()
        } else {
          const detail = _parseErrorDetail(xhr.responseText)
          reject(new Error(detail))
        }
      })

      xhr.addEventListener('error', () => {
        uploadingFiles.value = uploadingFiles.value.filter(f => f.id !== tempId)
        reject(new Error('网络错误，上传失败。'))
      })

      const baseURL = (client.defaults.baseURL ?? '/api').replace(/\/$/, '')
      xhr.open('POST', `${baseURL}/courses/${courseId.value}/materials`)
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      xhr.send(formData)
    })
  }

  async function deleteMaterial(matId: number) {
    if (!courseId.value) return
    await client.delete(`/courses/${courseId.value}/materials/${matId}`)
    materials.value = materials.value.filter(m => m.id !== matId)
  }

  // ── AI Generation ─────────────────────────────────────────────
  async function generateUnits(opts: Partial<GenerateOptions> = {}) {
    if (!courseId.value) return
    generating.value       = true
    generateWarnings.value = []
    error.value            = null

    try {
      const { data } = await client.post<GenerateUnitsResponse>(
        `/courses/${courseId.value}/generate-units`,
        {
          material_ids:       opts.materialIds     ?? [],
          target_unit_count:  opts.targetUnitCount ?? 0,
          overwrite:          opts.overwrite       ?? false,
        },
      )
      generateWarnings.value = data.warnings
      // Merge new units with existing (overwrite replaces drafts)
      if (opts.overwrite) {
        units.value = [
          ...units.value.filter(u => u.status !== 'draft'),
          ...data.units,
        ].sort((a, b) => a.unit_index - b.unit_index)
      } else {
        const newIds = new Set(data.units.map(u => u.id))
        units.value = [
          ...units.value.filter(u => !newIds.has(u.id)),
          ...data.units,
        ].sort((a, b) => a.unit_index - b.unit_index)
      }
    } catch (e: any) {
      error.value = e?.response?.data?.detail ?? 'AI 课时切分失败，请稍后重试。'
      throw e
    } finally {
      generating.value = false
    }
  }

  // ── Learning Units ────────────────────────────────────────────
  async function fetchUnits(statusFilter?: string) {
    if (!courseId.value) return
    loadingUnits.value = true
    try {
      const params = statusFilter ? { status: statusFilter } : {}
      const { data } = await client.get<{ units: LearningUnit[]; total: number }>(
        `/courses/${courseId.value}/units`,
        { params },
      )
      units.value = data.units
    } finally {
      loadingUnits.value = false
    }
  }

  async function updateUnit(unitId: number, patch: Partial<LearningUnit>) {
    if (!courseId.value) return
    const { data } = await client.patch<LearningUnit>(
      `/courses/${courseId.value}/units/${unitId}`,
      patch,
    )
    const idx = units.value.findIndex(u => u.id === unitId)
    if (idx !== -1) units.value[idx] = data
    return data
  }

  async function publishUnit(unitId: number) {
    return updateUnitStatus(unitId, 'ready')
  }

  async function archiveUnit(unitId: number) {
    return updateUnitStatus(unitId, 'archived')
  }

  async function updateUnitStatus(unitId: number, status: string) {
    if (!courseId.value) return
    const { data } = await client.patch<LearningUnit>(
      `/courses/${courseId.value}/units/${unitId}/status`,
      null,
      { params: { status } },
    )
    const idx = units.value.findIndex(u => u.id === unitId)
    if (idx !== -1) units.value[idx] = data
    return data
  }

  async function deleteUnit(unitId: number) {
    if (!courseId.value) return
    await client.delete(`/courses/${courseId.value}/units/${unitId}`)
    units.value = units.value.filter(u => u.id !== unitId)
  }

  // ── Polling for extraction status ─────────────────────────────
  function _startPollingIfNeeded() {
    if (pendingMaterials.value.length > 0 && !pollingTimer) {
      pollingTimer = setInterval(async () => {
        await fetchMaterials()
        if (pendingMaterials.value.length === 0) _stopPolling()
      }, 3000)
    }
  }

  function _stopPolling() {
    if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null }
  }

  function _parseErrorDetail(body: string): string {
    try {
      return JSON.parse(body)?.detail ?? '上传失败'
    } catch {
      return '上传失败'
    }
  }

  return {
    // State
    courseId, materials, units, uploadingFiles,
    generating, generateWarnings, loadingMaterials, loadingUnits, error,
    // Computed
    readyMaterials, pendingMaterials, draftUnits, readyUnits, totalEstimatedMin,
    // Actions
    init, dispose,
    fetchMaterials, uploadMaterial, deleteMaterial,
    generateUnits,
    fetchUnits, updateUnit, publishUnit, archiveUnit, deleteUnit,
  }
})
