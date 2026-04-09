/**
 * 存档导入/导出 composable
 * v1.0 #193
 */
import client from '@/api/client'

export interface CheckpointExportData {
  version: string
  save_name: string
  world_id: number
  session_id?: number
  message_index: number
  created_at: string
  stage?: string
  mastery_percent?: number
  preview_text?: string
  session_snapshot?: Record<string, unknown>
}

export function useCheckpointExport() {
  /**
   * 导出存档为 JSON 文件
   */
  async function exportCheckpoint(checkpointId: number, saveName: string): Promise<void> {
    const { data } = await client.get<CheckpointExportData>(
      `/checkpoints/${checkpointId}/export`
    )
    
    // 生成文件名
    const timestamp = new Date().toISOString().slice(0, 10)
    const filename = `${saveName}_${timestamp}.json`
    
    // 创建 Blob 并下载
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  /**
   * 导入存档 JSON 文件
   */
  async function importCheckpoint(file: File): Promise<{ id: number; save_name: string }> {
    const text = await file.text()
    const data = JSON.parse(text) as CheckpointExportData
    
    // 验证必要字段
    if (!data.version || !data.save_name || !data.world_id) {
      throw new Error('无效的存档文件')
    }
    
    const payload = {
      version: data.version,
      save_name: data.save_name,
      world_id: data.world_id,
      session_id: data.session_id,
      message_index: data.message_index,
      stage: data.stage,
      mastery_percent: data.mastery_percent,
      preview_text: data.preview_text,
      session_snapshot: data.session_snapshot,
    }
    
    const { data: result } = await client.post<{ id: number; save_name: string }>(
      '/checkpoints/import',
      payload
    )
    
    return result
  }

  return {
    exportCheckpoint,
    importCheckpoint,
  }
}
