<template>
  <div class="main-menu-page">
    <!-- Fixed scene background -->
    <div class="scene-bg" :style="{ backgroundImage: `url(${homeBg})` }"></div>
    <div class="scene-overlay"></div>

    <!-- Main Menu - shown when no child route is active -->
    <Transition name="menu-fade" mode="out-in">
      <div v-if="!hasChildRoute" key="menu" class="menu-container">
        <!-- Title area with v-motion -->
        <div 
          class="title-area"
          v-motion
          :initial="{ opacity: 0, y: -30 }"
          :enter="{ opacity: 1, y: 0 }"
          :transition="{ delay: 200, duration: 800 }"
        >
          <h1 class="title-text-hover title-text">知遇</h1>
          <div class="font-ui subtitle-text">✦ &nbsp; ZHĪ YÙ · 愿求知者皆得其道 &nbsp; ✦</div>
          <div class="gold-divider"></div>
        </div>

        <!-- Menu nav with v-motion stagger -->
        <nav 
          class="menu-nav"
          v-motion
          :initial="{ opacity: 0 }"
          :enter="{ opacity: 1 }"
          :transition="{ delay: 500, duration: 600 }"
        >
          <div
            v-for="(item, i) in MENU_ITEMS"
            :key="item.label"
            v-motion
            :initial="{ opacity: 0, x: -30 }"
            :enter="{ opacity: 1, x: 0 }"
            :transition="{ delay: 500 + i * 0.1, duration: 500 }"
          >
            <div class="galgame-menu-item" @click="item.action">{{ item.label }}</div>
          </div>
        </nav>
      </div>
    </Transition>

    <!-- Child routes -->
    <router-view v-slot="{ Component }">
      <Transition name="page-fade" mode="out-in">
        <component :is="Component" />
      </Transition>
    </router-view>

    <p v-if="errorMessage" class="error-toast font-ui">{{ errorMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import homeBg from '@/assets/home-bg.png'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const errorMessage = ref('')

// Check if a child route is active (route has more than just /home)
const hasChildRoute = computed(() => {
  return route.matched.length > 1
})

const logout = () => { 
  authStore.logout(); 
  router.push('/login') 
}

const MENU_ITEMS = [
  { label: '开 始 学 习', action: () => router.push('/home/worlds') },
  { label: '学 习 报 告', action: () => router.push('/home/report') },
  { label: '角 色 管 理', action: () => router.push('/character') },
  { label: '档 案 管 理', action: () => router.push('/archive') },
  { label: '系 统 设 置', action: () => router.push('/settings') },
  { label: '退 出 登 录', action: logout },
]
</script>

<style scoped>
.main-menu-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #0a0a1e;
}

.scene-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0.60;
  transition: opacity 1.2s ease;
}

.scene-overlay {
  position: absolute;
  inset: 0;
  background: 
    radial-gradient(ellipse at 50% 0%, rgba(10,10,30,0.15) 0%, transparent 60%),
    radial-gradient(ellipse at 30% 55%, rgba(255,215,0,0.05) 0%, transparent 55%),
    radial-gradient(ellipse at 70% 35%, rgba(96,165,250,0.04) 0%, transparent 55%),
    linear-gradient(to bottom, rgba(10,10,30,0.25) 0%, rgba(0,0,0,0.45) 100%);
}

/* Menu Container */
.menu-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.title-area {
  text-align: center;
  margin-bottom: 64px;
}

.gold-divider {
  width: 180px;
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(255,215,0,0.4), transparent);
  margin: 14px auto 0;
}

.menu-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.title-text {
  font-family: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
  font-size: 38px;
  letter-spacing: 12px;
  color: #ffd700;
  margin-bottom: 12px;
  transition: text-shadow 0.6s ease;
  text-align: center;
}

.title-text-hover:hover {
  text-shadow:
    0 0 8px rgba(255,215,0,0.6),
    0 0 16px rgba(255,215,0,0.35);
}

.subtitle-text {
  font-family: "Noto Serif SC", "Source Han Serif SC", "SimSun", serif;
  color: rgba(255,255,255,0.70);
  font-size: 14px;
  letter-spacing: 4px;
}

/* Error Toast */
.error-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(223, 74, 74, 0.9);
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  z-index: 9999;
  letter-spacing: 1px;
}
</style>
