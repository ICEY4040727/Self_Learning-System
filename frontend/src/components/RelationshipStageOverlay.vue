<script setup lang="ts">
import type { RelationshipStage } from '@/types'
import { STAGE_LABELS, STAGE_COLORS } from '@/types'
import { computed } from 'vue'

const props = defineProps<{
  isOpen: boolean
  newStage: RelationshipStage
  sageName: string
  specialDialogue: string
}>()

const emit = defineEmits<{ (e: 'continue'): void }>()

const colors     = computed(() => STAGE_COLORS[props.newStage])
const stageLabel = computed(() => STAGE_LABELS[props.newStage])
</script>

<template>
  <Teleport to="body">
    <Transition name="overlay-fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex flex-col items-center justify-center"
        style="background:rgba(0,0,0,0.88);cursor:pointer;"
        @click="emit('continue')"
      >
        <!-- Ripple rings -->
        <div
          v-for="(_, i) in 3"
          :key="i"
          class="absolute"
          :style="{
            width:  `${200 + i * 120}px`,
            height: `${200 + i * 120}px`,
            borderRadius: '50%',
            border: `1px solid ${colors.primary}`,
            opacity: 0,
            animation: `goldRipple 2.5s ease-out ${i * 0.6}s infinite`,
          }"
        />

        <!-- Content -->
        <div
          class="flex flex-col items-center gap-6"
          style="animation:stageReveal 0.8s ease-out both;"
          @click.stop="emit('continue')"
        >
          <!-- Star row -->
          <div class="flex gap-3">
            <span
              v-for="(s, i) in ['✦','✧','✦','✧','✦']"
              :key="i"
              :style="{
                color: colors.primary, fontSize: '14px', opacity: 0.7,
                animation: `ambientPulse ${1 + i * 0.2}s ease-in-out ${i * 0.1}s infinite alternate`,
              }"
            >{{ s }}</span>
          </div>

          <!-- Stage label -->
          <div class="flex flex-col items-center gap-2">
            <span class="font-ui" style="font-size:12px;letter-spacing:4px;color:rgba(255,255,255,0.5);">
              — 关系进展 —
            </span>
            <span
              class="font-dialogue"
              :style="{
                fontSize: '36px', letterSpacing: '8px',
                color: colors.primary,
                textShadow: `0 0 30px ${colors.glow}, 0 0 60px ${colors.glow}`,
              }"
            >{{ stageLabel }}</span>
          </div>

          <!-- Special dialogue -->
          <div
            v-if="specialDialogue"
            class="galgame-dialog font-dialogue"
            style="
              max-width:500px; padding:16px 24px;
              font-size:16px; line-height:1.9;
              color:rgba(240,240,255,0.9); text-align:center;
            "
          >
            「{{ specialDialogue }}」
          </div>

          <span class="font-ui" style="font-size:11px;letter-spacing:2px;
            color:rgba(255,255,255,0.35);margin-top:8px;">
            点击任意处继续
          </span>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay-fade-enter-from,
.overlay-fade-leave-to { opacity: 0; }
.overlay-fade-enter-active { transition: opacity 0.4s ease; }
.overlay-fade-leave-active  { transition: opacity 0.3s ease; }
</style>
