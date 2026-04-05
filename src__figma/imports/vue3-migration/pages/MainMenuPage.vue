<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Plus, BookOpen, Play, Trash2, Settings2 } from 'lucide-vue-next'
import { useWorldStore } from '@/stores/world'
import { useAuthStore }  from '@/stores/auth'
import { STAGE_LABELS }  from '@/types'
import type { World, Course, Checkpoint } from '@/types'
import ParticleBackground from '@/components/ParticleBackground.vue'

// ── Router & Stores ──────────────────────────────────────────
const router = useRouter()
const worldStore = useWorldStore()
const auth       = useAuthStore()

// ── Phase state machine ──────────────────────────────────────
type Phase = 'main' | 'world-select' | 'course-select' | 'memory-vault' | 'character-manage'
const phase = ref<Phase>('main')

// ── Local UI ──────────────────────────────────────────────────
const checkpoints  = ref<Checkpoint[]>([])
const charTab      = ref<'sage' | 'traveler'>('sage')
const newWorldName = ref('')
const newWorldDesc = ref('')
const showNewWorld = ref(false)

// 新增课程表单
const showNewCourse    = ref(false)
const newCourseName    = ref('')
const newCourseDesc    = ref('')
const newCourseLevel   = ref('中级')
const courseCreating   = ref(false)
const courseCreateErr  = ref('')

// ── Computed ──────────────────────────────────────────────────
const bgUrl = computed(() =>
  worldStore.selectedWorld?.scenes?.background ??
  worldStore.worlds[0]?.scenes?.background ??
  'https://images.unsplash.com/photo-1629639057315-410edca4fa89?w=1920&q=80'
)

const courses = computed(() => worldStore.selectedWorld?.courses ?? [])

// ── Lifecycle ─────────────────────────────────────────────────
onMounted(async () => {
  await worldStore.fetchWorlds()
})

// ── Navigation handlers ───────────────────────────────────────
async function selectWorld(world: World) {
  worldStore.selectWorld(world)
  await worldStore.fetchCourses(world.id)
  await worldStore.fetchCheckpoints(world.id)
  checkpoints.value = worldStore.checkpoints
  phase.value = 'course-select'
}

async function selectCourse(course: Course) {
  worldStore.selectCourse(course)
  if (checkpoints.value.length > 0) {
    phase.value = 'memory-vault'
  } else {
    navigate('/learning', course.id, worldStore.selectedWorld!.id)
  }
}

function loadCheckpoint(cp: Checkpoint) {
  router.push({
    path: '/learning',
    query: {
      worldId: String(worldStore.selectedWorld!.id),
      courseId: String(worldStore.selectedCourse!.id),
      checkpointId: String(cp.id),
    },
  })
}

function navigate(path: string, courseId?: number, worldId?: number) {
  router.push({
    path,
    query: {
      ...(worldId  ? { worldId:  String(worldId)  } : {}),
      ...(courseId ? { courseId: String(courseId) } : {}),
    },
  })
}

function startNewJourney() {
  navigate('/learning', worldStore.selectedCourse!.id, worldStore.selectedWorld!.id)
}

// ── Create world ──────────────────────────────────────────────
async function handleCreateWorld() {
  if (!newWorldName.value.trim()) return
  await worldStore.createWorld({
    name: newWorldName.value.trim(),
    description: newWorldDesc.value.trim(),
  })
  newWorldName.value = ''
  newWorldDesc.value = ''
  showNewWorld.value = false
}

// ── Create course + go to design ─────────────────────────────
async function handleCreateCourse() {
  if (!newCourseName.value.trim() || !worldStore.selectedWorld) return
  courseCreating.value = true
  courseCreateErr.value = ''
  try {
    const course = await worldStore.createCourse(worldStore.selectedWorld.id, {
      name:         newCourseName.value.trim(),
      description:  newCourseDesc.value.trim(),
      target_level: newCourseLevel.value,
    })
    // 直接跳转到课程设计页上传教材
    router.push(`/course/${course.id}/design`)
  } catch (e: any) {
    courseCreateErr.value = e?.response?.data?.detail ?? '创建失败'
  } finally {
    courseCreating.value = false
  }
}

function openCourseDesign(course: Course) {
  worldStore.selectCourse(course)
  router.push(`/course/${course.id}/design`)
}

// ── Logout ────────────────────────────────────────────────────
function handleLogout() {
  auth.logout()
  worldStore.reset()
  router.push('/')
}

// ── Phase label ───────────────────────────────────────────────
const PHASE_TITLES: Partial<Record<Phase, string>> = {
  'world-select':    '— 选择世界 —',
  'course-select':   '— 选择课程 —',
  'memory-vault':    '— 记忆库 —',
  'character-manage':'— 角色管理 —',
}
</script>

<template>
  <div
    class="relative w-screen h-screen overflow-hidden"
    style="background:#0a0a1e;"
  >
    <!-- Scene background -->
    <div
      class="absolute inset-0"
      :style="{
        backgroundImage: `url(${bgUrl})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        opacity: 0.18,
        transition: 'opacity 0.8s ease',
      }"
    />
    <div class="absolute inset-0" style="background:linear-gradient(to bottom,
      rgba(10,10,30,0.55) 0%,rgba(10,10,30,0.88) 70%,rgba(10,10,30,0.98) 100%);" />
    <ParticleBackground :count="22" :gold-ratio="0.55" />

    <!-- System title (main phase) -->
    <Transition name="fade">
      <div
        v-if="phase === 'main'"
        class="absolute top-16 left-0 right-0 text-center"
      >
        <h1
          class="breathe-glow font-dialogue"
          style="font-size:42px;letter-spacing:12px;color:#ffd700;"
        >知　遇</h1>
        <p class="font-ui" style="font-size:12px;letter-spacing:4px;
          color:rgba(255,255,255,0.35);margin-top:8px;">
          与智慧同行的学习之旅
        </p>
      </div>
    </Transition>

    <!-- Phase title (non-main) -->
    <Transition name="fade">
      <div
        v-if="phase !== 'main'"
        class="absolute top-0 left-0 right-0 flex items-center justify-between font-ui"
        style="padding:18px 28px;border-bottom:1px solid rgba(255,215,0,0.1);z-index:10;"
      >
        <button
          class="galgame-hud-btn flex items-center gap-2"
          style="font-size:13px;padding:6px 14px;"
          @click="phase = (phase === 'course-select' ? 'world-select' :
                           phase === 'memory-vault'   ? 'course-select' : 'main')"
        >
          <ArrowLeft :size="14" /> 返回
        </button>
        <span style="color:#ffd700;font-size:15px;letter-spacing:4px;">
          {{ PHASE_TITLES[phase] ?? '' }}
        </span>
        <div style="width:80px;" />
      </div>
    </Transition>

    <!-- ── Phase content ──────────────────────────────────────── -->
    <div
      class="absolute inset-0 flex"
      :style="{ paddingTop: phase !== 'main' ? '68px' : '0' }"
    >
      <Transition name="phase-fade" mode="out-in">

        <!-- MAIN MENU ─────────────────────────────────────────── -->
        <div
          v-if="phase === 'main'"
          key="main"
          class="flex w-full h-full items-center"
        >
          <!-- Right: vertical menu -->
          <div
            class="absolute right-16 top-1/2"
            style="transform:translateY(-50%);"
          >
            <nav class="flex flex-col gap-1">
              <button
                v-for="item in [
                  { label:'开 始 学 习', action: () => phase = 'world-select' },
                  { label:'档 案 管 理', action: () => router.push('/archive') },
                  { label:'角 色 管 理', action: () => phase = 'character-manage' },
                  { label:'系 统 设 置', action: () => router.push('/settings') },
                  { label:'退 出 登 录', action: handleLogout },
                ]"
                :key="item.label"
                class="galgame-menu-item text-right"
                @click="item.action()"
              >{{ item.label }}</button>
            </nav>
          </div>
        </div>

        <!-- WORLD SELECT ──────────────────────────────────────── -->
        <div
          v-else-if="phase === 'world-select'"
          key="world-select"
          class="w-full h-full overflow-y-auto galgame-scrollbar"
          style="padding:24px;"
        >
          <div v-if="worldStore.loading" style="color:rgba(255,255,255,0.5);text-align:center;margin-top:60px;">
            加载中…
          </div>
          <div
            v-else
            style="
              display:grid;
              grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
              gap:16px;max-width:900px;margin:0 auto;
            "
          >
            <div
              v-for="world in worldStore.worlds"
              :key="world.id"
              class="world-card"
              @click="selectWorld(world)"
            >
              <div
                :style="{
                  height: '120px',
                  backgroundImage: world.scenes?.background
                    ? `url(${world.scenes.background})`
                    : 'none',
                  background: world.scenes?.background ? undefined
                    : 'linear-gradient(135deg,#1e3a5f,#4c1d95)',
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                }"
              />
              <div style="padding:14px 16px;background:rgba(0,0,0,0.6);">
                <div class="font-ui" style="font-size:15px;color:#f0f0ff;letter-spacing:2px;margin-bottom:6px;">
                  {{ world.name }}
                </div>
                <div class="font-ui" style="font-size:12px;color:rgba(255,255,255,0.5);line-height:1.5;">
                  {{ world.description }}
                </div>
              </div>
            </div>

            <!-- Create new world -->
            <div
              class="world-card flex flex-col items-center justify-center gap-3"
              style="min-height:180px;cursor:pointer;"
              @click="showNewWorld = !showNewWorld"
            >
              <Plus :size="28" style="color:rgba(255,215,0,0.5);" />
              <span class="font-ui" style="font-size:13px;color:rgba(255,255,255,0.4);letter-spacing:2px;">
                创建新世界
              </span>
            </div>
          </div>

          <!-- Inline new world form -->
          <Transition name="fade">
            <div v-if="showNewWorld" class="galgame-panel" style="
              max-width:400px;margin:20px auto 0;padding:20px 24px;
            ">
              <div class="flex flex-col gap-3">
                <input
                  v-model="newWorldName"
                  class="galgame-input font-ui"
                  placeholder="世界名称"
                  style="padding:8px 12px;"
                />
                <textarea
                  v-model="newWorldDesc"
                  class="galgame-input font-ui"
                  placeholder="世界描述"
                  rows="2"
                  style="padding:8px 12px;resize:none;"
                />
                <div class="flex gap-2 justify-end">
                  <button class="galgame-hud-btn" @click="showNewWorld=false">取消</button>
                  <button class="galgame-send-btn font-ui" style="padding:6px 20px;" @click="handleCreateWorld">
                    创建
                  </button>
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <!-- COURSE SELECT ─────────────────────────────────────── -->
        <div
          v-else-if="phase === 'course-select'"
          key="course-select"
          class="w-full h-full flex items-end"
          style="padding-bottom:60px;"
        >
          <!-- Characters (decorative) -->
          <div class="absolute inset-0 flex items-end justify-center pointer-events-none"
            style="bottom:260px;">
            <div class="font-dialogue" style="font-size:80px;opacity:0.08;letter-spacing:20px;">
              {{ worldStore.selectedWorld?.name ?? '' }}
            </div>
          </div>

          <!-- Dialog box (course choices) -->
          <div class="w-full" style="padding:0 16px;">
            <div class="galgame-dialog" style="position:relative;">
              <!-- Name tag -->
              <div class="galgame-name-tag font-ui"
                style="position:absolute;top:-34px;left:28px;
                  padding:4px 18px 4px 14px;
                  clip-path:polygon(0 0,100% 0,calc(100% - 10px) 100%,0 100%);
                  font-size:14px;font-weight:600;letter-spacing:3px;color:#0a0a1e;">
                知者
              </div>
              <div style="padding:16px 28px 20px;">
                <p class="font-dialogue" style="font-size:18px;line-height:1.85;
                  color:#f0f0ff;margin-bottom:14px;">
                  「今天想学什么呢？选择一门课程，我们一起探索。」
                </p>
                <div class="flex flex-col gap-2">
                  <!-- Each course row: click left = learn, click 设计 = design page -->
                  <div
                    v-for="course in courses"
                    :key="course.id"
                    class="flex items-center gap-0"
                    style="border:1px solid rgba(255,215,0,0.1);transition:border-color 0.2s ease;"
                    @mouseenter="($event.currentTarget as HTMLElement).style.borderColor='rgba(255,215,0,0.3)'"
                    @mouseleave="($event.currentTarget as HTMLElement).style.borderColor='rgba(255,215,0,0.1)'"
                  >
                    <!-- Left: start learning -->
                    <button
                      class="galgame-choice font-ui text-left flex-1"
                      style="font-size:15px;color:#f0f0ff;border:none;border-radius:0;"
                      @click="selectCourse(course)"
                    >
                      <span style="color:rgba(255,215,0,0.6);margin-right:8px;">▸</span>
                      {{ course.name }}
                      <span style="color:rgba(255,255,255,0.35);font-size:12px;margin-left:8px;">
                        — {{ course.description }}
                      </span>
                    </button>

                    <!-- Divider -->
                    <div style="width:1px;height:28px;background:rgba(255,215,0,0.12);flex-shrink:0;" />

                    <!-- Right: go to course design (upload materials etc.) -->
                    <button
                      class="flex items-center gap-1 font-ui flex-shrink-0"
                      style="padding:0 16px;height:100%;color:rgba(255,215,0,0.5);font-size:11px;
                        letter-spacing:1px;cursor:pointer;white-space:nowrap;
                        transition:color 0.15s ease;background:transparent;border:none;"
                      title="课程设计：上传教材、AI 课时切分"
                      @mouseenter="($event.target as HTMLElement).style.color='rgba(255,215,0,0.9)'"
                      @mouseleave="($event.target as HTMLElement).style.color='rgba(255,215,0,0.5)'"
                      @click.stop="openCourseDesign(course)"
                    >
                      <Settings2 :size="11" />
                      设计
                    </button>
                  </div>

                  <!-- New course -->
                  <button
                    class="galgame-choice font-ui text-left"
                    style="font-size:14px;color:rgba(74,223,106,0.75);"
                    @click="showNewCourse = !showNewCourse; courseCreateErr = ''"
                  >
                    <span style="color:rgba(74,223,106,0.5);margin-right:8px;">＋</span>
                    新增课程
                  </button>

                  <button
                    class="galgame-choice font-ui text-left"
                    style="font-size:14px;color:rgba(96,165,250,0.8);"
                    @click="phase='world-select'"
                  >
                    <span style="color:rgba(96,165,250,0.6);margin-right:8px;">↩</span>
                    返回世界选择
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Inline new course form -->
          <Transition name="fade">
            <div v-if="showNewCourse" class="galgame-panel" style="
              max-width:400px;margin:20px auto 0;padding:20px 24px;
            ">
              <div class="flex flex-col gap-3">
                <input
                  v-model="newCourseName"
                  class="galgame-input font-ui"
                  placeholder="课程名称"
                  style="padding:8px 12px;"
                />
                <textarea
                  v-model="newCourseDesc"
                  class="galgame-input font-ui"
                  placeholder="课程描述"
                  rows="2"
                  style="padding:8px 12px;resize:none;"
                />
                <div class="flex gap-2 justify-end">
                  <button class="galgame-hud-btn" @click="showNewCourse=false">取消</button>
                  <button
                    class="galgame-send-btn font-ui"
                    style="padding:6px 20px;"
                    @click="handleCreateCourse"
                    :disabled="courseCreating"
                  >
                    创建
                  </button>
                </div>
                <div v-if="courseCreateErr" style="color:red;font-size:12px;margin-top:4px;">
                  {{ courseCreateErr }}
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <!-- MEMORY VAULT ──────────────────────────────────────── -->
        <div
          v-else-if="phase === 'memory-vault'"
          key="memory-vault"
          class="w-full h-full flex items-end"
          style="padding:0 16px 60px;"
        >
          <div class="w-full galgame-dialog" style="position:relative;">
            <div class="galgame-name-tag font-ui"
              style="position:absolute;top:-34px;left:28px;
                padding:4px 18px 4px 14px;
                clip-path:polygon(0 0,100% 0,calc(100% - 10px) 100%,0 100%);
                font-size:14px;font-weight:600;letter-spacing:3px;color:#0a0a1e;">
              记忆库
            </div>
            <div style="padding:16px 28px 20px;">
              <p class="font-dialogue" style="font-size:17px;color:#f0f0ff;margin-bottom:14px;">
                「检测到已有的记忆存档，是否从上次的节点继续？」
              </p>
              <div class="flex flex-col gap-2">
                <button
                  v-for="cp in checkpoints"
                  :key="cp.id"
                  class="galgame-choice font-ui text-left"
                  style="font-size:14px;"
                  @click="loadCheckpoint(cp)"
                >
                  <span style="color:rgba(255,215,0,0.6);margin-right:8px;">▸</span>
                  {{ cp.save_name }}
                  <span style="color:rgba(255,255,255,0.35);font-size:11px;margin-left:8px;">
                    {{ new Date(cp.created_at).toLocaleString('zh-CN') }}
                  </span>
                </button>
                <button
                  class="galgame-choice font-ui text-left"
                  style="font-size:14px;color:rgba(74,223,106,0.8);"
                  @click="startNewJourney"
                >
                  <span style="color:rgba(74,223,106,0.6);margin-right:8px;">✦</span>
                  全新旅途
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- CHARACTER MANAGE ──────────────────────────────────── -->
        <div
          v-else-if="phase === 'character-manage'"
          key="char-manage"
          class="w-full h-full overflow-y-auto galgame-scrollbar"
          style="padding:24px;"
        >
          <!-- Tab switch -->
          <div class="flex gap-4 mb-6">
            <button
              v-for="tab in (['sage', 'traveler'] as const)"
              :key="tab"
              class="galgame-hud-btn"
              :class="{ active: charTab === tab }"
              style="padding:6px 20px;font-size:13px;"
              @click="charTab = tab"
            >
              {{ tab === 'sage' ? '知　者' : '旅　者' }}
            </button>
          </div>

          <div style="color:rgba(255,255,255,0.4);font-size:13px;text-align:center;margin-top:40px;">
            角色管理功能正在接入后端 <code style="color:rgba(255,215,0,0.5);">/api/character</code> 接口
          </div>
        </div>

      </Transition>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-from, .fade-leave-to { opacity: 0; }
.fade-enter-active { transition: opacity 0.4s ease; }
.fade-leave-active  { transition: opacity 0.3s ease; }
.phase-fade-enter-from { opacity: 0; transform: translateX(16px); }
.phase-fade-enter-active { transition: opacity 0.35s ease, transform 0.35s ease; }
.phase-fade-leave-to { opacity: 0; transform: translateX(-16px); }
.phase-fade-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
</style>