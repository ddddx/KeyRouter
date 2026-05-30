<template>
  <!-- Login/setup pages have their own layout -->
  <router-view v-if="$route.path === '/login' || $route.path === '/setup'" />

  <!-- Main layout with sidebar -->
  <div v-else class="min-h-screen bg-gray-900 text-gray-100">
    <!-- Sidebar -->
    <aside class="lg:fixed lg:inset-y-0 lg:left-0 lg:w-64 bg-gray-800 border-b lg:border-b-0 lg:border-r border-gray-700 flex flex-col z-30">
      <div class="p-4 lg:p-6 border-b border-gray-700">
        <h1 class="text-xl font-bold text-white flex items-center gap-2">
          <span class="text-2xl">🔑</span> KeyRouter
        </h1>
        <p class="hidden sm:block text-xs text-gray-400 mt-1">{{ t('app.subtitle') }}</p>
      </div>
      <nav class="flex-1 p-2 lg:p-4 flex lg:block gap-2 lg:space-y-1 overflow-x-auto">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex shrink-0 items-center gap-2 lg:gap-3 px-3 lg:px-4 py-2 lg:py-3 rounded-lg transition-colors"
          :class="$route.path === item.path || (item.match && $route.path.startsWith(item.match))
            ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
            : 'text-gray-400 hover:bg-gray-700/50 hover:text-gray-200'"
        >
          <span class="text-lg">{{ item.icon }}</span>
          <span class="text-sm font-medium whitespace-nowrap">{{ t(item.labelKey) }}</span>
        </router-link>
      </nav>
      <div class="p-2 lg:p-4 border-t border-gray-700 space-y-2">
        <label class="block text-xs text-gray-500 px-1">{{ t('app.language') }}</label>
        <select
          :value="language"
          @change="setLanguage($event.target.value)"
          :aria-label="t('app.language')"
          class="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm text-gray-200 focus:outline-none focus:border-indigo-500"
        >
          <option v-for="option in languageOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <!-- Logout button -->
        <button
          @click="handleLogout"
          class="w-full flex items-center gap-2 lg:gap-3 px-3 lg:px-4 py-2 lg:py-3 rounded-lg text-gray-400 hover:bg-red-600/10 hover:text-red-400 transition-colors"
        >
          <span class="text-lg">🚪</span>
          <span class="text-sm font-medium">{{ t('nav.logout') }}</span>
        </button>
        <div class="hidden lg:block text-xs text-gray-500 mt-2">
          {{ t('app.version') }}
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <main class="p-4 lg:ml-64 lg:p-8 min-w-0">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { clearToken } from './api.js'
import { language, languageOptions, setLanguage, t } from './i18n.js'

const router = useRouter()

const navItems = [
  { path: '/', icon: '📊', labelKey: 'nav.dashboard', match: null },
  { path: '/channels', icon: '🌐', labelKey: 'nav.channels', match: '/channels' },
  { path: '/api-keys', icon: '🔑', labelKey: 'nav.apiKeys', match: '/api-keys' },
  { path: '/logs', icon: '📋', labelKey: 'nav.logs', match: '/logs' },
  { path: '/settings', icon: '⚙️', labelKey: 'nav.settings', match: '/settings' },
]

function handleLogout() {
  clearToken()
  router.push('/login')
}
</script>
