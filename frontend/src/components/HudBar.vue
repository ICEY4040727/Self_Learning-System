<script setup lang="ts">
import { computed } from 'vue'
import { EMOTION_COLORS, STAGE_LABELS } from '@/types'
import type { RelationshipStage } from '@/types'

const props = defineProps<{
  emotion: string
  relationshipStage: RelationshipStage
  masteryPercent: number
  autoMode: boolean
  motivation?: string  // v1.0 学习动机显示
}>()

const emit = defineEmits<{
  (e: 'save'): void
  (e: 'load'): void
  (e: 'skip'): void
  (e: 'autoToggle'): void
  (e: 'backlog'): void
  (e: 'knowledgeGraph'): void
  (e: 'settings'): void
  (e: 'home'): void
  (e: 'openMemoryDrawer'): void  // v1.0 打开 Memory 抽屉
}>()

const emotionColor = computed(
  () => EMOTION_COLORS[props.emotion] ?? '#aaaaaa'
)
const stageLabel = computed(() => STAGE_LABELS[props.relationshipStage])
</script>

<template>
  <div
    class="galgame-hud flex items-center justify-between"
    style="height:44px;padding:0 16px;"
  >
    <!-- Left: action buttons -->
    <div class="flex items-center gap-1">
      <button class="galgame-hud-btn flex items-center gap-1" @click="emit('save')">
        💾<span>存档</span>
      </button>
      <button class="galgame-hud-btn flex items-center gap-1" @click="emit('load')">
        📂<span>读档</span>
      </button>
      <button class="galgame-hud-btn flex items-center gap-1" @click="emit('skip')">
        ⏭<span>跳过</span>
      </button>
      <button
        class="galgame-hud-btn flex items-center gap-1"
        :class="{ active: autoMode }"
        @click="emit('autoToggle')"
      >
        ▶<span>自动</span>
        <span v-if="autoMode" style="color:#4adf6a;font-size:9px;">●</span>
      </button>
      <button class="galgame-hud-btn flex items-center gap-1" @click="emit('backlog')">
        📖<span>回忆</span>
      </button>
      <!-- v1.0 #191 Memory Drawer -->
      <button class="galgame-hud-btn flex items-center gap-1" @click="emit('openMemoryDrawer')">
        🧠<span>档案</span>
      </button>
      <!-- <button class="galgame-hud-btn flex items-center gap-1" @click="emit('knowledgeGraph')">🗺<span>知识图谱</span></button> P1 #185 -->
      <button class="galgame-hud-btn flex items-center gap-1" @click="emit('settings')">
        ⚙<span>设置</span>
      </button>
      <button class="galgame-hud-btn flex items-center gap-1" @click="emit('home')">
        🏠<span>返回主页</span>
      </button>
    </div>

    <!-- Right: status indicators -->
    <div class="flex items-center gap-3 font-ui" style="font-size:12px;">
      <!-- Emotion dot -->
      <div class="flex items-center gap-1">
        <div :style="{
          width: '6px', height: '6px', borderRadius: '50%',
          background: emotionColor,
          boxShadow: `0 0 6px ${emotionColor}`,
        }" />
        <span :style="{ color: emotionColor }">{{ emotion }}</span>
      </div>

      <span style="color:rgba(255,255,255,0.2);">|</span>

      <!-- Relationship stage -->
      <div class="flex items-center gap-1">
        <span style="color:rgba(255,215,0,0.6);">⏱</span>
        <span style="color:rgba(255,215,0,0.8);">{{ stageLabel }}</span>
      </div>

      <span style="color:rgba(255,255,255,0.2);">|</span>

      <!-- Mastery bar -->
      <div class="flex items-center gap-2">
        <div style="width:60px;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;overflow:hidden;">
          <div :style="{
            height: '100%',
            width: `${masteryPercent}%`,
            background: 'linear-gradient(90deg,#ffd700,#4adf6a)',
            borderRadius: '2px',
            transition: 'width 1s ease',
          }" />
        </div>
        <span style="color:rgba(255,255,255,0.55);">{{ masteryPercent }}%</span>
      </div>
    </div>
  </div>
</template>
