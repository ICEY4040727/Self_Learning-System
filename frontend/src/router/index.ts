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
            name: 'CourseLearning',
            component: () => import('@/views/Learning.vue')
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

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  if (to.name !== 'Login' && !authStore.isAuthenticated) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
