/**
 * Course API Module
 * Issue #29: 统一 API 调用层
 */
import client from './client'

export const courseApi = {
  /**
   * 获取课程详情
   */
  get: (courseId: number) =>
    client.get(`/courses/${courseId}`).then(res => res.data),

  /**
   * 获取课程的导师列表
   */
  getSages: (courseId: number) =>
    client.get(`/courses/${courseId}/sages`).then(res => res.data),

  /**
   * 获取课程的会话列表
   */
  getSessions: (courseId: number) =>
    client.get(`/courses/${courseId}/sessions`).then(res => res.data),

  /**
   * 获取课程的记忆事实
   */
  getMemoryFacts: (courseId: number, statsOnly = true) =>
    client.get(`/courses/${courseId}/memory-facts?stats_only=${statsOnly}`).then(res => res.data),

  /**
   * 开始学习会话
   */
  start: (courseId: number, sageId: number) =>
    client.post(`/courses/${courseId}/start`, { sage_id: sageId }).then(res => res.data),

  // ── Textbook / Course Generation (Phase 2C) ──────────────────

  /**
   * 上传教材到课程
   */
  uploadTextbook: (courseId: number, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return client.post(`/courses/${courseId}/textbooks`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    }).then(res => res.data)
  },

  /**
   * 列出课程的教材
   */
  listTextbooks: (courseId: number) =>
    client.get(`/courses/${courseId}/textbooks`).then(res => res.data),

  /**
   * 删除教材 (returns void — backend responds 204)
   */
  deleteTextbook: (courseId: number, textbookId: number) =>
    client.delete(`/courses/${courseId}/textbooks/${textbookId}`).then(() => undefined),

  /**
   * 基于教材生成课程结构
   * Backend rejects (409) if generated_lessons already exist — call
   * clearGeneratedContent first if you want to regenerate.
   */
  generateCourse: (courseId: number, customInstructions?: string) =>
    client.post(`/courses/${courseId}/generate`,
      {
        course_id: courseId,
        ...(customInstructions ? { custom_instructions: customInstructions } : {}),
      },
      { timeout: 120_000 }, // AI 生成可能较慢
    ).then(res => res.data),

  /**
   * 清空已生成的课程内容 (overview / lessons / concept_map + progress).
   * Used to unlock /generate when the previous output was unsatisfactory.
   * Backend responds 204.
   */
  clearGeneratedContent: (courseId: number) =>
    client.delete(`/courses/${courseId}/generated`).then(() => undefined),

  /** 删除课程 */
  deleteCourse: (courseId: number) =>
    client.delete(`/courses/${courseId}`).then(() => undefined),

  /**
   * 获取课程的章节列表（从 LessonPlan 表）
   */
  listLessons: (courseId: number) =>
    client.get(`/courses/${courseId}/lessons`).then(res => res.data),

  /**
   * 获取课程进度（课程列表）
   */
  getProgress: (courseId: number) =>
    client.get(`/courses/${courseId}/progress`).then(res => res.data),

  /**
   * 推进到下一课
   */
  advanceLesson: (courseId: number) =>
    client.post(`/courses/${courseId}/advance`).then(res => res.data),

  /**
   * 获取课程精通度
   */
  getMastery: (courseId: number) =>
    client.get(`/courses/${courseId}/mastery`).then(res => res.data),

  /**
   * 获取学习者画像 (dimension_scores, strengths, weaknesses, learning_stats)
   */
  getLearnerProfile: (worldId: number) =>
    client.get(`/worlds/${worldId}/learner_profile`).then(res => res.data),

  /**
   * AI 生成课程简介
   * 基于学科领域、课程名称、学习水平等生成一段课程描述
   */
  generateDescription: (params: {
    domain: string
    course_name?: string
    current_level?: string
    target_level?: string
  }): Promise<{ description: string }> =>
    client.post('/courses/generate-description', params).then(res => res.data),
}

