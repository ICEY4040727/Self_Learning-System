<template>
  <div class="learning-page-v2" @click="hideUI ? (hideUI = false) : undefined">
    <!-- Scene background -->
    <div
      class="scene-bg"
      :style="{
        backgroundImage: store.sceneBackground ? `url(${store.sceneBackground})` : 'none',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }"
      @click="handleSceneClick"
    />
    <!-- Gradient + ambient micro-light -->
    <div class="scene-overlay"></div>

    <!-- Characters -->
    <Transition name="chars-fade">
      <div v-show="!hideUI || anyPanelOpen" class="characters-layer pointer-events-none">
        <!-- Sage (left) -->
        <div
          :style="{
            position: 'absolute',
            bottom: `${44 + 230}px`,
            left: '8%',
            transformOrigin: 'bottom center',
            transform: isTravelerTurn ? 'scale(0.68)' : 'scale(1.0)',
            transition: 'transform 0.5s cubic-bezier(0.34,1.56,0.64,1)',
            filter: charFilter,
          }"
        >
          <CharacterSprite
            :character="sageCharacter"
            :expression="store.sageExpression"
            position="left"
            :jump-key="store.sageJumpKey"
            :is-active="!isTravelerTurn"
          />
        </div>

        <!-- Traveler (right) -->
        <div
          :style="{
            position: 'absolute',
            bottom: `${44 + 230}px`,
            right: '8%',
            transformOrigin: 'bottom center',
            transform: isTravelerTurn ? 'scale(1.0)' : 'scale(0.62)',
            transition: 'transform 0.5s cubic-bezier(0.34,1.56,0.64,1)',
            filter: charFilter,
          }"
        >
          <CharacterSprite
            :character="travelerCharacter"
            expression="default"
            position="right"
            :jump-key="store.travelerJumpKey"
            :is-active="isTravelerTurn"
          />
        </div>
      </div>
    </Transition>

    <!-- Dialog box -->
    <Transition name="dialog-slide">
      <div
        v-show="!hideUI"
        class="dialog-layer"
        :style="{ bottom: `${44 + 10}px` }"
      >
        <div style="padding:0 16px;">
          <DialogBox
            :mode="store.mode"
            :speaker-name="store.sageName"
            :full-text="store.currentText"
            :choices="store.currentChoices"
            placeholder="输入你的想法……"
            :skip-signal="skipSignal"
            :typewriter-enabled="settings.typewriterOn"
            @continue="skipSignal++"
            @choice-select="(i) => store.chooseOption(store.currentChoices[i])"
            @input-send="store.sendMessage"
          />
        </div>
      </div>
    </Transition>

    <!-- HUD -->
    <Transition name="hud-slide">
      <div v-show="!hideUI" class="hud-layer">
        <HudBar
          :emotion="store.currentEmotion"
          :relationship-stage="store.relationshipStage"
          :mastery-percent="store.masteryPercent"
          :auto-mode="autoMode"
          @save="handleSave"
          @load="loadOpen = true"
          @skip="skipSignal++"
          @auto-toggle="autoMode = !autoMode"
          @backlog="backlogOpen = true"
          @knowledge-graph="openKnowledge"
          @settings="router.push('/settings')"
          @home="router.push('/home')"
          @open-memory-drawer="openMemoryDrawer"
        />
      </div>
    </Transition>

    <!-- Error banner -->
    <Transition name="err-fade">
      <div v-if="store.loadError" class="error-banner">
        {{ store.loadError }}
      </div>
    </Transition>

    <!-- Modals -->
    <BacklogPanel
      :is-open="backlogOpen"
      :messages="store.messages"
      @close="backlogOpen = false"
    />

    <SaveLoadPanel
      :is-open="saveOpen || loadOpen"
      :mode="loadOpen ? 'load' : 'save'"
      :checkpoints="checkpoints"
      @close="saveOpen = false; loadOpen = false"
      @save="handleSaveSlot"
      @load="handleLoadCheckpoint"
      @delete="handleDeleteCheckpoint"
    />

    <KnowledgeGraphModal
      :is-open="knowledgeOpen"
      :world-name="String(store.worldId ?? worldId)"
      :graph="store.knowledgeGraph"
      @close="knowledgeOpen = false"
    />

    <RelationshipStageOverlay
      :is-open="!!store.pendingStageEvent"
      :new-stage="store.pendingStageEvent ?? 'friend'"
      :sage-name="store.sageName"
      :special-dialogue="store.stageSpecialLine"
      @continue="store.dismissStageEvent"
    />

    <!-- v1.0 #191 Memory Facts Drawer -->
    <MemoryFactsDrawer
      :show="memoryDrawerOpen"
      :facts="memoryFacts"
      :stats="memoryStats"
      :loading="memoryLoading"
      @close="memoryDrawerOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useLearningStore } from '@/stores/learning'
import { useSettingsStore } from '@/stores/settings'
import CharacterSprite from '@/components/CharacterSprite.vue'
import DialogBox from '@/components/DialogBox.vue'
import HudBar from '@/components/HudBar.vue'
import BacklogPanel from '@/components/BacklogPanel.vue'
import SaveLoadPanel from '@/components/SaveLoadPanel.vue'
import KnowledgeGraphModal from '@/components/KnowledgeGraphModal.vue'
import RelationshipStageOverlay from '@/components/RelationshipStageOverlay.vue'
import MemoryFactsDrawer from '@/components/course/MemoryFactsDrawer.vue'
import { memoryApi } from '@/api/memory'
import type { Checkpoint } from '@/types'

const router = useRouter()
const route = useRoute()
const store = useLearningStore()
const settings = useSettingsStore()

const courseId = Number(route.query.courseId || route.params.courseId)
const worldId = Number(route.query.worldId)
const checkpointId = route.query.checkpointId
  ? Number(route.query.checkpointId) : undefined

const hideUI = ref(false)
const backlogOpen = ref(false)
const saveOpen = ref(false)
const loadOpen = ref(false)
const knowledgeOpen = ref(false)
const autoMode = ref(false)
const skipSignal = ref(0)
const checkpoints = ref<Checkpoint[]>([])

// v1.0 #191 Memory Facts Drawer state
const memoryDrawerOpen = ref(false)
const memoryFacts = ref<any[]>([])
const memoryStats = ref({ total: 0, by_type: {} as Record<string, number> })
const memoryLoading = ref(false)

// v1.0 #192 fetch memory facts
async function fetchMemoryFacts() {
  const cid = store.courseId
  if (!cid) return
  memoryLoading.value = true
  try {
    const res = await memoryApi.getMemoryFacts(cid)
    memoryFacts.value = res.facts
    memoryStats.value = { total: res.stats.total, by_type: res.stats.by_type }
  } catch (e) {
    console.error('Failed to fetch memory facts:', e)
  } finally {
    memoryLoading.value = false
  }
}

// Listen for memory:fresh event from store (Issue #192)
function onMemoryFresh() {
  fetchMemoryFacts()
}

// v1.0 #191 open memory drawer
async function openMemoryDrawer() {
  await fetchMemoryFacts()
  memoryDrawerOpen.value = true
}

const anyPanelOpen = computed(() =>
  backlogOpen.value || saveOpen.value || loadOpen.value ||
  knowledgeOpen.value || !!store.pendingStageEvent || memoryDrawerOpen.value
)

let autoTimer: ReturnType<typeof setTimeout> | null = null

watch(
  [autoMode, () => store.mode, () => store.thinking],
  ([auto, mode, thinking]) => {
    clearAutoTimer()
    if (auto && mode === 'speaking' && !thinking) {
      autoTimer = setTimeout(
        () => { if (store.mode === 'speaking') skipSignal.value++ },
        settings.autoModeDelay * 1000,
      )
    }
  },
)

function clearAutoTimer() {
  if (autoTimer) { clearTimeout(autoTimer); autoTimer = null }
}

onMounted(async () => {
  await store.startSession(courseId, worldId, checkpointId)
  checkpoints.value = await store.fetchCheckpoints()
  // v1.0 #192: listen for memory:fresh event
  window.addEventListener('memory:fresh', onMemoryFresh)
})

onBeforeUnmount(() => {
  clearAutoTimer()
  store.reset()
  window.removeEventListener('memory:fresh', onMemoryFresh)
})

const sageCharacter = computed(() => ({
  id: 0,
  name: store.sageName,
  type: 'sage' as const,
  color: '#4c1d95',
  accentColor: '#7c3aed',
  symbol: '知',
  title: '智者',
  sprites: store.sageSprites,
}))

const travelerCharacter = computed(() => ({
  id: 99,
  name: '我',
  type: 'traveler' as const,
  color: '#1e293b',
  accentColor: '#475569',
  symbol: '我',
  title: '旅者',
  sprites: store.travelerSprites,
}))

const isTravelerTurn = computed(
  () => store.mode === 'input' || store.mode === 'waiting',
)

const charFilter = computed(() =>
  anyPanelOpen.value ? 'brightness(0.4)' : 'none'
)

async function handleSave() {
  const name = `存档 ${new Date().toLocaleString('zh-CN', {
    month: 'numeric', day: 'numeric',
    hour: 'numeric', minute: 'numeric',
  })}`
  await store.createCheckpoint(name)
  checkpoints.value = await store.fetchCheckpoints()
}

async function handleSaveSlot(slot: number) {
  await store.createCheckpoint(`存档 ${slot + 1}`)
  checkpoints.value = await store.fetchCheckpoints()
  saveOpen.value = false
}

async function handleLoadCheckpoint(cp: Checkpoint) {
  loadOpen.value = false
  router.replace({
    path: '/learning',
    query: {
      worldId: String(store.worldId ?? worldId),
      courseId: String(store.courseId ?? courseId),
      checkpointId: String(cp.id),
    },
  })
  store.reset()
  await store.startSession(
    store.courseId ?? courseId,
    store.worldId ?? worldId,
    cp.id,
  )
  checkpoints.value = await store.fetchCheckpoints()
}

async function handleDeleteCheckpoint(id: number) {
  checkpoints.value = checkpoints.value.filter(c => c.id !== id)
}

// Knowledge graph disabled - P1 #185 will redesign based on memory_facts
// async function openKnowledge() { knowledgeOpen.value = true }

function handleSceneClick() {
  if (anyPanelOpen.value) return
  hideUI.value = !hideUI.value
}
</script>

<style scoped>
.learning-page-v2 {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #0a0a1e;
}

.scene-bg {
  position: absolute;
  inset: 0;
  animation: sceneBgIn 1.5s ease-out both;
}

@keyframes sceneBgIn {
  from { transform: scale(1.05); opacity: 0; }
  to   { transform: scale(1);    opacity: 1; }
}

.scene-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(to bottom, rgba(10,10,30,0.3) 0%, rgba(10,10,30,0.15) 40%, rgba(10,10,30,0.6) 100%),
    radial-gradient(ellipse at 30% 40%, rgba(255,215,0,0.025) 0%, transparent 55%),
    radial-gradient(ellipse at 70% 60%, rgba(96,165,250,0.025) 0%, transparent 55%);
}

.characters-layer {
  position: absolute;
  inset: 0;
}

.dialog-layer {
  position: absolute;
  left: 0;
  right: 0;
}

.hud-layer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
}

.error-banner {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(239,68,68,0.15);
  border: 1px solid rgba(239,68,68,0.4);
  padding: 8px 20px;
  font-family: var(--font-ui);
  font-size: 13px;
  color: #ef4444;
  white-space: nowrap;
  z-index: 100;
}

/* Transitions */
.dialog-slide-enter-from { transform: translateY(36px); }
.dialog-slide-enter-active { transition: transform 0.35s ease-out; }
.dialog-slide-leave-to { transform: translateY(36px); }
.dialog-slide-leave-active { transition: transform 0.3s ease-out; }

.hud-slide-enter-from { opacity: 0; transform: translateY(20px); }
.hud-slide-enter-active { transition: opacity 0.4s ease 0.2s, transform 0.4s ease 0.2s; }
.hud-slide-leave-to { opacity: 0; }
.hud-slide-leave-active { transition: opacity 0.3s ease; }

.chars-fade-enter-from { opacity: 0; }
.chars-fade-enter-active { transition: opacity 0.5s ease; }
.chars-fade-leave-to { opacity: 0; }
.chars-fade-leave-active { transition: opacity 0.3s ease; }

.err-fade-enter-from,
.err-fade-leave-to { opacity: 0; }
.err-fade-enter-active,
.err-fade-leave-active { transition: opacity 0.2s ease; }

.pointer-events-none {
  pointer-events: none;
}
</style>
