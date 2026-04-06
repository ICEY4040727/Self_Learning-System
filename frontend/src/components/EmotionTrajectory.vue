<template>
  <div class="emotion-trajectory">
    <div class="chart-header">
      <h3>情感轨迹</h3>
      <select v-model="selectedSession" @change="fetchTrajectory">
        <option value="">选择会话</option>
        <option v-for="s in sessions" :key="s.id" :value="s.id">
          {{ formatDate(s.started_at) }} — {{ s.course_name || '会话 #' + s.id }}
        </option>
      </select>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="trajectoryData.length > 0" class="charts">
      <!-- Valence curve -->
      <div class="chart-container" ref="valenceChart"></div>
      <!-- Emotion distribution -->
      <div class="chart-container pie" ref="pieChart"></div>
    </div>

    <p v-else class="empty-text">选择一个会话查看情感轨迹</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import client from '@/api/client'
import { parseApiError } from '@/utils/error'
import * as echarts from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  MarkLineComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  LineChart, PieChart,
  TitleComponent, TooltipComponent, GridComponent, MarkLineComponent, LegendComponent,
  CanvasRenderer,
])


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

const sessions = ref<SessionItem[]>([])
const selectedSession = ref<number | string>('')
const trajectoryData = ref<EmotionPoint[]>([])
const loading = ref(false)

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

const formatDate = (d: string) => {
  const date = new Date(d)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
}

const fetchSessions = async () => {
  try {
    const params = props.courseId ? `?course_id=${props.courseId}` : ''
    const { data } = await client.get(`/api/sessions${params}`, )
    sessions.value = data
  } catch {
    // endpoint may not exist yet; silently skip
  }
}

const fetchTrajectory = async () => {
  if (!selectedSession.value) return
  loading.value = true
  try {
    const { data } = await client.get(
      `/api/sessions/${selectedSession.value}/emotion_trajectory`,
      
    )
    trajectoryData.value = data
    await nextTick()
    renderCharts()
  } catch (error) {
    console.error(parseApiError(error))
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  renderValenceChart()
  renderPieChart()
}

const renderValenceChart = () => {
  if (!valenceChart.value || trajectoryData.value.length === 0) return

  if (valenceInstance) valenceInstance.dispose()
  valenceInstance = echarts.init(valenceChart.value)

  const data = trajectoryData.value
  const xData = data.map(d => `#${d.index}`)
  const valenceData = data.map(d => d.valence)
  const colors = data.map(d => EMOTION_COLORS[d.emotion_type] || '#aaa')

  valenceInstance.setOption({
    title: { text: '情感效价曲线', textStyle: { color: '#ffd700', fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = params[0]
        const d = data[p.dataIndex]
        const label = EMOTION_LABELS[d.emotion_type] || d.emotion_type
        return `第 ${d.index} 轮<br/>情感: ${label}<br/>效价: ${d.valence}<br/>唤醒度: ${d.arousal}`
      },
    },
    xAxis: {
      data: xData,
      axisLabel: { color: '#888' },
      axisLine: { lineStyle: { color: '#4a4a8a' } },
    },
    yAxis: {
      min: 0, max: 1,
      name: '效价',
      nameTextStyle: { color: '#888' },
      axisLabel: { color: '#888' },
      splitLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [{
      type: 'line',
      data: valenceData,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#ffd700', width: 2 },
      itemStyle: {
        color: (params: any) => colors[params.dataIndex],
        borderColor: '#ffd700',
        borderWidth: 1,
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(255, 215, 0, 0.3)' },
          { offset: 1, color: 'rgba(255, 215, 0, 0.0)' },
        ]),
      },
      markLine: {
        silent: true,
        data: [{ yAxis: 0.5, lineStyle: { color: '#4a4a8a', type: 'dashed' } }],
        label: { show: false },
      },
    }],
    backgroundColor: 'transparent',
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
  })
}

const renderPieChart = () => {
  if (!pieChart.value || trajectoryData.value.length === 0) return

  if (pieInstance) pieInstance.dispose()
  pieInstance = echarts.init(pieChart.value)

  // Count emotion types
  const counts: Record<string, number> = {}
  for (const d of trajectoryData.value) {
    counts[d.emotion_type] = (counts[d.emotion_type] || 0) + 1
  }

  const pieData = Object.entries(counts).map(([name, value]) => ({
    name: EMOTION_LABELS[name] || name,
    value,
    itemStyle: { color: EMOTION_COLORS[name] || '#aaa' },
  }))

  pieInstance.setOption({
    title: { text: '情绪分布', textStyle: { color: '#ffd700', fontSize: 14 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '55%'],
      data: pieData,
      label: { color: '#ccc', fontSize: 12 },
      emphasis: { label: { fontSize: 14, fontWeight: 'bold' } },
    }],
    backgroundColor: 'transparent',
  })
}

// Resize charts on window resize
const handleResize = () => {
  valenceInstance?.resize()
  pieInstance?.resize()
}

onMounted(() => {
  fetchSessions()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  valenceInstance?.dispose()
  pieInstance?.dispose()
  valenceInstance = null
  pieInstance = null
})

const props = defineProps<{
  courseId?: number
}>()
</script>

<style scoped>
.emotion-trajectory {
  background: rgba(0, 0, 0, 0.5);
  border: 2px solid #4a4a8a;
  border-radius: 12px;
  padding: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.chart-header h3 {
  color: #ffd700;
}

.chart-header select {
  padding: 6px 12px;
  background: #1a1a2e;
  border: 1px solid #4a4a8a;
  border-radius: 6px;
  color: #fff;
}

.charts {
  display: flex;
  gap: 15px;
}

.chart-container {
  flex: 2;
  height: 280px;
}

.chart-container.pie {
  flex: 1;
  height: 280px;
}

.loading {
  text-align: center;
  color: #888;
  padding: 40px;
}

.empty-text {
  text-align: center;
  color: #666;
  padding: 40px;
}

@media (max-width: 768px) {
  .charts {
    flex-direction: column;
  }
  .chart-container, .chart-container.pie {
    flex: none;
    height: 240px;
  }
}
</style>
