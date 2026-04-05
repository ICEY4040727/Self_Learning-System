import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/pages/LoginPage.vue'),
    },
    {
      path: '/home',
      component: () => import('@/pages/MainMenuPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      // courseId comes from query: /learning?courseId=1&worldId=2&checkpointId=3
      path: '/learning',
      component: () => import('@/pages/LearningPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/archive',
      component: () => import('@/pages/ArchivesPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings',
      component: () => import('@/pages/SettingsPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      // 课程设计页：上传教材 + AI 课时切分
      path: '/course/:courseId/design',
      component: () => import('@/pages/CourseDesignPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return '/'
  }
})