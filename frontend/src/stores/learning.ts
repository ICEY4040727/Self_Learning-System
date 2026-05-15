/**
 * stores/learning.ts
 * ──────────────────────────────────────────────────────────────
 * Contract adaptations applied (vue3_migration_contract_adaptation.md):
 *
 *  §4  Chat request body: { message } not { content }
 *  §4  ChatResponse.emotion is dict|null, extract emotion_type for display
 *  §4  ChatResponse.type includes 'choice' (not just 'choices' / 'text')
 *  §4  ChatResponse.choices is optional, only present when type='choice'
 *  §5  StartLearningResponse.teacher_persona is string (name), not object
 *  §5  History endpoint: only {id,sender_type,content,timestamp} — no emotion/expression_hint
 *  §6  Branch response: consume session_id + course_id + world_id to rebuild full state
 * ──────────────────────────────────────────────────────────────
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import client from '@/api/client'
import type {
  Message, HistoryMessage,
  ChatRequest, ChatResponse,
  StartLearningResponse, BranchResponse,
  KnowledgeGraph, Checkpoint,
  RelationshipStage, Expression, Sprites,
} from '@/types'
import { EMOTION_TYPE_ZH } from '@/types'

export const useLearningStore = defineStore('learning', () => {
  // ── Session ──────────────────────────────────────────────────
  const sessionId        = ref<number | null>(null)
  const courseId         = ref<number | null>(null)
  const worldId          = ref<number | null>(null)
  const sageSprites      = ref<Sprites>({})
  const travelerSprites  = ref<Sprites>({})
  const sceneBackground  = ref<string>('')

  // ── Dialogue state ───────────────────────────────────────────
  const messages         = ref<Message[]>([])
  const mode             = ref<'speaking' | 'input' | 'choices' | 'waiting'>('speaking')
  const currentText      = ref('')
  const currentChoices   = ref<string[]>([])
  const currentEmotion   = ref('中性')
  const sageExpression   = ref<Expression>('default')
  const sageJumpKey      = ref(0)
  const travelerJumpKey  = ref(0)
  const textKey          = ref(0)   // increments every time currentText changes, ensures DialogBox re-triggers even with same text

  // ── Relationship ─────────────────────────────────────────────
  const relationshipStage = ref<RelationshipStage>('stranger')
  const pendingStageEvent = ref<RelationshipStage | null>(null)
  const stageSpecialLine  = ref('')

  // ── Progress ─────────────────────────────────────────────────
  const masteryPercent   = ref(0)

  // ── Phase 3: Narrative & Achievements ────────────────────────
  const narrativeEvents  = ref<Array<{ event_type: string; description: string; scene?: string }>>([])
  const newAchievements  = ref<Array<{ id: string; name: string; description: string; icon?: string }>>([])

  // ── Knowledge graph ──────────────────────────────────────────
  const knowledgeGraph   = ref<KnowledgeGraph>({ nodes: [], edges: [] })

  // ── Loading / error ──────────────────────────────────────────
  const thinking         = ref(false)
  const loadError        = ref<string | null>(null)

  // ── Sage data (from start response) ────────────────────────────
  const _sageName = ref('知者')
  const sageName  = computed(() => _sageName.value)
  const sageTitle = ref('智者')
  const sageSymbol = ref('知')
  const sageAvatar = ref<string | null>(null)
  const sageColor = ref('#4c1d95')
  const sageAccentColor = ref('#7c3aed')

  // ── Utility ────────────────────────────────────────────────────
  /** 将 hex 颜色亮度调高（factor 0~1） */
  function _lightenColor(hex: string, factor: number): string {
    const m = hex.match(/^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i)
    if (!m) return hex
    const r = Math.min(255, Math.round(parseInt(m[1], 16) + (255 - parseInt(m[1], 16)) * factor))
    const g = Math.min(255, Math.round(parseInt(m[2], 16) + (255 - parseInt(m[2], 16)) * factor))
    const b = Math.min(255, Math.round(parseInt(m[3], 16) + (255 - parseInt(m[3], 16)) * factor))
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
  }

  // ── Start / resume session ────────────────────────────────────
  /**
   * Adapted §5, §6:
   *  - If checkpointId given: branch first → get new session_id/course_id/world_id
   *  - start endpoint: teacher_persona is now a plain string (name)
   *  - scenes come directly from data.scenes
   */
  async function startSession(
    _courseId: number,
    _worldId: number,
    checkpointId?: number,
    sageId?: number,
  ) {
    courseId.value  = _courseId
    worldId.value   = _worldId
    loadError.value = null

    try {
      // §6 — If branching, get new IDs from branch response first
      if (checkpointId) {
        const { data: branch } = await client.post<BranchResponse>(
          `/checkpoints/${checkpointId}/branch`,
        )
        // Consume all three IDs — avoids stale state on nested branches
        sessionId.value = branch.session_id
        courseId.value  = branch.course_id   // may differ from caller arg
        worldId.value   = branch.world_id    // may differ from caller arg

        // Then start with the existing session already set
        const { data } = await client.post<StartLearningResponse>(
          `/courses/${branch.course_id}/start`,
        )
        _applyStartResponse(data)
        await loadHistory()   // restore branch history — don't show greeting
        return
      }

      // Normal start — pass sage_id so backend knows which sage to use
      console.log('[learning store] startSession called:', { _courseId, _worldId, sageId })
      const { data } = await client.post<StartLearningResponse>(
        `/courses/${_courseId}/start`,
        sageId ? { sage_id: sageId } : {},
      )
      console.log('[learning store] start response:', {
        session_id: data.session_id,
        is_new: data.is_new,
        greeting: data.greeting?.substring(0, 50),
        sage: data.sage?.name,
      })
      _applyStartResponse(data)
      sessionId.value = data.session_id

      if (data.is_new) {
        // 新 session：显示 greeting
        messages.value = []
        console.log('[learning store] pushing greeting, mode before:', mode.value)
        pushSpeaking(data.greeting || '你好，今天我们开始学习吧。')
        console.log('[learning store] pushed greeting, mode after:', mode.value, 'currentText:', currentText.value?.substring(0, 50))
      } else {
        // 恢复已有 session：加载历史对话
        await loadHistory()
      }

    } catch (e: any) {
      console.error('[learning store] startSession error:', e?.response?.status, e?.response?.data)
      loadError.value = e?.response?.data?.detail ?? '会话启动失败'
    }
  }

  /** Apply fields from StartLearningResponse — adapted §5 */
  function _applyStartResponse(data: StartLearningResponse) {
    if (!sessionId.value) sessionId.value = data.session_id

    // §5: teacher_persona is a plain string (the persona name), not an object
    _sageName.value = data.sage?.name
      || (typeof data.teacher_persona === 'string' && data.teacher_persona)
      || '知者'

    // 从 sage 字段获取完整角色数据（不再硬编码）
    if (data.sage) {
      sageTitle.value     = data.sage.title || '智者'
      sageSymbol.value    = data.sage.symbol || '知'
      sageAvatar.value    = data.sage.avatar || null
      sageColor.value     = data.sage.color || '#4c1d95'
      sageAccentColor.value = _lightenColor(sageColor.value, 0.35)
    }

    // sage_sprites: 优先用 sage.sprites，fallback 到旧字段
    sageSprites.value     = data.sage?.sprites ?? data.sage_sprites ?? data.character_sprites ?? {}
    travelerSprites.value = data.traveler_sprites ?? {}
    sceneBackground.value = data.scenes?.background_picture ?? data.scenes?.background ?? ''
    relationshipStage.value = data.relationship_stage
  }

  // ── Load history (resume) ─────────────────────────────────────
  /**
   * Adapted §5:
   *   History endpoint only returns {id, sender_type, content, timestamp}.
   *   No emotion or expression_hint. Map directly to Message without extras.
   */
  async function loadHistory() {
    if (!sessionId.value) return
    const { data } = await client.get<HistoryMessage[]>(
      `/sessions/${sessionId.value}/history`,
    )
    messages.value = data.map<Message>(m => ({
      id:          m.id,
      sender_type: m.sender_type,
      content:     m.content,
      timestamp:   m.timestamp,
      // emotion / expression_hint intentionally absent — history doesn't carry them
    }))

    // After restoring history, put UI into input mode
    setMode('input')
  }

  // ── Send message ──────────────────────────────────────────────
  /**
   * Adapted §4:
   *   Request body: { message } (field name matches backend ChatRequest.message)
   *   ChatResponse.emotion is a dict: extract .emotion_type for display
   *   ChatResponse.type: handle 'choice' (not just 'text'/'choices')
   */
  async function sendMessage(content: string) {
    if (!courseId.value || thinking.value) return

    const userMsg: Message = {
      id:          Date.now(),
      sender_type: 'user',
      content,
      timestamp:   new Date().toISOString(),
    }
    messages.value.push(userMsg)
    setMode('waiting')
    thinking.value = true

    try {
      // §4: field is `message`, not `content`
      const payload: ChatRequest = { message: content }
      console.log('[learning store] sendMessage: courseId=', courseId.value, 'sessionId=', sessionId.value)
      const { data } = await client.post<ChatResponse>(
        `/courses/${courseId.value}/chat`,
        payload,
      )
      console.log('[learning store] chat response:', data.type, data.reply?.substring(0, 50))

      // §4: emotion is dict|null — extract emotion_type for Chinese display label
      if (data.emotion) {
        const emotionType = (data.emotion as Record<string, unknown>).emotion_type as string | undefined
        currentEmotion.value = (emotionType && EMOTION_TYPE_ZH[emotionType])
          ? EMOTION_TYPE_ZH[emotionType]
          : (emotionType ?? '中性')
      }

      // Update expression
      if (data.expression_hint) {
        sageExpression.value = data.expression_hint
        sageJumpKey.value++
      }

      // Update relationship
      if (data.relationship_stage) {
        const oldStage = relationshipStage.value
        const newStage = data.relationship_stage
        relationshipStage.value = newStage

        const events = data.relationship_events ?? []
        const upgradeEvent = events.find(e => e.type === 'stage_change')
        if (upgradeEvent && oldStage !== newStage) {
          pendingStageEvent.value = newStage
          stageSpecialLine.value  = upgradeEvent.special_dialogue ?? ''
        }
      }

      // Update mastery
      masteryPercent.value = Math.min(100, masteryPercent.value + 3)

      // §4: type can be 'choice' (singular), not 'choices'
      if ((data as any).type === 'error') {
        // Error from backend (e.g. no API key) — show as sage dialogue but stay in input mode
        messages.value.push({
          id:          Date.now(),
          sender_type: 'assistant',
          content:     data.reply,
          timestamp:   new Date().toISOString(),
          emotion:     '中性',
        })
        currentText.value    = data.reply
        currentChoices.value = []
        textKey.value++
        // Show the error text briefly in speaking mode, then user clicks to dismiss
        setMode('speaking')
      } else if (data.type === 'choice') {
        pushChoices(data.reply, data.choices ?? [])
      } else {
        // type === 'text' or 'tool_request'
        pushSpeaking(data.reply)
      }

      // Issue #192: 通知 memory facts drawer 刷新（如果有新提取的记忆）
      if (data.memory_extracted_count && data.memory_extracted_count > 0) {
        window.dispatchEvent(new CustomEvent('memory:fresh', {
          detail: { count: data.memory_extracted_count }
        }))
      }

      // Phase 3: Handle narrative events
      if (data.narrative_events && data.narrative_events.length > 0) {
        narrativeEvents.value.push(...data.narrative_events)
      }

      // Phase 3: Handle new achievements
      if (data.new_achievements && data.new_achievements.length > 0) {
        newAchievements.value.push(...data.new_achievements)
      }

    } catch (e: any) {
      const detail = e?.response?.data?.detail ?? '连接错误，请检查网络和 API Key 配置'
      pushSpeaking(`（${detail}）`)
      setMode('input')
    } finally {
      thinking.value = false
    }
  }

  async function chooseOption(choice: string) {
    await sendMessage(choice)
  }

  // ── Knowledge graph ───────────────────────────────────────────
  async function fetchKnowledgeGraph() {
    if (!worldId.value) return
    try {
      const params = sessionId.value ? { session_id: sessionId.value } : undefined
      const { data } = await client.get<KnowledgeGraph>(
        `/worlds/${worldId.value}/knowledge-graph`,
        { params },
      )
      knowledgeGraph.value = data
    } catch {}
  }

  // ── Checkpoints ───────────────────────────────────────────────
  async function createCheckpoint(saveName: string): Promise<Checkpoint | null> {
    if (!worldId.value || !sessionId.value) return null
    const { data } = await client.post<Checkpoint>('/checkpoints', {
      world_id:      worldId.value,
      session_id:    sessionId.value,
      save_name:     saveName,
      message_index: messages.value.length,
    })
    return data
  }

  async function fetchCheckpoints(): Promise<Checkpoint[]> {
    if (!worldId.value) return []
    const { data } = await client.get<Checkpoint[]>(
      `/worlds/${worldId.value}/checkpoints`,
    )
    return data
  }

  // ── Internal helpers ──────────────────────────────────────────
  function pushSpeaking(text: string) {
    messages.value.push({
      id:          Date.now(),
      sender_type: 'assistant',
      content:     text,
      timestamp:   new Date().toISOString(),
      emotion:     currentEmotion.value,
      expression_hint: sageExpression.value,
    })
    currentText.value    = text
    currentChoices.value = []
    textKey.value++
    setMode('speaking')
  }

  function pushChoices(question: string, choices: string[]) {
    messages.value.push({
      id:          Date.now(),
      sender_type: 'assistant',
      content:     question,
      timestamp:   new Date().toISOString(),
      emotion:     currentEmotion.value,
    })
    currentText.value    = question
    currentChoices.value = choices
    textKey.value++
    setMode('choices')
  }

  function setMode(m: typeof mode.value) {
    mode.value = m
    if (m === 'input')                      travelerJumpKey.value++
    if (m === 'speaking' || m === 'choices') sageJumpKey.value++
  }

  function dismissStageEvent() {
    pendingStageEvent.value = null
    stageSpecialLine.value  = ''
    setMode('input')
  }

  /** 通知后端关闭 session（静默失败不影响流程） */
  async function endSession() {
    if (!sessionId.value) return
    try {
      await client.post(`/sessions/${sessionId.value}/end`)
    } catch { /* 静默 */ }
  }

  function reset() {
    sessionId.value         = null
    courseId.value          = null
    worldId.value           = null
    sageSprites.value       = {}
    travelerSprites.value   = {}
    sceneBackground.value   = ''
    messages.value          = []
    mode.value              = 'speaking'
    currentText.value       = ''
    currentChoices.value    = []
    currentEmotion.value    = '中性'
    sageExpression.value    = 'default'
    sageJumpKey.value       = 0
    travelerJumpKey.value   = 0
    relationshipStage.value = 'stranger'
    pendingStageEvent.value = null
    stageSpecialLine.value  = ''
    masteryPercent.value    = 0
    narrativeEvents.value   = []
    newAchievements.value   = []
    knowledgeGraph.value    = { nodes: [], edges: [] }
    thinking.value          = false
    loadError.value         = null
    _sageName.value         = '知者'
  }

  return {
    sessionId, courseId, worldId,
    sageSprites, travelerSprites, sceneBackground,
    messages, mode, currentText, currentChoices,
    currentEmotion, sageExpression, sageJumpKey, travelerJumpKey, textKey,
    relationshipStage, pendingStageEvent, stageSpecialLine,
    masteryPercent, narrativeEvents, newAchievements, knowledgeGraph, thinking, loadError,
    sageName, sageTitle, sageSymbol, sageAvatar, sageColor, sageAccentColor,
    startSession, endSession, loadHistory, sendMessage, chooseOption,
    fetchKnowledgeGraph, createCheckpoint, fetchCheckpoints,
    dismissStageEvent, setMode, reset,
  }
})

