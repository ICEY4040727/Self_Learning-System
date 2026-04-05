<script setup lang="ts">
/**
 * LearningUnitCard.vue
 * ──────────────────────────────────────────────────────────────
 * 单个学习单元卡片（展示 + 内联编辑 + 状态操作）
 * ──────────────────────────────────────────────────────────────
 */
import { ref, computed } from 'vue'
import {
  ChevronDown, ChevronRight, Edit2, Check, X,
  Play, Archive, Trash2, Clock, BookOpen,
} from 'lucide-vue-next'
import type { LearningUnit } from '@/types'
import { BLOOM_LABELS, BLOOM_COLORS } from '@/types'
import { useCourseDesignStore } from '@/stores/course_design'

const props = defineProps<{ unit: LearningUnit; allUnits: LearningUnit[] }>()
const emit  = defineEmits<{ (e: 'deleted'): void }>()

const store    = useCourseDesignStore()
const expanded = ref(false)
const editing  = ref(false)
const saving   = ref(false)

// ── Edit form state ───────────────────────────────────────────
const editTitle       = ref('')
const editSummary     = ref('')
const editMinutes     = ref(0)
const editObjectives  = ref('')   // newline-separated
const editConcepts    = ref('')   // newline-separated
const editBloom       = ref<string | null>(null)

function startEdit() {
  editTitle.value      = props.unit.title
  editSummary.value    = props.unit.summary
  editMinutes.value    = props.unit.estimated_minutes
  editObjectives.value = props.unit.learning_objectives.join('\n')
  editConcepts.value   = props.unit.key_concepts.join('\n')
  editBloom.value      = props.unit.bloom_level
  editing.value        = true
  expanded.value       = true
}

async function saveEdit() {
  saving.value = true
  try {
    await store.updateUnit(props.unit.id, {
      title:               editTitle.value.trim(),
      summary:             editSummary.value.trim(),
      estimated_minutes:   editMinutes.value,
      learning_objectives: editObjectives.value.split('\n').map(s => s.trim()).filter(Boolean),
      key_concepts:        editConcepts.value.split('\n').map(s => s.trim()).filter(Boolean),
      bloom_level:         editBloom.value as any,
    })
    editing.value = false
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  editing.value = false
}

// ── Status actions ────────────────────────────────────────────
async function handlePublish() {
  await store.publishUnit(props.unit.id)
}
async function handleArchive() {
  await store.archiveUnit(props.unit.id)
}
async function handleDelete() {
  await store.deleteUnit(props.unit.id)
  emit('deleted')
}

// ── Derived display ───────────────────────────────────────────
const bloomLabel = computed(() =>
  props.unit.bloom_level ? (BLOOM_LABELS[props.unit.bloom_level] ?? props.unit.bloom_level) : '—'
)
const bloomColor = computed(() =>
  props.unit.bloom_level ? (BLOOM_COLORS[props.unit.bloom_level] ?? '#aaaaaa') : '#555'
)

const statusStyle = computed(() => {
  switch (props.unit.status) {
    case 'ready':    return { color: 'rgba(74,223,106,0.9)',   border: 'rgba(74,223,106,0.3)'  }
    case 'archived': return { color: 'rgba(148,163,184,0.6)', border: 'rgba(148,163,184,0.2)' }
    default:         return { color: 'rgba(255,215,0,0.7)',   border: 'rgba(255,215,0,0.2)'   }
  }
})

const prerequisiteNames = computed(() =>
  props.unit.prerequisite_unit_ids
    .map(id => props.allUnits.find(u => u.id === id)?.title ?? `#${id}`)
    .join('、')
)

const BLOOM_OPTIONS = [
  'remember', 'understand', 'apply', 'analyze', 'evaluate', 'create',
] as const
</script>

<template>
  <div
    style="border:1px solid rgba(255,215,0,0.12);transition:border-color 0.2s ease;"
    :style="{ borderColor: expanded ? 'rgba(255,215,0,0.3)' : 'rgba(255,215,0,0.12)' }"
  >
    <!-- Header row -->
    <div
      class="flex items-center gap-3"
      style="padding:12px 16px;cursor:pointer;"
      @click="expanded = !expanded; editing = false"
    >
      <!-- Index badge -->
      <div
        class="flex-shrink-0 font-ui"
        style="width:26px;height:26px;border-radius:50%;border:1px solid rgba(255,215,0,0.3);
          display:flex;align-items:center;justify-content:center;
          font-size:11px;color:rgba(255,215,0,0.7);"
      >{{ unit.unit_index + 1 }}</div>

      <!-- Title + status -->
      <div class="flex-1 min-w-0">
        <div class="font-ui" style="font-size:14px;color:rgba(240,240,255,0.9);
          white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          {{ unit.title }}
        </div>
        <div class="flex items-center gap-3 mt-1">
          <!-- Status badge -->
          <span
            class="font-ui"
            :style="{
              fontSize: '10px', letterSpacing: '1px',
              color: statusStyle.color,
              border: `1px solid ${statusStyle.border}`,
              padding: '1px 6px',
            }"
          >{{ { draft:'草稿', ready:'已发布', archived:'已归档' }[unit.status] }}</span>
          <!-- Bloom badge -->
          <span
            v-if="unit.bloom_level"
            class="font-ui"
            :style="{
              fontSize: '10px', color: bloomColor,
              border: `1px solid ${bloomColor}40`,
              padding: '1px 6px',
            }"
          >{{ bloomLabel }}</span>
          <!-- Time -->
          <span class="flex items-center gap-1 font-ui" style="font-size:10px;color:rgba(255,255,255,0.3);">
            <Clock :size="9" /> {{ unit.estimated_minutes }} min
          </span>
        </div>
      </div>

      <!-- Actions (shown on hover via CSS group) -->
      <div class="flex items-center gap-1 flex-shrink-0" @click.stop>
        <button
          v-if="unit.status === 'draft'"
          class="galgame-hud-btn flex items-center gap-1"
          style="font-size:10px;padding:2px 8px;color:rgba(74,223,106,0.8);"
          title="发布"
          @click="handlePublish"
        ><Play :size="9" /> 发布</button>

        <button
          v-if="unit.status === 'ready'"
          class="galgame-hud-btn flex items-center gap-1"
          style="font-size:10px;padding:2px 8px;"
          title="归档"
          @click="handleArchive"
        ><Archive :size="9" /> 归档</button>

        <button
          class="galgame-hud-btn flex items-center gap-1"
          style="font-size:10px;padding:2px 8px;"
          title="编辑"
          @click="startEdit"
        ><Edit2 :size="9" /> 编辑</button>

        <button
          class="galgame-hud-btn flex items-center gap-1"
          style="font-size:10px;padding:2px 8px;color:rgba(239,68,68,0.7);"
          title="删除"
          @click="handleDelete"
        ><Trash2 :size="9" /></button>
      </div>

      <!-- Expand chevron -->
      <component
        :is="expanded ? ChevronDown : ChevronRight"
        :size="14"
        style="color:rgba(255,215,0,0.4);flex-shrink:0;"
      />
    </div>

    <!-- Expanded body -->
    <Transition name="unit-expand">
      <div v-if="expanded" style="border-top:1px solid rgba(255,215,0,0.08);padding:16px 18px;">

        <!-- View mode -->
        <template v-if="!editing">
          <p class="font-dialogue" style="font-size:14px;line-height:1.85;color:rgba(240,240,255,0.8);margin-bottom:14px;">
            {{ unit.summary }}
          </p>

          <div class="flex flex-wrap gap-6">
            <!-- Learning objectives -->
            <div style="flex:1;min-width:200px;">
              <div class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.6);letter-spacing:2px;margin-bottom:6px;">
                学习目标
              </div>
              <ul style="padding:0;margin:0;list-style:none;">
                <li
                  v-for="(obj, i) in unit.learning_objectives"
                  :key="i"
                  class="font-ui"
                  style="font-size:12px;color:rgba(255,255,255,0.7);padding:2px 0;display:flex;gap:6px;"
                >
                  <span style="color:rgba(255,215,0,0.5);">▸</span> {{ obj }}
                </li>
              </ul>
            </div>

            <!-- Key concepts -->
            <div style="flex:1;min-width:160px;">
              <div class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.6);letter-spacing:2px;margin-bottom:6px;">
                关键概念
              </div>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="concept in unit.key_concepts"
                  :key="concept"
                  class="font-ui"
                  style="font-size:11px;color:rgba(255,255,255,0.7);
                    border:1px solid rgba(255,255,255,0.1);padding:2px 8px;"
                >{{ concept }}</span>
              </div>
            </div>
          </div>

          <!-- Prerequisites -->
          <div v-if="unit.prerequisite_unit_ids.length > 0" class="mt-3">
            <span class="font-ui" style="font-size:10px;color:rgba(255,255,255,0.3);">
              前置单元：{{ prerequisiteNames }}
            </span>
          </div>

          <!-- Dialogue hints (collapsible) -->
          <details v-if="unit.dialogue_hints.length > 0" class="mt-3">
            <summary class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.4);
              cursor:pointer;letter-spacing:1px;user-select:none;">
              对话引导提示（仅教师端可见）
            </summary>
            <ul style="padding:8px 0 0 16px;margin:0;">
              <li
                v-for="(hint, i) in unit.dialogue_hints"
                :key="i"
                class="font-dialogue"
                style="font-size:12px;color:rgba(255,255,255,0.4);padding:2px 0;line-height:1.7;"
              >{{ hint }}</li>
            </ul>
          </details>
        </template>

        <!-- Edit mode -->
        <template v-else>
          <div class="flex flex-col gap-3">
            <div>
              <label class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.6);letter-spacing:1px;display:block;margin-bottom:4px;">
                课时标题
              </label>
              <input
                v-model="editTitle"
                class="galgame-input font-ui w-full"
                style="padding:7px 10px;font-size:13px;"
              />
            </div>

            <div>
              <label class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.6);letter-spacing:1px;display:block;margin-bottom:4px;">
                概要描述
              </label>
              <textarea
                v-model="editSummary"
                class="galgame-input font-dialogue w-full"
                rows="3"
                style="padding:7px 10px;font-size:13px;resize:none;"
              />
            </div>

            <div class="flex gap-4">
              <div style="flex:1;">
                <label class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.6);letter-spacing:1px;display:block;margin-bottom:4px;">
                  Bloom 层次
                </label>
                <div class="flex flex-wrap gap-1">
                  <button
                    v-for="lvl in BLOOM_OPTIONS"
                    :key="lvl"
                    class="font-ui"
                    :style="{
                      fontSize: '10px', padding: '2px 8px', cursor: 'pointer',
                      border: `1px solid ${editBloom === lvl ? BLOOM_COLORS[lvl] : 'rgba(255,255,255,0.1)'}`,
                      color: editBloom === lvl ? BLOOM_COLORS[lvl] : 'rgba(255,255,255,0.4)',
                      background: 'transparent', transition: 'all 0.15s ease',
                    }"
                    @click="editBloom = lvl"
                  >{{ BLOOM_LABELS[lvl] }}</button>
                </div>
              </div>

              <div>
                <label class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.6);letter-spacing:1px;display:block;margin-bottom:4px;">
                  时长（分钟）
                </label>
                <input
                  v-model.number="editMinutes"
                  type="number" min="5" max="240"
                  class="galgame-input font-ui"
                  style="padding:7px 10px;font-size:13px;width:80px;"
                />
              </div>
            </div>

            <div class="flex gap-4">
              <div style="flex:1;">
                <label class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.6);letter-spacing:1px;display:block;margin-bottom:4px;">
                  学习目标（每行一条）
                </label>
                <textarea
                  v-model="editObjectives"
                  class="galgame-input font-ui w-full"
                  rows="3"
                  style="padding:7px 10px;font-size:12px;resize:none;"
                />
              </div>
              <div style="flex:1;">
                <label class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.6);letter-spacing:1px;display:block;margin-bottom:4px;">
                  关键概念（每行一个）
                </label>
                <textarea
                  v-model="editConcepts"
                  class="galgame-input font-ui w-full"
                  rows="3"
                  style="padding:7px 10px;font-size:12px;resize:none;"
                />
              </div>
            </div>

            <!-- Save / Cancel -->
            <div class="flex gap-2 justify-end">
              <button class="galgame-hud-btn flex items-center gap-1" @click="cancelEdit">
                <X :size="11" /> 取消
              </button>
              <button
                class="galgame-send-btn font-ui flex items-center gap-1"
                style="padding:6px 20px;font-size:12px;"
                :disabled="saving"
                @click="saveEdit"
              >
                <Check :size="11" /> {{ saving ? '保存中…' : '保存' }}
              </button>
            </div>
          </div>
        </template>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.unit-expand-enter-from { opacity: 0; transform: translateY(-6px); }
.unit-expand-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.unit-expand-leave-to { opacity: 0; }
.unit-expand-leave-active { transition: opacity 0.15s ease; }
</style>
