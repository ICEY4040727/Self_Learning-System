<template>
  <div class="emotion-trajectory">
    <div class="chart-header">
      <h3>情感轨迹</h3>
      <select v-model.number="selectedSession" class="galgame-input" @change="fetchTrajectory">
        <option :value="0">选择会话</option>
        <option v-for="session in sessions" :key="session.id" :value="session.id">
          {{ formatDate(session.started_at) }} — {{ session.course_name || `会话 #${session.id}` }}
        </option>
      </select>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <div v-else-if="loading" class="status-text">加载中...</div>
    <p v-else-if="sessions.length === 0" class="status-text">暂无会话记录</p>
    <p v-else-if="trajectoryData.length === 0" class="status-text">该会话暂无情感轨迹</p>

    <div v-else class="charts">
      <div ref="valenceChart" class="chart-container"></div>
      <div ref="pieChart" class="chart-container pie"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import axios from 'axios'
import { parseApiError } from '@/utils/error'
import * as echarts from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useAuthStore } from '@/stores/auth'

echarts.use([LineChart, PieChart, TitleComponent, TooltipComponent, GridComponent, MarkLineComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{
  courseId?: number
}>()

interface SessionItem {
  id: number
  started_at: string
  course_name?: string
}

interface EmotionPoint {
  index: number
  timestamp: string
  emotion_type: string
  valence: number
  arousal: number
  confidence: number
}

const authStore = useAuthStore()
const sessions = ref<SessionItem[]>([])
const selectedSession = ref(0)
const trajectoryData = ref<EmotionPoint[]>([])
const loading = ref(false)
const errorMessage = ref('')

const valenceChart = ref<HTMLElement | null>(null)
const pieChart = ref<HTMLElement | null>(null)

let valenceInstance: echarts.ECharts | null = null
let pieInstance: echarts.ECharts | null = null

const EMOTION_COLORS: Record<string, string> = {
  curiosity: '#4adf6a',
  excitement: '#ffd700',
  satisfaction: '#4a9adf',
  confusion: '#df8a4a',
  frustration: '#df4a4a',
  anxiety: '#df4adf',
  boredom: '#8a8a8a',
  neutral: '#aaaaaa',
}

const EMOTION_LABELS: Record<string, string> = {
  curiosity: '好奇',
  excitement: '兴奋',
  satisfaction: '满足',
  confusion: '困惑',
  frustration: '沮丧',
  anxiety: '焦虑',
  boredom: '无聊',
  neutral: '平静',
}

const headers = () => ({ Authorization: `Bearer ${authStore.token}` })

const formatDate = (dateTime: string) => {
  const date = new Date(dateTime)
  if (Number.isNaN(date.getTime())) return dateTime
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

const fetchSessions = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await axios.get('/api/sessions', {
      params: { course_id: props.courseId },
      headers: headers(),
    })
    sessions.value = Array.isArray(response.data) ? response.data : []

    if (sessions.value.length === 0) {
      selectedSession.value = 0
      trajectoryData.value = []
      return
    }

    const stillExists = sessions.value.some((session) => session.id === selectedSession.value)
    if (!stillExists) selectedSession.value = sessions.value[0].id
    await fetchTrajectory()
  } catch (error) {
    errorMessage.value = parseApiError(error)
  } finally {
    loading.value = false
  }
}

const fetchTrajectory = async () => {
  if (!selectedSession.value) {
    trajectoryData.value = []
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    const response = await axios.get(`/api/sessions/${selectedSession.value}/emotion_trajectory`, { headers: headers() })
    trajectoryData.value = Array.isArray(response.data) ? response.data : []
    await nextTick()
    renderCharts()
  } catch (error) {
    errorMessage.value = parseApiError(error)
    trajectoryData.value = []
  } finally {
    loading.value = false
  }
}

const renderValenceChart = () => {
  if (!valenceChart.value || trajectoryData.value.length === 0) return

  valenceInstance?.dispose()
  valenceInstance = echarts.init(valenceChart.value)

  const xData = trajectoryData.value.map((point) => `#${point.index}`)
  const valenceData = trajectoryData.value.map((point) => point.valence)

  valenceInstance.setOption({
    title: { text: '情感效价曲线', textStyle: { color: '#ffd700', fontSize: 13 } },
    tooltip: {
      trigger: 'axis',
      formatter: (params: { dataIndex: number }[]) => {
        const row = trajectoryData.value[params[0].dataIndex]
        return `第 ${row.index} 轮<br/>情感：${EMOTION_LABELS[row.emotion_type] || row.emotion_type}<br/>效价：${row.valence}<br/>唤醒：${row.arousal}`
      },
    },
    xAxis: {
      data: xData,
      axisLabel: { color: 'rgba(255,255,255,0.45)' },
      axisLine: { lineStyle: { color: 'rgba(74,74,138,0.7)' } },
    },
    yAxis: {
      min: 0,
      max: 1,
      axisLabel: { color: 'rgba(255,255,255,0.45)' },
      splitLine: { lineStyle: { color: 'rgba(74,74,138,0.35)' } },
    },
    series: [{
      type: 'line',
      data: valenceData,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#ffd700', width: 2 },
      itemStyle: {
        color: (params: { dataIndex: number }) => {
          const point = trajectoryData.value[params.dataIndex]
          return EMOTION_COLORS[point.emotion_type] || '#aaaaaa'
        },
        borderColor: '#ffd700',
        borderWidth: 1,
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(255, 215, 0, 0.25)' },
          { offset: 1, color: 'rgba(255, 215, 0, 0.0)' },
        ]),
      },
      markLine: {
        silent: true,
        label: { show: false },
        data: [{ yAxis: 0.5, lineStyle: { color: '#4a4a8a', type: 'dashed' } }],
      },
    }],
    backgroundColor: 'transparent',
    grid: { left: 48, right: 18, top: 38, bottom: 30 },
  })
}

const renderPieChart = () => {
  if (!pieChart.value || trajectoryData.value.length === 0) return

  pieInstance?.dispose()
  pieInstance = echarts.init(pieChart.value)

  const counts: Record<string, number> = {}
  for (const row of trajectoryData.value) {
    counts[row.emotion_type] = (counts[row.emotion_type] || 0) + 1
  }

  pieInstance.setOption({
    title: { text: '情感分布', textStyle: { color: '#ffd700', fontSize: 13 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '56%'],
      data: Object.entries(counts).map(([name, value]) => ({
        name: EMOTION_LABELS[name] || name,
        value,
        itemStyle: { color: EMOTION_COLORS[name] || '#aaaaaa' },
      })),
      label: { color: 'rgba(255,255,255,0.68)', fontSize: 11 },
    }],
    backgroundColor: 'transparent',
  })
}

const renderCharts = () => {
  renderValenceChart()
  renderPieChart()
}

const handleResize = () => {
  valenceInstance?.resize()
  pieInstance?.resize()
}

watch(
  () => props.courseId,
  () => {
    selectedSession.value = 0
    trajectoryData.value = []
    void fetchSessions()
  },
)

onMounted(() => {
  void fetchSessions()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  valenceInstance?.dispose()
  pieInstance?.dispose()
  valenceInstance = null
  pieInstance = null
})
</script>

<style scoped>
.emotion-trajectory {
  padding: 0;
}

.chart-header {
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.chart-header h3 {
  color: rgba(255, 255, 255, 0.42);
  font-size: 12px;
  letter-spacing: 3px;
  text-transform: uppercase;
}

.chart-header select {
  min-width: 240px;
  padding: 7px 8px;
}

.charts {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
}

.chart-container {
  height: 280px;
  border: 1px solid rgba(74, 74, 138, 0.5);
  border-radius: var(--radius-world-card);
  background: radial-gradient(circle at 40% 25%, #1f1f38 0%, #121225 100%);
}

.chart-container.pie {
  min-width: 250px;
}

.status-text {
  color: rgba(255, 255, 255, 0.45);
  text-align: center;
  padding: 26px 0;
  font-size: 13px;
}

.error-text {
  color: #ff9f9f;
  border: 1px solid rgba(223, 74, 74, 0.45);
  background: rgba(223, 74, 74, 0.15);
  padding: 8px 10px;
  margin-bottom: 10px;
  font-size: 13px;
}

@media (max-width: 900px) {
  .charts {
    grid-template-columns: 1fr;
  }

  .chart-container,
  .chart-container.pie {
    min-width: 0;
    height: 240px;
  }

  .chart-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .chart-header select {
    width: 100%;
    min-width: 0;
  }
}
</style>
