import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './views/Dashboard.vue'
import Channels from './views/Channels.vue'
import ChannelDetail from './views/ChannelDetail.vue'
import Logs from './views/Logs.vue'
import Settings from './views/Settings.vue'
import './style.css'

const routes = [
  { path: '/', name: 'dashboard', component: Dashboard },
  { path: '/channels', name: 'channels', component: Channels },
  { path: '/channels/:id', name: 'channel-detail', component: ChannelDetail },
  { path: '/logs', name: 'logs', component: Logs },
  { path: '/settings', name: 'settings', component: Settings },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

createApp(App).use(router).mount('#app')