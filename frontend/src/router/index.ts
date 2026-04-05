import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/learning/:courseId',
    name: 'Learning',
    component: () => import('@/views/Learning.vue')
  },
  {
    path: '/archive',
    name: 'Archive',
    component: () => import('@/views/Archive.vue')
  },
  {
    path: '/character',
    name: 'Character',
    component: () => import('@/views/Character.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

let authInitialized = false

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  if (!authInitialized) {
    await authStore.initAuth()
    authInitialized = true
  }

  if (to.name === 'Login' && authStore.isAuthenticated) return { name: 'Home' }
  if (to.name !== 'Login' && !authStore.isAuthenticated) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
