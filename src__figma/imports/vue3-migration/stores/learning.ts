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

  // ── Relationship ─────────────────────────────────────────────
  const relationshipStage = ref<RelationshipStage>('stranger')
  const pendingStageEvent = ref<RelationshipStage | null>(null)
  const stageSpecialLine  = ref('')

  // ── Progress ─────────────────────────────────────────────────
  const masteryPercent   = ref(0)

  // ── Knowledge graph ──────────────────────────────────────────
  const knowledgeGraph   = ref<KnowledgeGraph>({ nodes: [], edges: [] })

  // ── Loading / error ──────────────────────────────────────────
  const thinking         = ref(false)
  const loadError        = ref<string | null>(null)

  // ── Sage name (from teacher_persona string) ───────────────────
  const _sageName = ref('知者')
  const sageName  = computed(() => _sageName.value)

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

      // Normal start
      const { data } = await client.post<StartLearningResponse>(
        `/courses/${_courseId}/start`,
      )
      _applyStartResponse(data)
      sessionId.value = data.session_id

      // Show greeting as first speaking turn
      messages.value = []
      pushSpeaking(data.greeting)

    } catch (e: any) {
      loadError.value = e?.response?.data?.detail ?? '会话启动失败'
    }
  }

  /** Apply fields from StartLearningResponse — adapted §5 */
  function _applyStartResponse(data: StartLearningResponse) {
    if (!sessionId.value) sessionId.value = data.session_id

    // §5: teacher_persona is a plain string (the persona name), not an object
    _sageName.value = typeof data.teacher_persona === 'string' && data.teacher_persona
      ? data.teacher_persona
      : '知者'

    // sage_sprites / character_sprites are aliases
    sageSprites.value     = data.sage_sprites ?? data.character_sprites ?? {}
    travelerSprites.value = data.traveler_sprites ?? {}
    sceneBackground.value = data.scenes?.background ?? ''
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
      const { data } = await client.post<ChatResponse>(
        `/courses/${courseId.value}/chat`,
        payload,
      )

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
      if (data.type === 'choice') {
        pushChoices(data.reply, data.choices ?? [])
      } else {
        // type === 'text' or 'tool_request'
        pushSpeaking(data.reply)
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
    knowledgeGraph.value    = { nodes: [], edges: [] }
    thinking.value          = false
    loadError.value         = null
    _sageName.value         = '知者'
  }

  return {
    sessionId, courseId, worldId,
    sageSprites, travelerSprites, sceneBackground,
    messages, mode, currentText, currentChoices,
    currentEmotion, sageExpression, sageJumpKey, travelerJumpKey,
    relationshipStage, pendingStageEvent, stageSpecialLine,
    masteryPercent, knowledgeGraph, thinking, loadError,
    sageName,
    startSession, loadHistory, sendMessage, chooseOption,
    fetchKnowledgeGraph, createCheckpoint, fetchCheckpoints,
    dismissStageEvent, reset,
  }
})
