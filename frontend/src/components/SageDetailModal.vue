<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="detail-modal">
      <!-- Header -->
      <div class="detail-header">
        <div class="detail-avatar" :style="{ background: character?.color || 'rgba(255,215,0,0.2)' }">
          {{ character?.symbol || character?.name?.[0] || '?' }}
        </div>
        <div class="detail-identity">
          <div class="detail-name">{{ character?.name || '未命名' }}</div>
          <div class="detail-title">{{ character?.title || (isSage ? '知者' : '旅者') }}</div>
          <div v-if="relationshipStage" class="detail-stage">
            <span class="stage-badge">{{ relationshipStage }}</span>
          </div>
        </div>
        <button class="close-btn" @click="$emit('close')">✕</button>
      </div>

      <!-- Body -->
      <div class="detail-body">
        <!-- Background -->
        <div v-if="fullCharacter?.background" class="detail-section">
          <div class="section-label">背景故事</div>
          <div class="section-text">{{ fullCharacter.background }}</div>
        </div>

        <!-- Personality -->
        <div v-if="fullCharacter?.personality" class="detail-section">
          <div class="section-label">性格</div>
          <div class="section-text">{{ fullCharacter.personality }}</div>
        </div>

        <!-- Speech Style -->
        <div v-if="fullCharacter?.speech_style" class="detail-section">
          <div class="section-label">说话风格</div>
          <div class="section-text">{{ fullCharacter.speech_style }}</div>
        </div>

        <!-- Traits (5-dimension) -->
        <div v-if="traits && Object.keys(traits).length" class="detail-section">
          <div class="section-label">性格参数</div>
          <div class="traits-grid">
            <div v-for="(label, key) in traitLabels" :key="key" class="trait-row">
              <span class="trait-name">{{ label }}</span>
              <div class="trait-bar">
                <div class="trait-fill" :style="{ width: `${(traits[key] || 5) * 10}%` }"></div>
              </div>
              <span class="trait-value">{{ traits[key] || 5 }}</span>
            </div>
          </div>
        </div>

        <!-- Tags -->
        <div v-if="fullCharacter?.tags?.length" class="detail-section">
          <div class="section-label">标签</div>
          <div class="tags-row">
            <span v-for="tag in fullCharacter.tags" :key="tag" class="tag-chip">{{ tag }}</span>
          </div>
        </div>

        <!-- Relationship (好感度) -->
        <div v-if="relationshipDimensions" class="detail-section">
          <div class="section-label">关系维度</div>
          <div class="traits-grid">
            <div v-for="(label, key) in relLabels" :key="key" class="trait-row">
              <span class="trait-name">{{ label }}</span>
              <div class="trait-bar">
                <div class="trait-fill rel-fill" :style="{ width: `${(relationshipDimensions[key] || 0) * 100}%` }"></div>
              </div>
              <span class="trait-value">{{ Math.round((relationshipDimensions[key] || 0) * 100) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="detail-footer">
        <button class="btn-edit" @click="character && $emit('edit', character)">
          ✎ 编辑
        </button>
        <button class="btn-close-action" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { characterApi } from '@/api/character'

interface CharacterBasic {
  id: number
  name: string
  title?: string
  type?: string
  color?: string
  symbol?: string
}

const props = defineProps<{
  show: boolean
  character: CharacterBasic | null
  relationship?: {
    stage?: string
    dimensions?: Record<string, number>
  } | null
}>()

defineEmits<{
  close: []
  edit: [character: CharacterBasic]
}>()

const STAGE_LABELS: Record<string, string> = {
  stranger: '初识',
  acquaintance: '相识',
  friend: '朋友',
  mentor: '导师',
  partner: '伙伴',
}

const traitLabels: Record<string, string> = {
  strictness: '严厉',
  pace: '节奏',
  questioning: '追问',
  warmth: '温暖',
  humor: '幽默',
}

const relLabels: Record<string, string> = {
  trust: '信任',
  familiarity: '熟悉',
  respect: '尊敬',
  comfort: '舒适',
}

const fullCharacter = ref<any>(null)

const isSage = computed(() => props.character?.type === 'sage')
const traits = computed(() => fullCharacter.value?.traits || {})
const relationshipStage = computed(() => {
  const stage = props.relationship?.stage
  return stage ? STAGE_LABELS[stage] || stage : null
})
const relationshipDimensions = computed(() => {
  const dims = props.relationship?.dimensions
  return dims && Object.keys(dims).length > 0 ? dims : null
})

watch(() => props.show, async (newVal) => {
  if (newVal && props.character?.id) {
    try {
      fullCharacter.value = await characterApi.get(props.character.id)
    } catch {
      fullCharacter.value = props.character
    }
  } else {
    fullCharacter.value = null
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.detail-modal {
  width: 520px;
  max-width: 92vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background: rgba(12, 12, 30, 0.98);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

/* Header */
.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 24px 16px;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
}

.detail-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  border: 2px solid rgba(255, 215, 0, 0.4);
  flex-shrink: 0;
}

.detail-identity {
  flex: 1;
}

.detail-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 20px;
  color: #ffd700;
  letter-spacing: 2px;
  margin-bottom: 4px;
}

.detail-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 6px;
}

.stage-badge {
  display: inline-block;
  padding: 2px 10px;
  font-size: 11px;
  color: #4adf6a;
  background: rgba(74, 223, 106, 0.12);
  border: 1px solid rgba(74, 223, 106, 0.25);
  border-radius: 10px;
  letter-spacing: 1px;
}

.close-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.2s;
}

.close-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

/* Body */
.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.detail-section {
  margin-bottom: 20px;
}

.section-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 215, 0, 0.7);
  letter-spacing: 2px;
  margin-bottom: 8px;
  text-transform: uppercase;
}

.section-text {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.75);
  line-height: 1.7;
}

/* Traits */
.traits-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.trait-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.trait-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  width: 40px;
  flex-shrink: 0;
}

.trait-bar {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.trait-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #f59e0b);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.trait-fill.rel-fill {
  background: linear-gradient(90deg, #60a5fa, #4adf6a);
}

.trait-value {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  width: 36px;
  text-align: right;
  flex-shrink: 0;
}

/* Tags */
.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-chip {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 215, 0, 0.7);
  background: rgba(255, 215, 0, 0.08);
  border: 1px solid rgba(255, 215, 0, 0.15);
  padding: 2px 10px;
  border-radius: 10px;
}

/* Footer */
.detail-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 215, 0, 0.1);
}

.btn-edit {
  padding: 8px 20px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: #0a0a1e;
  background: rgba(255, 215, 0, 0.9);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 1px;
}

.btn-edit:hover {
  background: #ffd700;
}

.btn-close-action {
  padding: 8px 20px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 1px;
}

.btn-close-action:hover {
  border-color: rgba(255, 255, 255, 0.4);
  color: #fff;
}
</style>