<script setup lang="ts">
/**
 * CourseDesignPage.vue
 * ──────────────────────────────────────────────────────────────
 * 课程设计页面 — 路由: /course/:courseId/design
 *
 * 三步流程：
 *   Step 1: 上传教材（MaterialUploader）
 *   Step 2: 配置切分参数 → 触发 AI 生成
 *   Step 3: 审阅 / 编辑 / 发布学习单元（LearningUnitCard）
 *
 * 路由注册（追加到 router/index.ts）：
 *   {
 *     path: '/course/:courseId/design',
 *     component: () => import('@/pages/CourseDesignPage.vue'),
 *     meta: { requiresAuth: true },
 *   }
 * ──────────────────────────────────────────────────────────────
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, Upload, Sparkles, BookOpen,
  AlertTriangle, CheckCircle, RefreshCw,
} from 'lucide-vue-next'
import { useCourseDesignStore }   from '@/stores/course_design'
import { useWorldStore }           from '@/stores/world'
import MaterialUploader            from '@/components/MaterialUploader.vue'
import LearningUnitCard            from '@/components/LearningUnitCard.vue'
import ParticleBackground          from '@/components/ParticleBackground.vue'

const route  = useRouter()
const router = useRouter()
const store  = useCourseDesignStore()
const world  = useWorldStore()
const routeP = useRoute()

const courseId   = Number(routeP.params.courseId)
const activeStep = ref<1 | 2 | 3>(1)

// ── Generate options ──────────────────────────────────────────
const targetCount    = ref(0)
const overwrite      = ref(false)
const selectedMatIds = ref<number[]>([])   // empty = use all ready materials

const canGenerate = computed(() =>
  store.readyMaterials.length > 0 && !store.generating
)

const courseName = computed(() =>
  world.selectedCourse?.name ?? `课程 #${courseId}`
)

// ── Lifecycle ─────────────────────────────────────────────────
onMounted(async () => {
  await store.init(courseId)
  // Auto-advance to step 3 if units already exist
  if (store.units.length > 0) activeStep.value = 3
  else if (store.materials.length > 0) activeStep.value = 2
})

onBeforeUnmount(() => store.dispose())

// ── Actions ───────────────────────────────────────────────────
async function handleGenerate() {
  store.error = null
  await store.generateUnits({
    materialIds:     selectedMatIds.value,
    targetUnitCount: targetCount.value,
    overwrite:       overwrite.value,
  })
  if (!store.error) {
    overwrite.value = false
    activeStep.value = 3
  }
}

async function handlePublishAll() {
  for (const unit of store.draftUnits) {
    await store.publishUnit(unit.id)
  }
}

// ── Steps ─────────────────────────────────────────────────────
const STEPS = [
  { id: 1, label: '上传教材', icon: Upload },
  { id: 2, label: 'AI 课时切分', icon: Sparkles },
  { id: 3, label: '审阅 & 发布', icon: BookOpen },
]

const BG_URL = 'https://images.unsplash.com/photo-1629639057315-410edca4fa89?w=1920&q=80'
</script>

<template>
  <div
    class="relative w-screen h-screen overflow-hidden"
    style="background:#0a0a1e;"
  >
    <!-- Background -->
    <div class="absolute inset-0"
      :style="{ backgroundImage:`url(${BG_URL})`, backgroundSize:'cover',
                backgroundPosition:'center', opacity:0.1 }" />
    <div class="absolute inset-0" style="background:linear-gradient(to bottom,
      rgba(10,10,30,0.95) 0%,rgba(10,10,30,0.98) 100%);" />
    <ParticleBackground :count="14" :gold-ratio="0.5" />

    <!-- Header -->
    <div
      class="absolute top-0 left-0 right-0 flex items-center justify-between font-ui"
      style="padding:14px 24px;border-bottom:1px solid rgba(255,215,0,0.1);z-index:10;"
    >
      <button
        class="flex items-center gap-2 galgame-hud-btn"
        style="font-size:13px;padding:6px 14px;"
        @click="router.push('/home')"
      >
        <ArrowLeft :size="14" /> 返回
      </button>

      <div class="flex flex-col items-center">
        <span style="color:#ffd700;font-size:15px;letter-spacing:3px;">课程设计</span>
        <span style="color:rgba(255,255,255,0.4);font-size:11px;margin-top:1px;">{{ courseName }}</span>
      </div>

      <!-- Step indicator -->
      <div class="flex items-center gap-3">
        <template v-for="(step, i) in STEPS" :key="step.id">
          <button
            class="flex items-center gap-1 font-ui"
            :style="{
              fontSize: '11px', letterSpacing: '1px',
              color: activeStep === step.id ? '#ffd700' : 'rgba(255,255,255,0.3)',
              cursor: 'pointer', padding: '4px 0',
              borderBottom: activeStep === step.id ? '1px solid #ffd700' : '1px solid transparent',
              transition: 'all 0.2s ease',
            }"
            @click="(activeStep as any) = step.id"
          >
            <component :is="step.icon" :size="11" />
            {{ step.label }}
          </button>
          <span
            v-if="i < STEPS.length - 1"
            style="color:rgba(255,255,255,0.15);font-size:12px;"
          >›</span>
        </template>
      </div>
    </div>

    <!-- Content -->
    <div
      class="absolute inset-0 overflow-y-auto galgame-scrollbar"
      style="padding-top:68px;padding-bottom:32px;"
    >
      <div style="max-width:820px;margin:0 auto;padding:24px;">
        <Transition name="step-fade" mode="out-in">

          <!-- ── Step 1: Upload Materials ─────────────────────── -->
          <div v-if="activeStep === 1" key="step1" class="flex flex-col gap-5">
            <div class="galgame-panel" style="padding:22px 26px;">
              <div class="flex items-center justify-between mb-5">
                <div>
                  <div class="font-ui" style="color:#ffd700;font-size:14px;letter-spacing:2px;margin-bottom:3px;">
                    📂 上传课程教材
                  </div>
                  <div class="font-ui" style="font-size:11px;color:rgba(255,255,255,0.4);">
                    支持 .txt · .md · .pdf · .docx，单文件 ≤ 10 MB
                  </div>
                </div>
                <button
                  v-if="store.readyMaterials.length > 0"
                  class="galgame-send-btn font-ui flex items-center gap-2"
                  style="padding:8px 20px;font-size:12px;"
                  @click="activeStep = 2"
                >
                  下一步 →
                </button>
              </div>
              <MaterialUploader />
            </div>

            <!-- Summary tip -->
            <div
              v-if="store.readyMaterials.length > 0"
              style="border:1px solid rgba(74,223,106,0.2);padding:12px 16px;
                display:flex;align-items:center;gap:10px;"
            >
              <CheckCircle :size="14" style="color:rgba(74,223,106,0.7);flex-shrink:0;" />
              <span class="font-ui" style="font-size:12px;color:rgba(255,255,255,0.6);">
                {{ store.readyMaterials.length }} 份教材已就绪，可以进行 AI 课时切分。
              </span>
              <button
                class="galgame-hud-btn font-ui ml-auto"
                style="font-size:11px;padding:4px 12px;"
                @click="activeStep = 2"
              >前往切分 →</button>
            </div>

            <div
              v-if="store.pendingMaterials.length > 0"
              style="border:1px solid rgba(96,165,250,0.2);padding:12px 16px;
                display:flex;align-items:center;gap:10px;"
            >
              <RefreshCw :size="13" style="color:rgba(96,165,250,0.7);animation:spin 2s linear infinite;" />
              <span class="font-ui" style="font-size:12px;color:rgba(255,255,255,0.4);">
                {{ store.pendingMaterials.length }} 份教材正在提取文本，每 3 秒自动刷新…
              </span>
            </div>
          </div>

          <!-- ── Step 2: Generate Units ──────────────────────── -->
          <div v-else-if="activeStep === 2" key="step2" class="flex flex-col gap-5">
            <div class="galgame-panel" style="padding:22px 26px;">
              <div class="font-ui mb-5" style="color:#ffd700;font-size:14px;letter-spacing:2px;">
                ✦ AI 课时切分配置
              </div>

              <!-- Material selection -->
              <div class="mb-5">
                <div class="font-ui mb-2" style="font-size:11px;color:rgba(255,255,255,0.5);letter-spacing:1px;">
                  参与切分的教材（不选则使用全部就绪教材）
                </div>
                <div class="flex flex-col gap-1">
                  <label
                    v-for="mat in store.readyMaterials"
                    :key="mat.id"
                    class="flex items-center gap-2 font-ui"
                    style="font-size:12px;color:rgba(255,255,255,0.7);cursor:pointer;"
                  >
                    <input
                      type="checkbox"
                      :value="mat.id"
                      v-model="selectedMatIds"
                      style="accent-color:#ffd700;"
                    />
                    {{ mat.original_filename }}
                    <span style="color:rgba(255,255,255,0.3);font-size:10px;">
                      ({{ (mat.file_size / 1024).toFixed(0) }} KB)
                    </span>
                  </label>
                </div>
                <div v-if="store.readyMaterials.length === 0"
                  class="font-ui" style="font-size:12px;color:rgba(255,100,100,0.7);">
                  ⚠ 没有就绪的教材，请先在第一步上传并等待提取完成。
                </div>
              </div>

              <!-- Options -->
              <div class="flex gap-6 mb-6 flex-wrap">
                <div>
                  <div class="font-ui mb-1" style="font-size:11px;color:rgba(255,255,255,0.5);letter-spacing:1px;">
                    期望课时数（0 = AI 自主决定）
                  </div>
                  <input
                    v-model.number="targetCount"
                    type="number" min="0" max="50"
                    class="galgame-input font-ui"
                    style="padding:6px 12px;width:100px;font-size:13px;"
                  />
                </div>

                <div>
                  <div class="font-ui mb-2" style="font-size:11px;color:rgba(255,255,255,0.5);letter-spacing:1px;">
                    覆盖已有草稿单元
                  </div>
                  <button
                    :style="{
                      width:'44px', height:'24px', borderRadius:'12px', border:'none',
                      cursor:'pointer', position:'relative', transition:'background 0.2s ease',
                      background: overwrite ? 'rgba(239,68,68,0.6)' : 'rgba(255,255,255,0.15)',
                    }"
                    @click="overwrite = !overwrite"
                  >
                    <span :style="{
                      position:'absolute', top:'2px', width:'20px', height:'20px',
                      borderRadius:'50%', background:'#fff', transition:'left 0.2s ease',
                      left: overwrite ? '22px' : '2px',
                    }" />
                  </button>
                </div>
              </div>

              <!-- Warnings from previous run -->
              <div
                v-for="(w, i) in store.generateWarnings"
                :key="i"
                style="border:1px solid rgba(249,115,22,0.3);padding:8px 14px;
                  display:flex;gap:8px;align-items:center;margin-bottom:8px;"
              >
                <AlertTriangle :size="12" style="color:#f97316;flex-shrink:0;" />
                <span class="font-ui" style="font-size:11px;color:rgba(249,115,22,0.9);">{{ w }}</span>
              </div>

              <!-- Error -->
              <div v-if="store.error"
                style="border:1px solid rgba(239,68,68,0.3);padding:10px 14px;margin-bottom:12px;
                  color:rgba(239,68,68,0.9);font-size:12px;" class="font-ui">
                {{ store.error }}
              </div>

              <!-- Generate button -->
              <button
                class="galgame-send-btn font-ui flex items-center gap-2"
                style="padding:12px 32px;font-size:14px;letter-spacing:2px;"
                :disabled="!canGenerate"
                :style="{ opacity: canGenerate ? 1 : 0.4, cursor: canGenerate ? 'pointer' : 'not-allowed' }"
                @click="handleGenerate"
              >
                <Sparkles :size="15" />
                {{ store.generating ? 'AI 正在切分中…' : '开始 AI 课时切分' }}
              </button>

              <div v-if="store.generating" class="flex items-center gap-3 mt-4">
                <span
                  v-for="i in 5" :key="i"
                  class="font-dialogue"
                  :style="{
                    fontSize: '20px', color: 'rgba(255,215,0,0.6)',
                    animation: `dotFlash 1.4s ease-in-out ${(i-1)*0.25}s infinite`,
                    display: 'inline-block',
                  }"
                >·</span>
                <span class="font-ui" style="font-size:12px;color:rgba(255,255,255,0.4);">
                  AI 正在分析教材内容并生成结构化课时，通常需要 10-60 秒…
                </span>
              </div>
            </div>
          </div>

          <!-- ── Step 3: Review Units ────────────────────────── -->
          <div v-else-if="activeStep === 3" key="step3" class="flex flex-col gap-4">

            <!-- Summary bar -->
            <div class="galgame-panel flex items-center justify-between" style="padding:14px 20px;">
              <div class="flex items-center gap-6 font-ui" style="font-size:12px;">
                <span style="color:rgba(255,255,255,0.6);">
                  共 <span style="color:#ffd700;">{{ store.units.length }}</span> 个课时
                </span>
                <span style="color:rgba(255,255,255,0.6);">
                  草稿 <span style="color:rgba(255,215,0,0.7);">{{ store.draftUnits.length }}</span>
                  · 已发布 <span style="color:rgba(74,223,106,0.8);">{{ store.readyUnits.length }}</span>
                </span>
                <span style="color:rgba(255,255,255,0.6);">
                  预估总时长 <span style="color:#ffd700;">{{ store.totalEstimatedMin }}</span> 分钟
                </span>
              </div>
              <div class="flex gap-2">
                <button
                  class="galgame-hud-btn flex items-center gap-1"
                  style="font-size:11px;"
                  @click="activeStep = 2"
                ><RefreshCw :size="10" /> 重新生成</button>
                <button
                  v-if="store.draftUnits.length > 0"
                  class="galgame-send-btn font-ui flex items-center gap-1"
                  style="padding:6px 16px;font-size:11px;"
                  @click="handlePublishAll"
                ><CheckCircle :size="10" /> 全部发布</button>
              </div>
            </div>

            <!-- Warnings from generation -->
            <div
              v-for="(w, i) in store.generateWarnings"
              :key="i"
              style="border:1px solid rgba(249,115,22,0.25);padding:8px 14px;
                display:flex;gap:8px;align-items:center;"
            >
              <AlertTriangle :size="11" style="color:#f97316;flex-shrink:0;" />
              <span class="font-ui" style="font-size:11px;color:rgba(249,115,22,0.8);">{{ w }}</span>
            </div>

            <!-- Unit cards -->
            <div v-if="store.units.length === 0"
              class="font-ui" style="color:rgba(255,255,255,0.3);text-align:center;padding:60px 0;">
              暂无学习单元。请在第二步触发 AI 课时切分。
            </div>

            <LearningUnitCard
              v-for="unit in store.units"
              :key="unit.id"
              :unit="unit"
              :all-units="store.units"
              @deleted="store.fetchUnits()"
            />
          </div>

        </Transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.step-fade-enter-from { opacity: 0; transform: translateX(12px); }
.step-fade-enter-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.step-fade-leave-to { opacity: 0; transform: translateX(-12px); }
.step-fade-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
