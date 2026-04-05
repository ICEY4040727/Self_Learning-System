<script setup lang="ts">
import type { Character, Expression } from '@/types'
import { EXPRESSION_SYMBOLS, EXPRESSION_COLORS } from '@/types'
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  character: Character
  expression: Expression
  position: 'left' | 'right'
  jumpKey: number
  isActive: boolean
  scale?: number
}>(), { scale: 1 })

const isSage        = computed(() => props.character.type === 'sage')
const spriteWidth   = computed(() => isSage.value ? 170 : 140)
const spriteHeight  = computed(() => isSage.value ? 340 : 280)
const symbolSize    = computed(() => spriteWidth.value * props.scale * 0.45)

const outerStyle = computed(() => ({
  width:  `${spriteWidth.value  * props.scale}px`,
  height: `${spriteHeight.value * props.scale}px`,
  animation: 'jumpOnce 0.35s ease-out',
  filter: props.isActive
    ? `drop-shadow(0 0 18px ${props.character.accentColor ?? '#7c3aed'}80)
       drop-shadow(0 0 36px ${props.character.accentColor ?? '#7c3aed'}30)`
    : 'drop-shadow(0 4px 16px rgba(0,0,0,0.7))',
  transition: 'filter 0.4s ease',
  transformOrigin: 'bottom center',
}))

const frameStyle = computed(() => ({
  width: '100%', height: '100%',
  position: 'relative' as const,
  borderRadius: '8px 8px 0 0',
  overflow: 'hidden' as const,
  border: props.isActive
    ? `1px solid ${props.character.accentColor ?? '#7c3aed'}80`
    : '1px solid rgba(255,255,255,0.08)',
  boxShadow: props.isActive
    ? `0 0 20px ${props.character.accentColor ?? '#7c3aed'}40,
       inset 0 0 20px ${props.character.accentColor ?? '#7c3aed'}10`
    : 'none',
  transition: 'all 0.4s ease',
}))

const nameColor   = computed(() =>
  props.isActive ? '#ffd700' : 'rgba(255,255,255,0.8)'
)
const nameShadow  = computed(() =>
  props.isActive ? '0 0 10px rgba(255,215,0,0.5)' : 'none'
)
</script>

<template>
  <!-- :key re-triggers jumpOnce CSS animation on each jumpKey change -->
  <div :key="jumpKey" :style="outerStyle">
    <div :style="frameStyle">
      <!-- Background gradient -->
      <div :style="{
        position: 'absolute', inset: 0,
        background: `linear-gradient(175deg,
          ${character.color ?? '#4c1d95'}ee 0%,
          ${character.color ?? '#4c1d95'}99 40%,
          #0a0a1e 100%)`,
      }" />

      <!-- Scan lines texture -->
      <div style="position:absolute;inset:0;
        background:repeating-linear-gradient(0deg,
          rgba(0,0,0,0.03) 0px,rgba(0,0,0,0.03) 1px,
          transparent 1px,transparent 4px);" />

      <!-- Rim light (active only) -->
      <div
        v-if="isActive"
        :style="{
          position: 'absolute',
          top: 0, bottom: 0,
          left:  position === 'left' ? 'auto' : 0,
          right: position === 'left' ? 0      : 'auto',
          width: '3px',
          background: `linear-gradient(to bottom,
            transparent,
            ${character.accentColor ?? '#7c3aed'}cc,
            transparent)`,
        }"
      />

      <!-- Large watermark symbol -->
      <div :style="{
        position: 'absolute',
        top: '18%', left: '50%',
        transform: 'translateX(-50%)',
        fontSize: `${symbolSize}px`,
        color: `${character.accentColor ?? '#7c3aed'}50`,
        fontFamily: 'serif',
        userSelect: 'none', lineHeight: 1, fontWeight: 700,
      }">{{ character.symbol ?? '？' }}</div>

      <!-- Expression -->
      <div :style="{
        position: 'absolute',
        top: '38%', left: '50%',
        transform: 'translateX(-50%)',
        fontSize: '11px',
        color: EXPRESSION_COLORS[expression],
        fontFamily: 'monospace',
        userSelect: 'none', whiteSpace: 'nowrap',
        textShadow: `0 0 8px ${EXPRESSION_COLORS[expression]}`,
        transition: 'color 0.3s ease',
      }">{{ EXPRESSION_SYMBOLS[expression] }}</div>

      <!-- Bottom name area -->
      <div style="position:absolute;bottom:0;left:0;right:0;
        padding:12px 10px 10px;
        background:linear-gradient(to top,rgba(0,0,0,0.85) 0%,transparent 100%);">
        <div :style="{
          color: nameColor,
          fontSize: '14px',
          fontFamily: '\'Noto Sans SC\', sans-serif',
          fontWeight: 500, textAlign: 'center',
          letterSpacing: '2px', transition: 'color 0.3s ease',
          textShadow: nameShadow,
        }">{{ character.name }}</div>
        <div style="color:rgba(255,255,255,0.45);fontSize:11px;
          fontFamily:'Noto Sans SC',sans-serif;textAlign:center;
          letterSpacing:1px;marginTop:2px;">
          {{ character.title ?? '' }}
        </div>
      </div>

      <!-- Speaking dots (active only) -->
      <div v-if="isActive" style="position:absolute;top:8px;left:50%;
        transform:translateX(-50%);display:flex;gap:3px;alignItems:center;">
        <div
          v-for="i in 3"
          :key="i"
          :style="{
            width: '4px', height: '4px', borderRadius: '50%',
            background: '#ffd700',
            animation: `dotFlash 1.4s ease-in-out ${(i - 1) * 0.2}s infinite`,
          }"
        />
      </div>
    </div>
  </div>
</template>
