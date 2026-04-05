<script setup lang="ts">
import { ref } from 'vue'
import { X } from 'lucide-vue-next'
import type { Checkpoint } from '@/types'

const props = defineProps<{
  isOpen: boolean
  mode: 'save' | 'load'
  checkpoints: Checkpoint[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', slot: number): void
  (e: 'load', checkpoint: Checkpoint): void
  (e: 'delete', id: number): void
}>()

const TOTAL_SLOTS = 6
const slots = Array.from({ length: TOTAL_SLOTS }, (_, i) => i)

const pendingDelete = ref<number | null>(null)

function getCheckpoint(slot: number): Checkpoint | null {
  return props.checkpoints[slot] ?? null
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function handleSlotClick(slot: number) {
  const cp = getCheckpoint(slot)
  if (props.mode === 'save') {
    emit('save', slot)
  } else {
    if (cp) emit('load', cp)
  }
}

const SCENE_GRADIENTS: Record<string, string> = {
  default: 'linear-gradient(135deg,#1a1a2e 0%,#16213e 100%)',
  academy: 'linear-gradient(135deg,#1e3a5f 0%,#4c1d95 100%)',
  garden:  'linear-gradient(135deg,#064e3b 0%,#1e3a5f 100%)',
  market:  'linear-gradient(135deg,#7c2d12 0%,#1e3a5f 100%)',
}
</script>

<template>
  <Teleport to="body">
    <Transition name="panel-in">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-40 flex items-center justify-center"
        style="background:rgba(0,0,0,0.7);"
        @click="emit('close')"
      >
        <div
          class="galgame-panel"
          style="width:600px;max-width:92vw;border-radius:16px;"
          @click.stop
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between font-ui"
            style="padding:16px 22px;border-bottom:1px solid rgba(255,215,0,0.15);"
          >
            <span style="color:#ffd700;font-size:15px;letter-spacing:3px;">
              {{ mode === 'save' ? '📁  存  档' : '📂  读  档' }}
            </span>
            <button
              style="color:rgba(255,255,255,0.5);cursor:pointer;"
              @click="emit('close')"
            ><X :size="18" /></button>
          </div>

          <!-- Slot grid -->
          <div
            style="
              padding:20px 22px 22px;
              display:grid;grid-template-columns:repeat(3,1fr);gap:12px;
            "
          >
            <div
              v-for="slot in slots"
              :key="slot"
              style="cursor:pointer;border-radius:8px;overflow:hidden;border:1px solid rgba(255,215,0,0.15);transition:all 0.2s ease;"
              class="hover-gold-border"
              @click="handleSlotClick(slot)"
            >
              <!-- Has checkpoint -->
              <template v-if="getCheckpoint(slot)">
                <div
                  :style="{
                    background: SCENE_GRADIENTS.default,
                    height: '80px', position: 'relative',
                  }"
                >
                  <div
                    class="font-ui"
                    style="
                      position:absolute;bottom:0;left:0;right:0;
                      padding:6px 8px;
                      background:linear-gradient(to top,rgba(0,0,0,0.8),transparent);
                      font-size:11px;color:rgba(255,255,255,0.8);
                    "
                  >{{ getCheckpoint(slot)!.save_name }}</div>
                </div>
                <div style="padding:8px 10px;background:rgba(0,0,0,0.4);">
                  <div class="font-ui" style="font-size:10px;color:rgba(255,215,0,0.7);">
                    {{ formatDate(getCheckpoint(slot)!.created_at) }}
                  </div>
                  <!-- Actions -->
                  <div class="flex gap-2 mt-2" @click.stop>
                    <button
                      v-if="mode === 'load'"
                      class="galgame-hud-btn"
                      style="font-size:10px;padding:2px 8px;"
                      @click="emit('load', getCheckpoint(slot)!)"
                    >读取</button>
                    <button
                      v-if="mode === 'save'"
                      class="galgame-hud-btn"
                      style="font-size:10px;padding:2px 8px;"
                      @click="emit('save', slot)"
                    >覆盖</button>
                    <button
                      class="galgame-hud-btn"
                      style="font-size:10px;padding:2px 8px;color:rgba(239,68,68,0.8);"
                      @click="emit('delete', getCheckpoint(slot)!.id)"
                    >删除</button>
                  </div>
                </div>
              </template>

              <!-- Empty slot -->
              <template v-else>
                <div
                  style="
                    height:120px; display:flex; flex-direction:column;
                    align-items:center; justify-content:center; gap:6px;
                    border:1px dashed rgba(255,215,0,0.12);
                    color:rgba(255,255,255,0.25); font-size:24px;
                  "
                >
                  <span>+</span>
                  <span
                    v-if="mode === 'save'"
                    class="font-ui"
                    style="font-size:10px;letter-spacing:1px;"
                  >存入此槽</span>
                  <span
                    v-else
                    class="font-ui"
                    style="font-size:10px;"
                  >空档位</span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.hover-gold-border:hover { border-color: rgba(255,215,0,0.55) !important; }
.panel-in-enter-from { opacity: 0; transform: scale(0.96) translateY(8px); }
.panel-in-enter-active { transition: opacity 0.3s ease-out, transform 0.3s ease-out; }
.panel-in-leave-to { opacity: 0; transform: scale(0.96) translateY(8px); }
.panel-in-leave-active { transition: opacity 0.25s ease-in, transform 0.25s ease-in; }
</style>
