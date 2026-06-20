import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/app/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/app/views/Login.vue')
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/app/views/Home.vue'),
    children: [
      {
        path: 'worlds',
        name: 'Worlds',
        component: () => import('@/worlds/views/Worlds.vue')
      },
      {
        path: 'worlds/:worldId',
        name: 'WorldDetail',
        component: () => import('@/worlds/views/WorldDetail.vue')
      },
      {
        path: 'worlds/:worldId/courses/:courseId',
        name: 'CoursePage',
        component: () => import('@/courses/views/CoursePage.vue')
      }
    ]
  },
  {
    path: '/learning/:courseId',
    name: 'Learning',
    component: () => import('@/courses/views/Learning.vue')
  },
  {
    path: '/bookshelf',
    name: 'Bookshelf',
    component: () => import('@/courses/views/Bookshelf.vue')
  },
  {
    path: '/archive',
    name: 'Archive',
    component: () => import('@/archives/views/Archive.vue')
  },
  {
    path: '/character',
    name: 'Character',
    component: () => import('@/characters/views/Character.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/settings/views/Settings.vue')
  }
]

const router = createRouter({
  // hash 路由更适合 Electron 打包
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

