import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { MotionPlugin } from '@vueuse/motion'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

// Import Figma styles - core galgame styles
import './styles/galgame.css'
// Import base CSS for compatibility
import './assets/main.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(MotionPlugin)

// Restore auth state from localStorage on app startup
const authStore = useAuthStore(pinia)
authStore.initAuth()

app.mount('#app')
