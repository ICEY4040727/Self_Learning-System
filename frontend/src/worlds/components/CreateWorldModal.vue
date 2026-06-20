<template>
  <Transition name="modal-fade">
    <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-box">
        <div class="modal-header">
          <div class="modal-subtitle">NEW WORLD</div>
          <div class="modal-title">创 建 世 界 壳</div>
          <div class="gold-line"></div>
        </div>

        <div class="step-header">
          <div class="step-meta">
            <div class="step-name">{{ stepTitle }}</div>
            <div class="step-index">{{ stepIndex + 1 }}/5</div>
          </div>
          <div class="step-progress">
            <div class="step-progress-fill" :style="{ width: `${((stepIndex + 1) / 5) * 100}%` }"></div>
          </div>
          <p class="step-hint">{{ stepHint }}</p>
        </div>

        <div class="modal-body">
          <div class="wizard-panel">
            <template v-if="uiState.currentStep === 'space'">
              <div class="field-group">
                <label class="field-label">世 界 名 种 子</label>
                <input
                  v-model="wizardDraft.world_name_seed"
                  type="text"
                  class="galgame-input"
                  maxlength="24"
                  placeholder="如果你脑中已经有名字，可以先写在这里"
                />
              </div>

              <div class="field-group">
                <label class="field-label">这 个 世 界 最 像 什 么 地 方 <span class="required">*</span></label>
                <div class="option-grid">
                  <button
                    v-for="option in SPACE_ANCHOR_OPTIONS"
                    :key="option"
                    type="button"
                    class="option-card"
                    :class="{ selected: wizardDraft.space_anchor === option }"
                    @click="wizardDraft.space_anchor = option"
                  >
                    {{ option }}
                  </button>
                </div>
              </div>

              <div class="field-group">
                <label class="field-label">这 个 地 方 最 吸 引 你 的 是 什 么</label>
                <textarea
                  v-model="wizardDraft.space_reason"
                  class="galgame-input"
                  rows="3"
                  maxlength="40"
                  placeholder="例如：安静、稳定、适合长期钻研"
                ></textarea>
              </div>
            </template>

            <template v-else-if="uiState.currentStep === 'learning'">
              <div class="field-group">
                <label class="field-label">学 习 在 这 里 更 像 什 么 <span class="required">*</span></label>
                <div class="option-grid">
                  <button
                    v-for="option in LEARNING_MODE_OPTIONS"
                    :key="option"
                    type="button"
                    class="option-card"
                    :class="{ selected: wizardDraft.learning_mode_preset === option }"
                    @click="wizardDraft.learning_mode_preset = option"
                  >
                    {{ option }}
                  </button>
                </div>
                <button type="button" class="text-link" @click="toggleCustomField('learningMode')">
                  {{ uiState.showLearningModeCustom || wizardDraft.learning_mode_custom ? '收起补充' : '自己填写' }}
                </button>
                <textarea
                  v-if="uiState.showLearningModeCustom || wizardDraft.learning_mode_custom"
                  v-model="wizardDraft.learning_mode_custom"
                  class="galgame-input"
                  rows="3"
                  maxlength="60"
                  placeholder="例如：希望边讨论边推演，而不是纯论文式研究"
                ></textarea>
              </div>

              <div class="field-group">
                <label class="field-label">这 里 的 推 进 节 奏 <span class="required">*</span></label>
                <div class="option-grid option-grid-tight">
                  <button
                    v-for="option in WORLD_PACE_OPTIONS"
                    :key="option"
                    type="button"
                    class="option-card"
                    :class="{ selected: wizardDraft.world_pace_preset === option }"
                    @click="wizardDraft.world_pace_preset = option"
                  >
                    {{ option }}
                  </button>
                </div>
                <button type="button" class="text-link" @click="toggleCustomField('worldPace')">
                  {{ uiState.showWorldPaceCustom || wizardDraft.world_pace_custom ? '收起补充' : '补充节奏' }}
                </button>
                <textarea
                  v-if="uiState.showWorldPaceCustom || wizardDraft.world_pace_custom"
                  v-model="wizardDraft.world_pace_custom"
                  class="galgame-input"
                  rows="3"
                  maxlength="60"
                  placeholder="例如：平时稳定，但阶段性会集中冲刺"
                ></textarea>
              </div>
            </template>

            <template v-else-if="uiState.currentStep === 'relationship'">
              <div class="field-group">
                <label class="field-label">你 在 这 个 世 界 里 更 像 谁 <span class="required">*</span></label>
                <div class="option-grid">
                  <button
                    v-for="option in SELF_POSITION_OPTIONS"
                    :key="option"
                    type="button"
                    class="option-card"
                    :class="{ selected: wizardDraft.self_position_preset === option }"
                    @click="wizardDraft.self_position_preset = option"
                  >
                    {{ option }}
                  </button>
                </div>
                <button type="button" class="text-link" @click="toggleCustomField('selfPosition')">
                  {{ uiState.showSelfPositionCustom || wizardDraft.self_position_custom ? '收起补充' : '补充我的位置' }}
                </button>
                <textarea
                  v-if="uiState.showSelfPositionCustom || wizardDraft.self_position_custom"
                  v-model="wizardDraft.self_position_custom"
                  class="galgame-input"
                  rows="3"
                  maxlength="60"
                  placeholder="例如：希望被带着进入世界，但保留自己决定路径的空间"
                ></textarea>
              </div>

              <div class="field-group">
                <label class="field-label">你 希 望 这 个 世 界 对 你 更 像 什 么 <span class="required">*</span></label>
                <div class="option-grid">
                  <button
                    v-for="option in WORLD_RELATIONSHIP_OPTIONS"
                    :key="option"
                    type="button"
                    class="option-card"
                    :class="{ selected: wizardDraft.world_relationship === option }"
                    @click="wizardDraft.world_relationship = option"
                  >
                    {{ option }}
                  </button>
                </div>
              </div>
            </template>

            <template v-else-if="uiState.currentStep === 'boundary'">
              <div class="field-group">
                <label class="field-label">不 希 望 这 个 世 界 太 像 什 么 <span class="required">*</span></label>
                <div class="tag-grid">
                  <button
                    v-for="option in NEGATIVE_WORLD_TRAIT_OPTIONS"
                    :key="option"
                    type="button"
                    class="tag-chip"
                    :class="{ selected: wizardDraft.negative_world_traits_preset.includes(option) }"
                    @click="togglePresetTag('worldTraits', option)"
                  >
                    {{ option }}
                  </button>
                </div>
                <div class="custom-tag-box">
                  <button type="button" class="text-link" @click="toggleCustomField('negativeWorldTrait')">
                    {{ uiState.showNegativeWorldTraitCustomInput ? '收起自定义边界' : '+ 添加自己的边界' }}
                  </button>
                  <div v-if="uiState.showNegativeWorldTraitCustomInput || wizardDraft.negative_world_traits_custom.length" class="custom-tag-editor">
                    <input
                      v-model="negativeWorldTraitInput"
                      type="text"
                      class="galgame-input"
                      maxlength="24"
                      placeholder="输入后回车添加"
                      @keyup.enter="appendCustomTag('worldTraits')"
                    />
                    <div v-if="wizardDraft.negative_world_traits_custom.length" class="selected-tags">
                      <span
                        v-for="tag in wizardDraft.negative_world_traits_custom"
                        :key="`world-${tag}`"
                        class="selected-tag"
                      >
                        {{ tag }}
                        <button type="button" class="remove-tag" @click="removeCustomTag('worldTraits', tag)">×</button>
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="field-group">
                <label class="field-label">不 希 望 学 习 在 这 里 变 成 什 么 <span class="required">*</span></label>
                <div class="tag-grid">
                  <button
                    v-for="option in NEGATIVE_LEARNING_MODE_OPTIONS"
                    :key="option"
                    type="button"
                    class="tag-chip"
                    :class="{ selected: wizardDraft.negative_learning_modes_preset.includes(option) }"
                    @click="togglePresetTag('learningModes', option)"
                  >
                    {{ option }}
                  </button>
                </div>
                <div class="custom-tag-box">
                  <button type="button" class="text-link" @click="toggleCustomField('negativeLearningMode')">
                    {{ uiState.showNegativeLearningModeCustomInput ? '收起自定义边界' : '+ 添加自己的边界' }}
                  </button>
                  <div v-if="uiState.showNegativeLearningModeCustomInput || wizardDraft.negative_learning_modes_custom.length" class="custom-tag-editor">
                    <input
                      v-model="negativeLearningModeInput"
                      type="text"
                      class="galgame-input"
                      maxlength="24"
                      placeholder="输入后回车添加"
                      @keyup.enter="appendCustomTag('learningModes')"
                    />
                    <div v-if="wizardDraft.negative_learning_modes_custom.length" class="selected-tags">
                      <span
                        v-for="tag in wizardDraft.negative_learning_modes_custom"
                        :key="`learning-${tag}`"
                        class="selected-tag"
                      >
                        {{ tag }}
                        <button type="button" class="remove-tag" @click="removeCustomTag('learningModes', tag)">×</button>
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="field-group">
                <label class="field-label">你 最 想 先 看 到 的 一 个 场 景 <span class="required">*</span></label>
                <textarea
                  v-model="wizardDraft.first_scene_fragment"
                  class="galgame-input"
                  rows="3"
                  maxlength="40"
                  placeholder="例如：清晨有雾的长廊"
                ></textarea>
              </div>

              <div class="field-group">
                <label class="field-label">第 一 次 来 到 这 里 的 人 会 立 刻 感 到 什 么 <span class="required">*</span></label>
                <textarea
                  v-model="wizardDraft.first_impression_fragment"
                  class="galgame-input"
                  rows="3"
                  maxlength="40"
                  placeholder="例如：安静、专注、被接住"
                ></textarea>
              </div>

              <div class="field-group">
                <label class="field-label">这 里 最 有 代 表 性 的 一 处 空 间</label>
                <textarea
                  v-model="wizardDraft.signature_space_fragment"
                  class="galgame-input"
                  rows="3"
                  maxlength="40"
                  placeholder="例如：堆满手稿和图表的公共研修室"
                ></textarea>
              </div>
            </template>

            <template v-else>
              <div class="field-group">
                <label class="field-label">世 界 名 称 <span class="required">*</span></label>
                <input
                  v-model="reviewForm.name"
                  type="text"
                  class="galgame-input"
                  maxlength="24"
                  placeholder="AI 生成后可手动微调"
                />
              </div>

              <div class="field-group">
                <label class="field-label">世 界 说 明 <span class="required">*</span></label>
                <textarea
                  v-model="reviewForm.description"
                  class="galgame-input"
                  rows="5"
                  maxlength="300"
                  placeholder="AI 生成后可手动微调"
                ></textarea>
              </div>

              <div class="field-group">
                <label class="field-label">背 景 图</label>
                <input
                  v-model="reviewForm.background_picture"
                  type="text"
                  class="galgame-input"
                  maxlength="120"
                  placeholder="/themes/academy.jpg"
                />
                <div class="background-preset-grid">
                  <button
                    v-for="preset in BACKGROUND_PRESETS"
                    :key="preset.path"
                    type="button"
                    class="background-preset"
                    :class="{ selected: reviewForm.background_picture === preset.path }"
                    @click="reviewForm.background_picture = preset.path"
                  >
                    {{ preset.label }}
                  </button>
                </div>
                <div v-if="reviewForm.background_picture" class="background-preview">
                  <div class="background-preview-image" :style="{ backgroundImage: `url(${reviewForm.background_picture})` }"></div>
                </div>
              </div>

              <div v-if="aiState.error" class="ai-error-inline">{{ aiState.error }}</div>
            </template>
          </div>

          <div class="summary-panel">
            <div class="summary-card">
              <div class="summary-title">当 前 世 界 壳 摘 要</div>
              <div class="summary-item">
                <span class="summary-label">地点</span>
                <span class="summary-value">{{ summarySpace }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">学习</span>
                <span class="summary-value">{{ summaryLearning }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">位置</span>
                <span class="summary-value">{{ summaryRelationship }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">边界</span>
                <span class="summary-value">{{ summaryBoundary }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">第一眼</span>
                <span class="summary-value">{{ summaryFirstScene }}</span>
              </div>
            </div>

            <div class="summary-card ai-card">
              <div class="summary-title">AI 生 成</div>
              <p class="summary-hint">
                先完成前四步，再让 AI 把这些碎片整合成最终世界说明。
              </p>
              <button
                type="button"
                class="ai-btn summary-ai-btn"
                :disabled="!canGenerateAi || aiState.generating"
                @click="handleAiGenerate"
              >
                <span v-if="aiState.generating" class="ai-spinner"></span>
                <span v-else>{{ uiState.currentStep === 'review' ? '重新生成' : '生成世界壳' }}</span>
              </button>
              <div v-if="aiState.generating" class="ai-progress-bar">
                <div class="ai-progress-fill" :style="{ width: aiState.progress + '%' }"></div>
              </div>
              <div v-if="reviewForm.name || reviewForm.description" class="review-snapshot">
                <div class="review-name">{{ reviewForm.name || '等待生成世界名' }}</div>
                <div class="review-description">{{ reviewForm.description || '等待生成世界说明' }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="btn-row">
          <button
            type="button"
            class="back-btn"
            @click="handleBack"
          >
            {{ uiState.currentStep === 'space' ? '取消' : '上一步' }}
          </button>

          <button
            v-if="uiState.currentStep !== 'review'"
            type="button"
            class="submit-btn"
            :disabled="!canProceed"
            @click="goNextStep"
          >
            下一步
          </button>

          <button
            v-else
            type="button"
            class="submit-btn"
            :disabled="!canCreate || creating"
            @click="handleCreate"
          >
            {{ creating ? '创建中…' : '进入这个世界' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { WORLD_THEMES } from '@/worlds/constants/worldThemes'
import { worldApi } from '@/worlds/api/world'

interface Props {
  show: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'create', data: {
    name: string
    description: string
    background_picture: string
  }): void
}

type WizardStep = 'space' | 'learning' | 'relationship' | 'boundary' | 'review'

interface WizardDraft {
  world_name_seed: string
  space_anchor: string
  space_reason: string
  learning_mode_preset: string
  learning_mode_custom: string
  world_pace_preset: string
  world_pace_custom: string
  self_position_preset: string
  self_position_custom: string
  world_relationship: string
  negative_world_traits_preset: string[]
  negative_world_traits_custom: string[]
  negative_learning_modes_preset: string[]
  negative_learning_modes_custom: string[]
  first_scene_fragment: string
  first_impression_fragment: string
  signature_space_fragment: string
}

interface ReviewForm {
  name: string
  description: string
  background_picture: string
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const SPACE_ANCHOR_OPTIONS = ['学院', '研究所', '书院', '档案馆', '山中居所', '空间站', '移动旅居地']
const LEARNING_MODE_OPTIONS = ['修行', '研究', '训练', '解谜', '协作建造', '长途探索']
const WORLD_PACE_OPTIONS = ['稳定长期推进', '高频挑战推进', '任务驱动推进', '安静整理与反思']
const SELF_POSITION_OPTIONS = ['新来的学习者', '被引导的探索者', '已有基础的进修者', '独立推进的研究者']
const WORLD_RELATIONSHIP_OPTIONS = ['庇护所', '训练场', '工作坊', '长期基地', '试炼地']
const NEGATIVE_WORLD_TRAIT_OPTIONS = ['压迫', '喧闹', '花哨', '冷漠', '军事化', '过度奇幻', '过度科幻']
const NEGATIVE_LEARNING_MODE_OPTIONS = ['考试工厂', '纯剧情表演', '过度游戏化', '没有秩序的闲聊']
const BACKGROUND_PRESETS = WORLD_THEMES.filter(theme => theme.background).map(theme => ({
  label: theme.name,
  path: theme.background,
}))

const STEP_ORDER: WizardStep[] = ['space', 'learning', 'relationship', 'boundary', 'review']

const creating = ref(false)
const negativeWorldTraitInput = ref('')
const negativeLearningModeInput = ref('')

const wizardDraft = reactive<WizardDraft>({
  world_name_seed: '',
  space_anchor: '',
  space_reason: '',
  learning_mode_preset: '',
  learning_mode_custom: '',
  world_pace_preset: '',
  world_pace_custom: '',
  self_position_preset: '',
  self_position_custom: '',
  world_relationship: '',
  negative_world_traits_preset: [],
  negative_world_traits_custom: [],
  negative_learning_modes_preset: [],
  negative_learning_modes_custom: [],
  first_scene_fragment: '',
  first_impression_fragment: '',
  signature_space_fragment: '',
})

const uiState = reactive({
  currentStep: 'space' as WizardStep,
  showLearningModeCustom: false,
  showWorldPaceCustom: false,
  showSelfPositionCustom: false,
  showNegativeWorldTraitCustomInput: false,
  showNegativeLearningModeCustomInput: false,
})

const aiState = reactive({
  generating: false,
  progress: 0,
  error: '',
  generatedName: '',
  generatedDescription: '',
  generatedBackgroundPicture: '',
})

const reviewForm = reactive<ReviewForm>({
  name: '',
  description: '',
  background_picture: '',
})

const stepIndex = computed(() => STEP_ORDER.indexOf(uiState.currentStep))

const stepTitle = computed(() => {
  switch (uiState.currentStep) {
    case 'space': return '这 是 什 么 地 方'
    case 'learning': return '这 里 如 何 学 习'
    case 'relationship': return '你 与 世 界 的 关 系'
    case 'boundary': return '边 界 与 场 景 碎 片'
    case 'review': return 'AI 生 成 确 认'
  }
})

const stepHint = computed(() => {
  switch (uiState.currentStep) {
    case 'space': return '先抓住这个世界的空间骨架。'
    case 'learning': return '再告诉系统，这里如何推进学习。'
    case 'relationship': return '接着确定你希望如何待在这个世界里。'
    case 'boundary': return '补上边界和画面感，防止 AI 跑偏。'
    case 'review': return 'AI 会把前面的碎片整合成最终世界壳。'
  }
})

const totalNegativeWorldTraits = computed(() =>
  wizardDraft.negative_world_traits_preset.length + wizardDraft.negative_world_traits_custom.length
)
const totalNegativeLearningModes = computed(() =>
  wizardDraft.negative_learning_modes_preset.length + wizardDraft.negative_learning_modes_custom.length
)

const canGenerateAi = computed(() =>
  Boolean(
    wizardDraft.space_anchor.trim()
    && (wizardDraft.learning_mode_preset.trim() || wizardDraft.learning_mode_custom.trim())
    && (wizardDraft.world_pace_preset.trim() || wizardDraft.world_pace_custom.trim())
    && (wizardDraft.self_position_preset.trim() || wizardDraft.self_position_custom.trim())
    && wizardDraft.world_relationship.trim()
    && totalNegativeWorldTraits.value > 0
    && totalNegativeLearningModes.value > 0
    && wizardDraft.first_scene_fragment.trim()
    && wizardDraft.first_impression_fragment.trim()
  )
)

const canProceed = computed(() => {
  switch (uiState.currentStep) {
    case 'space':
      return Boolean(wizardDraft.space_anchor.trim())
    case 'learning':
      return Boolean(
        (wizardDraft.learning_mode_preset.trim() || wizardDraft.learning_mode_custom.trim())
        && (wizardDraft.world_pace_preset.trim() || wizardDraft.world_pace_custom.trim())
      )
    case 'relationship':
      return Boolean(
        (wizardDraft.self_position_preset.trim() || wizardDraft.self_position_custom.trim())
        && wizardDraft.world_relationship.trim()
      )
    case 'boundary':
      return canGenerateAi.value
    case 'review':
      return canCreate.value
  }
})

const canCreate = computed(() =>
  Boolean(reviewForm.name.trim() && reviewForm.description.trim())
)

const summarySpace = computed(() => {
  if (!wizardDraft.space_anchor) return '还未选择空间母体'
  return wizardDraft.space_reason
    ? `${wizardDraft.space_anchor} · ${wizardDraft.space_reason}`
    : wizardDraft.space_anchor
})

const summaryLearning = computed(() => {
  const mode = [wizardDraft.learning_mode_preset, wizardDraft.learning_mode_custom].filter(Boolean).join(' / ')
  const pace = [wizardDraft.world_pace_preset, wizardDraft.world_pace_custom].filter(Boolean).join(' / ')
  if (!mode && !pace) return '还未确定学习方式'
  return [mode, pace].filter(Boolean).join(' · ')
})

const summaryRelationship = computed(() => {
  const position = [wizardDraft.self_position_preset, wizardDraft.self_position_custom].filter(Boolean).join(' / ')
  if (!position && !wizardDraft.world_relationship) return '还未确定你和世界的关系'
  return [position, wizardDraft.world_relationship].filter(Boolean).join(' · ')
})

const summaryBoundary = computed(() => {
  const tags = [
    ...wizardDraft.negative_world_traits_preset,
    ...wizardDraft.negative_world_traits_custom,
    ...wizardDraft.negative_learning_modes_preset,
    ...wizardDraft.negative_learning_modes_custom,
  ]
  return tags.length ? tags.slice(0, 4).join('、') : '还未设置边界'
})

const summaryFirstScene = computed(() => {
  if (wizardDraft.first_scene_fragment) return wizardDraft.first_scene_fragment
  if (wizardDraft.first_impression_fragment) return wizardDraft.first_impression_fragment
  return '还未提供第一眼场景'
})

function resetWizard() {
  Object.assign(wizardDraft, {
    world_name_seed: '',
    space_anchor: '',
    space_reason: '',
    learning_mode_preset: '',
    learning_mode_custom: '',
    world_pace_preset: '',
    world_pace_custom: '',
    self_position_preset: '',
    self_position_custom: '',
    world_relationship: '',
    negative_world_traits_preset: [],
    negative_world_traits_custom: [],
    negative_learning_modes_preset: [],
    negative_learning_modes_custom: [],
    first_scene_fragment: '',
    first_impression_fragment: '',
    signature_space_fragment: '',
  })

  Object.assign(uiState, {
    currentStep: 'space' as WizardStep,
    showLearningModeCustom: false,
    showWorldPaceCustom: false,
    showSelfPositionCustom: false,
    showNegativeWorldTraitCustomInput: false,
    showNegativeLearningModeCustomInput: false,
  })

  Object.assign(aiState, {
    generating: false,
    progress: 0,
    error: '',
    generatedName: '',
    generatedDescription: '',
    generatedBackgroundPicture: '',
  })

  Object.assign(reviewForm, {
    name: '',
    description: '',
    background_picture: '',
  })

  negativeWorldTraitInput.value = ''
  negativeLearningModeInput.value = ''
}

function toggleCustomField(kind: 'learningMode' | 'worldPace' | 'selfPosition' | 'negativeWorldTrait' | 'negativeLearningMode') {
  if (kind === 'learningMode') uiState.showLearningModeCustom = !uiState.showLearningModeCustom
  if (kind === 'worldPace') uiState.showWorldPaceCustom = !uiState.showWorldPaceCustom
  if (kind === 'selfPosition') uiState.showSelfPositionCustom = !uiState.showSelfPositionCustom
  if (kind === 'negativeWorldTrait') uiState.showNegativeWorldTraitCustomInput = !uiState.showNegativeWorldTraitCustomInput
  if (kind === 'negativeLearningMode') uiState.showNegativeLearningModeCustomInput = !uiState.showNegativeLearningModeCustomInput
}

function togglePresetTag(kind: 'worldTraits' | 'learningModes', value: string) {
  const target = kind === 'worldTraits'
    ? wizardDraft.negative_world_traits_preset
    : wizardDraft.negative_learning_modes_preset
  const index = target.indexOf(value)
  if (index >= 0) target.splice(index, 1)
  else target.push(value)
}

function appendCustomTag(kind: 'worldTraits' | 'learningModes') {
  const inputRef = kind === 'worldTraits' ? negativeWorldTraitInput : negativeLearningModeInput
  const value = inputRef.value.trim()
  if (!value) return
  const target = kind === 'worldTraits'
    ? wizardDraft.negative_world_traits_custom
    : wizardDraft.negative_learning_modes_custom
  if (!target.includes(value)) target.push(value)
  inputRef.value = ''
}

function removeCustomTag(kind: 'worldTraits' | 'learningModes', value: string) {
  const target = kind === 'worldTraits'
    ? wizardDraft.negative_world_traits_custom
    : wizardDraft.negative_learning_modes_custom
  const index = target.indexOf(value)
  if (index >= 0) target.splice(index, 1)
}

function goNextStep() {
  if (!canProceed.value) return
  const current = stepIndex.value
  if (current >= 0 && current < STEP_ORDER.length - 1) {
    uiState.currentStep = STEP_ORDER[current + 1]
  }
}

function handleBack() {
  if (uiState.currentStep === 'space') {
    emit('close')
    return
  }
  const current = stepIndex.value
  if (current > 0) {
    uiState.currentStep = STEP_ORDER[current - 1]
  }
}

function buildWorldShellGeneratePrompt() {
  const lines = [
    wizardDraft.world_name_seed ? `名字线索：${wizardDraft.world_name_seed}` : '',
    `这个世界最像：${wizardDraft.space_anchor}`,
    wizardDraft.space_reason ? `这个地方吸引我的原因：${wizardDraft.space_reason}` : '',
    `学习方式：${wizardDraft.learning_mode_preset || wizardDraft.learning_mode_custom}`,
    wizardDraft.learning_mode_custom ? `学习方式补充：${wizardDraft.learning_mode_custom}` : '',
    `推进节奏：${wizardDraft.world_pace_preset || wizardDraft.world_pace_custom}`,
    wizardDraft.world_pace_custom ? `节奏补充：${wizardDraft.world_pace_custom}` : '',
    `我在世界里的位置：${wizardDraft.self_position_preset || wizardDraft.self_position_custom}`,
    wizardDraft.self_position_custom ? `位置补充：${wizardDraft.self_position_custom}` : '',
    `我希望这个世界对我更像：${wizardDraft.world_relationship}`,
    [...wizardDraft.negative_world_traits_preset, ...wizardDraft.negative_world_traits_custom].length
      ? `这个世界不要太像：${[...wizardDraft.negative_world_traits_preset, ...wizardDraft.negative_world_traits_custom].join('、')}`
      : '',
    [...wizardDraft.negative_learning_modes_preset, ...wizardDraft.negative_learning_modes_custom].length
      ? `学习不要变成：${[...wizardDraft.negative_learning_modes_preset, ...wizardDraft.negative_learning_modes_custom].join('、')}`
      : '',
    `我最想先看到的场景：${wizardDraft.first_scene_fragment}`,
    `第一次进入会立刻感觉到：${wizardDraft.first_impression_fragment}`,
    wizardDraft.signature_space_fragment ? `最有代表性的空间：${wizardDraft.signature_space_fragment}` : '',
    '请根据这些碎片，生成一个适合长期学习的世界壳名称、世界说明和背景图建议。',
  ]

  return lines.filter(Boolean).join('\n')
}

async function handleAiGenerate() {
  if (!canGenerateAi.value || aiState.generating) return

  aiState.generating = true
  aiState.progress = 0
  aiState.error = ''

  const progressInterval = setInterval(() => {
    if (aiState.progress < 90) {
      aiState.progress += Math.random() * 15
    }
  }, 400)

  try {
    const result = await worldApi.generateWorld(buildWorldShellGeneratePrompt())
    aiState.progress = 100

    aiState.generatedName = result.name_suggestion || wizardDraft.world_name_seed || ''
    aiState.generatedDescription = result.description || ''
    aiState.generatedBackgroundPicture =
      result.background_picture
      || reviewForm.background_picture
      || '/themes/academy.jpg'

    reviewForm.name = aiState.generatedName
    reviewForm.description = aiState.generatedDescription
    reviewForm.background_picture = aiState.generatedBackgroundPicture

    uiState.currentStep = 'review'
  } catch (err: any) {
    aiState.error = err?.response?.data?.detail || err?.message || 'AI 生成失败，请重试'
  } finally {
    clearInterval(progressInterval)
    aiState.generating = false
  }
}

async function handleCreate() {
  if (!canCreate.value) return

  creating.value = true
  try {
    emit('create', {
      name: reviewForm.name.trim(),
      description: reviewForm.description.trim(),
      background_picture: reviewForm.background_picture.trim(),
    })
  } finally {
    creating.value = false
  }
}

watch(() => props.show, (visible) => {
  if (visible) resetWizard()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-box {
  position: relative;
  width: min(1080px, 94vw);
  max-height: 92vh;
  overflow-y: auto;
  padding: 28px 32px 24px;
  background: rgba(8, 8, 25, 0.98);
  border: 1px solid rgba(255, 215, 0, 0.15);
  border-top: none;
  backdrop-filter: blur(20px);
  border-radius: 12px;
}

.modal-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    to right,
    transparent 0%,
    rgba(255, 215, 0, 0.6) 20%,
    rgba(255, 215, 0, 0.9) 50%,
    rgba(255, 215, 0, 0.6) 80%,
    transparent 100%
  );
  border-radius: 12px 12px 0 0;
}

.modal-header {
  text-align: center;
  margin-bottom: 16px;
}

.modal-subtitle {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.25);
  margin-bottom: 6px;
}

.modal-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 18px;
  letter-spacing: 6px;
  color: #ffd700;
}

.gold-line {
  width: 120px;
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(255, 215, 0, 0.4), transparent);
  margin: 10px auto 0;
}

.step-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 18px;
}

.step-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.step-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.85);
}

.step-index {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  letter-spacing: 2px;
  color: rgba(255, 255, 255, 0.35);
}

.step-progress {
  height: 4px;
  background: rgba(255, 215, 0, 0.08);
  border-radius: 999px;
  overflow: hidden;
}

.step-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #f0c000);
  transition: width 0.25s ease;
}

.step-hint {
  margin: 0;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
}

.modal-body {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.95fr);
  gap: 20px;
}

.wizard-panel,
.summary-card {
  border: 1px solid rgba(255, 215, 0, 0.12);
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  padding: 18px;
}

.wizard-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.summary-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  letter-spacing: 3px;
  color: #ffd700;
  margin-bottom: 12px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 215, 0, 0.08);
}

.summary-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.summary-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  letter-spacing: 2px;
  color: rgba(255, 255, 255, 0.35);
}

.summary-value,
.review-description,
.summary-hint {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.65;
}

.review-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  letter-spacing: 2px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 8px;
}

.review-snapshot {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 215, 0, 0.08);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  font-family: "Noto Sans SC", sans-serif;
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
  letter-spacing: 3px;
}

.required {
  color: #ef4444;
}

.galgame-input {
  width: 100%;
  background: rgba(0, 0, 0, 0.4) !important;
  border: 2px solid rgba(255, 215, 0, 0.3) !important;
  font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif !important;
  font-size: 13px;
  padding: 10px 12px;
  color: rgba(255, 255, 255, 0.85);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s ease;
  resize: vertical;
}

.galgame-input:focus {
  border-color: rgba(255, 215, 0, 0.7) !important;
}

.galgame-input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

.option-grid,
.background-preset-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.option-grid-tight {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.option-card,
.background-preset {
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 215, 0, 0.16);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.24);
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
  cursor: pointer;
  transition: all 0.2s ease;
}

.option-card:hover,
.background-preset:hover {
  border-color: rgba(255, 215, 0, 0.36);
}

.option-card.selected,
.background-preset.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.08);
  color: #ffd700;
}

.text-link {
  align-self: flex-start;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 215, 0, 0.8);
  letter-spacing: 1px;
}

.text-link:hover {
  color: #ffe033;
}

.tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-chip,
.selected-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 215, 0, 0.16);
  background: rgba(0, 0, 0, 0.24);
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.72);
}

.tag-chip {
  cursor: pointer;
  transition: all 0.2s ease;
}

.tag-chip.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.08);
  color: #ffd700;
}

.custom-tag-box,
.custom-tag-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.remove-tag {
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 0;
  font-size: 12px;
  line-height: 1;
}

.background-preview {
  margin-top: 4px;
}

.background-preview-image {
  height: 112px;
  border-radius: 8px;
  background-size: cover;
  background-position: center;
  border: 1px solid rgba(255, 215, 0, 0.16);
}

.btn-row {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}

.back-btn {
  flex: 1;
  font-family: "Noto Sans SC", sans-serif;
  padding: 12px 24px;
  font-size: 13px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-btn:hover {
  color: rgba(255, 255, 255, 0.8);
  border-color: rgba(255, 215, 0, 0.4);
}

.submit-btn,
.ai-btn {
  font-family: "Noto Sans SC", sans-serif;
  padding: 12px 24px;
  font-size: 13px;
  letter-spacing: 4px;
  font-weight: 600;
  color: #0a0a1e;
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.submit-btn {
  flex: 2;
}

.summary-ai-btn {
  width: 100%;
  justify-content: center;
}

.submit-btn:hover:not(:disabled),
.ai-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffe033, #ffd700);
  box-shadow: 0 4px 20px rgba(255, 215, 0, 0.35);
  transform: translateY(-1px);
}

.submit-btn:disabled,
.ai-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.ai-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(10, 10, 30, 0.3);
  border-top-color: #0a0a1e;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.ai-progress-bar {
  height: 3px;
  background: rgba(255, 215, 0, 0.1);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 8px;
}

.ai-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700, #f0c000);
  border-radius: 2px;
  transition: width 0.5s ease;
}

.ai-error-inline {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: #ef4444;
}

.modal-fade-enter-active,
.modal-fade-enter-active .modal-box {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.modal-fade-leave-active,
.modal-fade-leave-active .modal-box {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .modal-box,
.modal-fade-leave-to .modal-box {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

@media (max-width: 900px) {
  .modal-box {
    width: 96vw;
    padding: 22px 18px 18px;
  }

  .modal-body {
    grid-template-columns: 1fr;
  }

  .summary-panel {
    order: -1;
  }
}

@media (max-width: 640px) {
  .option-grid,
  .background-preset-grid {
    grid-template-columns: 1fr;
  }

  .btn-row {
    flex-direction: column;
  }
}
</style>
