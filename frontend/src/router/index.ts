import { createRouter, createWebHashHistory } from 'vue-router'
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
    component: () => import('@/views/Home.vue'),
    children: [
      {
        path: 'worlds',
        name: 'Worlds',
        component: () => import('@/views/Worlds.vue')
      },
      {
        path: 'worlds/:worldId',
        name: 'WorldDetail',
        component: () => import('@/views/WorldDetail.vue'),
        children: [
          {
            path: 'courses/:courseId',
            name: 'CoursePage',
            component: () => import('@/views/CoursePage.vue')
          }
        ]
      }
    ]
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
  // Hash 路由更适合 Electron 打包
  history: createWebHashHistory(),
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
