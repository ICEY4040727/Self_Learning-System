<script setup lang="ts">
import { computed } from 'vue'

interface Particle {
  id: number; left: string; top: string
  size: number; duration: number; delay: number; opacity: number
}

const props = withDefaults(defineProps<{
  count?: number
  goldRatio?: number
}>(), { count: 28, goldRatio: 0.6 })

const particles = computed<Particle[]>(() =>
  Array.from({ length: props.count }, (_, i) => ({
    id:       i,
    left:     `${Math.random() * 100}%`,
    top:      `${Math.random() * 100}%`,
    size:     Math.random() * 2.5 + 1,
    duration: Math.random() * 10 + 6,
    delay:    Math.random() * 8,
    opacity:  Math.random() * 0.4 + 0.15,
  }))
)

function isGold(id: number) {
  return id / props.count < props.goldRatio
}
function color(p: Particle) {
  return isGold(p.id)
    ? `rgba(255, 215, 0, ${p.opacity})`
    : `rgba(147, 197, 253, ${p.opacity * 0.7})`
}
function glow(p: Particle) {
  const c = color(p)
  return isGold(p.id)
    ? `0 0 ${p.size * 3}px ${c}`
    : `0 0 ${p.size * 2}px ${c}`
}
</script>

<template>
  <div class="absolute inset-0 pointer-events-none overflow-hidden">
    <div
      v-for="p in particles"
      :key="p.id"
      class="absolute rounded-full"
      :style="{
        left: p.left, top: p.top,
        width: `${p.size}px`, height: `${p.size}px`,
        background: color(p),
        boxShadow: glow(p),
        animation: `floatParticle ${p.duration}s ease-in-out ${p.delay}s infinite`,
      }"
    />
    <!-- Ambient light blobs -->
    <div class="absolute" style="width:40%;height:40%;left:10%;top:20%;
      background:radial-gradient(circle,rgba(255,215,0,0.025) 0%,transparent 70%);
      animation:ambientPulse 12s ease-in-out infinite;" />
    <div class="absolute" style="width:35%;height:35%;right:5%;bottom:25%;
      background:radial-gradient(circle,rgba(99,102,241,0.03) 0%,transparent 70%);
      animation:ambientPulse 15s ease-in-out 3s infinite;" />
  </div>
</template>
