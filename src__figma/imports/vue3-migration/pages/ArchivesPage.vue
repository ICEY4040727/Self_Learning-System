<script setup lang="ts">
/**
 * ArchivesPage.vue
 * ──────────────────────────────────────────────────────────────
 * Contract adaptation §7:
 *   POST /api/learning_diary requires:
 *     - course_id  (int, required — backend validates ownership)
 *     - date       (ISO 8601 datetime string, not date-only)
 *   Without course_id the backend returns 422/404.
 * ──────────────────────────────────────────────────────────────
 */
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, PenLine } from 'lucide-vue-next'
import { Line, Pie } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement,
  ArcElement, Tooltip, Legend, Filler,
} from 'chart.js'
import client from '@/api/client'
import type { DiaryEntry, DiaryCreatePayload, EmotionDataPoint, ProgressItem, Course } from '@/types'
import ParticleBackground from '@/components/ParticleBackground.vue'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  ArcElement, Tooltip, Legend, Filler,
)

const router = useRouter()
const BG_URL = 'https://images.unsplash.com/photo-1675371708731-50d9c04eb530?w=1920&q=80'

// ── State ─────────────────────────────────────────────────────
const sessions = ref<{ id: number; started_at: string; course_name: string }[]>([])
const selectedSessionId  = ref<number | null>(null)
const emotionData        = ref<EmotionDataPoint[]>([])
const progressItems      = ref<ProgressItem[]>([])
const diaryEntries       = ref<DiaryEntry[]>([])
const courses            = ref<Course[]>([])        // §7: needed for diary course_id
const loading            = ref(true)

// §7: diary form state
const diaryOpen          = ref(false)
const diaryContent       = ref('')
const diaryReflection    = ref('')
// §7: course_id selector for diary submission
const diaryCourseId      = ref<number | null>(null)
const diarySubmitting    = ref(false)
const diaryError         = ref('')

// Progress filter
const selectedCourseId   = ref<number | null>(null)

// ── Fetch ─────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    fetchSessions(),
    fetchProgress(),
    fetchDiary(),
    fetchCourses(),    // §7: fetch courses for diary selector
  ])
  loading.value = false
})

async function fetchCourses() {
  try {
    const { data } = await client.get<Course[]>('/courses')
    courses.value = data
    // Pre-select first course for diary
    if (data.length > 0) diaryCourseId.value = data[0].id
  } catch {}
}

async function fetchSessions() {
  try {
    const { data } = await client.get('/sessions')
    sessions.value = data
    if (data.length > 0) {
      selectedSessionId.value = data[0].id
      await fetchEmotionTrajectory(data[0].id)
    }
  } catch {}
}

async function fetchEmotionTrajectory(sessionId: number) {
  try {
    const { data } = await client.get<EmotionDataPoint[]>(
      `/sessions/${sessionId}/emotion_trajectory`,
    )
    emotionData.value = data
  } catch {}
}

async function fetchProgress() {
  try {
    const params = selectedCourseId.value ? { course_id: selectedCourseId.value } : {}
    const { data } = await client.get<ProgressItem[]>('/progress', { params })
    progressItems.value = data
  } catch {}
}

async function fetchDiary() {
  try {
    const { data } = await client.get<DiaryEntry[]>('/learning_diary')
    diaryEntries.value = data
  } catch {}
}

async function handleSessionChange(id: number) {
  selectedSessionId.value = id
  await fetchEmotionTrajectory(id)
}

/**
 * §7: diary payload must include course_id (int) and date as ISO datetime.
 *   POST /learning_diary validates: Course belongs to current_user via world.user_id.
 *   Missing course_id → 422.  Course not found for user → 404.
 */
async function submitDiary() {
  if (!diaryContent.value.trim()) return
  if (!diaryCourseId.value) {
    diaryError.value = '请选择关联课程'
    return
  }

  diarySubmitting.value = true
  diaryError.value = ''

  const payload: DiaryCreatePayload = {
    course_id:  diaryCourseId.value,
    date:       new Date().toISOString(),   // §7: ISO 8601 datetime, not date-only
    content:    diaryContent.value.trim(),
    ...(diaryReflection.value.trim()
      ? { reflection: diaryReflection.value.trim() }
      : {}),
  }

  try {
    await client.post('/learning_diary', payload)
    diaryContent.value    = ''
    diaryReflection.value = ''
    diaryOpen.value       = false
    await fetchDiary()
  } catch (e: any) {
    diaryError.value = e?.response?.data?.detail ?? '提交失败'
  } finally {
    diarySubmitting.value = false
  }
}

// ── Chart data ────────────────────────────────────────────────
const lineChartData = computed(() => ({
  labels: emotionData.value.map(d => `#${d.index}`),
  datasets: [
    {
      label: '效价',
      data: emotionData.value.map(d => d.valence),
      borderColor: '#ffd700', backgroundColor: 'rgba(255,215,0,0.1)',
      tension: 0.4, fill: true,
    },
    {
      label: '唤醒度',
      data: emotionData.value.map(d => d.arousal),
      borderColor: '#60a5fa', backgroundColor: 'rgba(96,165,250,0.1)',
      tension: 0.4, fill: true,
    },
  ],
}))

const EMOTION_TYPE_COLORS: Record<string, string> = {
  curiosity: '#60a5fa', excitement: '#ffd700', happy: '#ffd700',
  confusion: '#f97316', satisfaction: '#4adf6a',
  frustration: '#ef4444', anticipation: '#a78bfa', neutral: '#aaaaaa',
}

const pieChartData = computed(() => {
  const counts: Record<string, number> = {}
  emotionData.value.forEach(d => {
    counts[d.emotion_type] = (counts[d.emotion_type] ?? 0) + 1
  })
  const labels = Object.keys(counts)
  return {
    labels,
    datasets: [{
      data: labels.map(l => counts[l]),
      backgroundColor: labels.map(l => EMOTION_TYPE_COLORS[l] ?? '#aaaaaa'),
    }],
  }
})

const CHART_OPTIONS = {
  responsive: true,
  plugins: {
    legend: { labels: { color: 'rgba(255,255,255,0.6)', font: { size: 11 } } },
  },
  scales: {
    x: {
      ticks: { color: 'rgba(255,255,255,0.4)' },
      grid:  { color: 'rgba(255,255,255,0.05)' },
    },
    y: {
      ticks: { color: 'rgba(255,255,255,0.4)' },
      grid:  { color: 'rgba(255,255,255,0.05)' },
      min: 0, max: 1,
    },
  },
}
</script>

<template>
  <div
    class="relative w-screen h-screen overflow-hidden"
    style="background:#0a0a1e;"
  >
    <div class="absolute inset-0"
      :style="{ backgroundImage:`url(${BG_URL})`, backgroundSize:'cover',
                backgroundPosition:'center', opacity:0.08 }" />
    <div class="absolute inset-0" style="background:linear-gradient(to bottom,
      rgba(10,10,30,0.95) 0%,rgba(10,10,30,0.98) 100%);" />
    <ParticleBackground :count="16" :gold-ratio="0.5" />

    <!-- Header -->
    <div
      class="absolute top-0 left-0 right-0 flex items-center justify-between font-ui"
      style="padding:16px 24px;border-bottom:1px solid rgba(255,215,0,0.1);z-index:10;"
    >
      <button
        class="flex items-center gap-2 galgame-hud-btn"
        style="font-size:13px;padding:6px 14px;"
        @click="router.push('/home')"
      >
        <ArrowLeft :size="14" /> 返回
      </button>
      <span style="color:#ffd700;font-size:16px;letter-spacing:4px;">档 案 管 理</span>
      <div style="width:80px;" />
    </div>

    <!-- Content -->
    <div
      class="absolute inset-0 overflow-y-auto galgame-scrollbar"
      style="padding-top:68px;padding-bottom:32px;padding-left:24px;padding-right:24px;"
    >
      <div style="max-width:900px;margin:0 auto;" class="flex flex-col gap-6">

        <div v-if="loading" class="font-ui" style="color:rgba(255,255,255,0.4);text-align:center;margin-top:60px;">
          加载中…
        </div>

        <template v-else>
          <!-- Emotion trajectory -->
          <div class="galgame-panel" style="padding:20px 24px;">
            <div class="flex items-center justify-between mb-4">
              <span class="font-ui" style="color:#ffd700;font-size:14px;letter-spacing:2px;">📈 情感轨迹</span>
              <select
                v-if="sessions.length > 0"
                class="galgame-input font-ui"
                style="padding:4px 10px;font-size:12px;width:auto;"
                @change="handleSessionChange(Number(($event.target as HTMLSelectElement).value))"
              >
                <option
                  v-for="s in sessions"
                  :key="s.id"
                  :value="s.id"
                >{{ new Date(s.started_at).toLocaleDateString('zh-CN') }} · {{ s.course_name }}</option>
              </select>
            </div>
            <div v-if="emotionData.length === 0"
              style="color:rgba(255,255,255,0.3);text-align:center;padding:40px 0;font-size:13px;">
              暂无情感记录
            </div>
            <Line v-else :data="lineChartData" :options="CHART_OPTIONS" style="max-height:240px;" />
          </div>

          <!-- Two columns: pie + progress -->
          <div class="flex gap-6" style="align-items:flex-start;flex-wrap:wrap;">
            <!-- Emotion pie -->
            <div class="galgame-panel" style="padding:20px 24px;flex:1;min-width:200px;">
              <div class="font-ui mb-4" style="color:#ffd700;font-size:14px;letter-spacing:2px;">情感分布</div>
              <div v-if="emotionData.length === 0"
                style="color:rgba(255,255,255,0.3);text-align:center;padding:30px 0;font-size:13px;">
                暂无数据
              </div>
              <Pie
                v-else
                :data="pieChartData"
                :options="{
                  responsive: true,
                  plugins: { legend: { labels: { color:'rgba(255,255,255,0.6)', font:{ size:11 } } } },
                }"
              />
            </div>

            <!-- Concept mastery -->
            <div class="galgame-panel" style="padding:20px 24px;flex:1;min-width:200px;">
              <div class="flex items-center justify-between mb-4">
                <span class="font-ui" style="color:#ffd700;font-size:14px;letter-spacing:2px;">📚 概念掌握</span>
                <select
                  v-if="courses.length > 0"
                  class="galgame-input font-ui"
                  style="padding:4px 8px;font-size:11px;width:auto;"
                  @change="selectedCourseId = Number(($event.target as HTMLSelectElement).value) || null; fetchProgress()"
                >
                  <option value="">全部</option>
                  <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
              </div>
              <div v-if="progressItems.length === 0"
                style="color:rgba(255,255,255,0.3);text-align:center;padding:30px 0;font-size:13px;">
                暂无进度数据
              </div>
              <div
                v-for="item in progressItems"
                :key="item.id"
                class="flex flex-col gap-1 mb-4"
              >
                <div class="flex justify-between font-ui" style="font-size:12px;">
                  <span style="color:rgba(255,255,255,0.8);">{{ item.topic }}</span>
                  <span style="color:rgba(255,215,0,0.7);">{{ Math.round(item.mastery_level * 100) }}%</span>
                </div>
                <div style="height:4px;background:rgba(255,255,255,0.08);border-radius:2px;overflow:hidden;">
                  <div :style="{
                    height:'100%',
                    width: `${item.mastery_level * 100}%`,
                    background: 'linear-gradient(90deg,#ffd700,#4adf6a)',
                    transition: 'width 0.8s ease',
                  }" />
                </div>
                <div class="font-ui" style="font-size:10px;color:rgba(255,255,255,0.3);">
                  下次复习：{{ item.next_review }}
                </div>
              </div>
            </div>
          </div>

          <!-- Diary -->
          <div class="galgame-panel" style="padding:20px 24px;">
            <div class="flex items-center justify-between mb-4">
              <span class="font-ui" style="color:#ffd700;font-size:14px;letter-spacing:2px;">📓 学习日记</span>
              <button
                class="galgame-hud-btn flex items-center gap-1"
                @click="diaryOpen = !diaryOpen; diaryError = ''"
              >
                <PenLine :size="12" /> 写日记
              </button>
            </div>

            <!-- §7: diary write form with required course_id -->
            <Transition name="diary-slide">
              <div v-if="diaryOpen" class="mb-6 flex flex-col gap-3">

                <!-- Course selector (§7 required) -->
                <div class="flex flex-col gap-1">
                  <label class="font-ui" style="font-size:11px;color:rgba(255,215,0,0.6);letter-spacing:1px;">
                    关联课程 <span style="color:#ef4444;">*</span>
                  </label>
                  <select
                    v-model="diaryCourseId"
                    class="galgame-input font-ui"
                    style="padding:8px 12px;font-size:13px;"
                  >
                    <option :value="null" disabled>请选择课程…</option>
                    <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}</option>
                  </select>
                </div>

                <!-- Content -->
                <textarea
                  v-model="diaryContent"
                  class="galgame-input font-dialogue w-full"
                  placeholder="今天的感悟…"
                  rows="3"
                  style="padding:10px 14px;font-size:15px;resize:none;"
                />

                <!-- Reflection (optional) -->
                <textarea
                  v-model="diaryReflection"
                  class="galgame-input font-dialogue w-full"
                  placeholder="反思与总结（选填）…"
                  rows="2"
                  style="padding:10px 14px;font-size:14px;resize:none;"
                />

                <!-- Error -->
                <Transition name="err-fade">
                  <p v-if="diaryError" class="font-ui" style="font-size:12px;color:#ef4444;">
                    {{ diaryError }}
                  </p>
                </Transition>

                <div class="flex gap-2 justify-end">
                  <button class="galgame-hud-btn" @click="diaryOpen=false;diaryError=''">取消</button>
                  <button
                    class="galgame-send-btn font-ui"
                    style="padding:6px 20px;"
                    :disabled="diarySubmitting || !diaryCourseId"
                    @click="submitDiary"
                  >
                    {{ diarySubmitting ? '提交中…' : '提交' }}
                  </button>
                </div>
              </div>
            </Transition>

            <div v-if="diaryEntries.length === 0"
              class="font-ui" style="color:rgba(255,255,255,0.3);font-size:13px;">
              暂无日记
            </div>
            <div
              v-for="entry in diaryEntries"
              :key="entry.id"
              style="border-bottom:1px solid rgba(255,215,0,0.08);padding:12px 0;"
            >
              <div class="font-ui" style="font-size:11px;color:rgba(255,215,0,0.6);margin-bottom:6px;">
                {{ new Date(entry.date).toLocaleDateString('zh-CN') }}
              </div>
              <p class="font-dialogue" style="font-size:14px;line-height:1.85;color:rgba(240,240,255,0.8);">
                {{ entry.content }}
              </p>
              <p v-if="entry.reflection"
                class="font-dialogue"
                style="font-size:13px;line-height:1.7;color:rgba(255,255,255,0.45);margin-top:6px;
                  border-left:2px solid rgba(255,215,0,0.2);padding-left:10px;">
                {{ entry.reflection }}
              </p>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.diary-slide-enter-from { opacity: 0; transform: translateY(-8px); }
.diary-slide-enter-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.diary-slide-leave-to { opacity: 0; transform: translateY(-8px); }
.diary-slide-leave-active { transition: opacity 0.2s ease; }
.err-fade-enter-from, .err-fade-leave-to { opacity: 0; }
.err-fade-enter-active, .err-fade-leave-active { transition: opacity 0.2s ease; }
</style>
