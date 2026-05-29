<template>
  <!-- Login/setup pages have their own layout -->
  <router-view v-if="$route.path === '/login' || $route.path === '/setup'" />

  <!-- Main layout with sidebar -->
  <div v-else class="min-h-screen bg-gray-900 text-gray-100">
    <!-- Sidebar -->
    <aside class="fixed inset-y-0 left-0 w-64 bg-gray-800 border-r border-gray-700 flex flex-col z-30">
      <div class="p-6 border-b border-gray-700">
        <h1 class="text-xl font-bold text-white flex items-center gap-2">
          <span class="text-2xl">🔑</span> KeyRouter
        </h1>
        <p class="text-xs text-gray-400 mt-1">API Key Smart Routing Proxy</p>
      </div>
      <nav class="flex-1 p-4 space-y-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-4 py-3 rounded-lg transition-colors"
          :class="$route.path === item.path || (item.match && $route.path.startsWith(item.match))
            ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
            : 'text-gray-400 hover:bg-gray-700/50 hover:text-gray-200'"
        >
          <span class="text-lg">{{ item.icon }}</span>
          <span class="text-sm font-medium">{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="p-4 border-t border-gray-700">
        <!-- Logout button -->
        <button
          @click="handleLogout"
          class="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-gray-400 hover:bg-red-600/10 hover:text-red-400 transition-colors"
        >
          <span class="text-lg">🚪</span>
          <span class="text-sm font-medium">Logout</span>
        </button>
        <div class="text-xs text-gray-500 mt-2">
          v1.0 · OpenAI Compatible Proxy
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <main class="ml-64 p-8">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { clearToken } from './api.js'

const router = useRouter()

const navItems = [
  { path: '/', icon: '📊', label: 'Dashboard', match: null },
  { path: '/channels', icon: '🌐', label: 'Channels', match: '/channels' },
  { path: '/logs', icon: '📋', label: 'Request Logs', match: '/logs' },
  { path: '/settings', icon: '⚙️', label: 'Settings', match: '/settings' },
]

function handleLogout() {
  clearToken()
  router.push('/login')
}
</script>