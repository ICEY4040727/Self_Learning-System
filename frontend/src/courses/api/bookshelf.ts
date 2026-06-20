/**
 * Bookshelf API Module
 * 用户级书架教材库 — 上传/列表/删除/关联课程
 */
import client from '@/shared/api/client'
import { TEXTBOOK_UPLOAD_TIMEOUT_MS } from '@/courses/constants/textbooks'

export interface BookshelfItem {
  id: number
  filename: string
  file_size: number | null
  content_type: string | null
  page_count: number | null
  status: string
  error_message: string | null
  is_usable: boolean
  title: string | null
  created_at: string | null
  linked_course_ids?: number[]
}

export const bookshelfApi = {
  /**
   * 上传教材到书架
   */
  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/bookshelf/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: TEXTBOOK_UPLOAD_TIMEOUT_MS,
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    }).then(res => res.data as BookshelfItem)
  },

  /**
   * 列出书架所有教材
   */
  list: () =>
    client.get('/bookshelf').then(res => res.data as BookshelfItem[]),

  /**
   * 从书架删除教材
   */
  delete: (libraryId: number) =>
    client.delete(`/bookshelf/${libraryId}`).then(() => undefined),

  /**
   * 将书架教材关联到课程
   */
  linkToCourse: (courseId: number, libraryId: number) =>
    client.post(`/courses/${courseId}/link-textbook`, { library_id: libraryId })
      .then(res => res.data),

  /**
   * 批量将书架教材关联到课程
   */
  batchLinkToCourse: (courseId: number, libraryIds: number[]) =>
    client.post(`/courses/batch-link-textbooks?course_id=${courseId}`, libraryIds)
      .then(res => res.data),
}

