import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Setup from './views/Setup.vue'
import Login from './views/Login.vue'
import Dashboard from './views/Dashboard.vue'
import Channels from './views/Channels.vue'
import ChannelDetail from './views/ChannelDetail.vue'
import Logs from './views/Logs.vue'
import Settings from './views/Settings.vue'
import ApiKeys from './views/ApiKeys.vue'
import './style.css'

const routes = [
  { path: '/setup', name: 'setup', component: Setup, meta: { noAuth: true } },
  { path: '/login', name: 'login', component: Login, meta: { noAuth: true } },
  { path: '/', name: 'dashboard', component: Dashboard },
  { path: '/channels', name: 'channels', component: Channels },
  { path: '/channels/:id', name: 'channel-detail', component: ChannelDetail },
  { path: '/logs', name: 'logs', component: Logs },
  { path: '/settings', name: 'settings', component: Settings },
  { path: '/api-keys', name: 'api-keys', component: ApiKeys },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Auth guard — redirect based on auth state
router.beforeEach(async (to, from, next) => {
  const token = localStorage.getItem('keyrouter_token')

  if (to.meta.noAuth) {
    // Setup/login pages don't need auth
    next()
    return
  }

  if (token) {
    // Has token, allow access
    next()
    return
  }

  // No token — check if setup is needed first
  try {
    const res = await fetch('/api/auth/status')
    const status = await res.json()
    if (!status.has_admin) {
      next('/setup')
    } else {
      next('/login')
    }
  } catch {
    // Network error — fallback to login
    next('/login')
  }
})

createApp(App).use(router).mount('#app')
