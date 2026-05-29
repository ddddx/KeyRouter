<template>
  <div class="min-h-screen bg-gray-900 flex items-center justify-center">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-white flex items-center justify-center gap-2">
          <span class="text-4xl">🔑</span> KeyRouter
        </h1>
        <p class="text-sm text-gray-400 mt-2">API Key Smart Routing Proxy</p>
      </div>

      <!-- Setup Card (first time, no admin yet) -->
      <div v-if="needsSetup" class="bg-gray-800 rounded-xl p-8 border border-gray-700 shadow-xl">
        <h2 class="text-xl font-semibold text-white mb-2">🚀 Initial Setup</h2>
        <p class="text-sm text-gray-400 mb-6">Create your admin account to get started. This is only available on first launch.</p>

        <div v-if="error" class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {{ error }}
        </div>

        <form @submit.prevent="handleSetup">
          <div class="mb-5">
            <label class="text-sm text-gray-400 mb-2 block">Username</label>
            <input
              v-model="username"
              type="text"
              placeholder="Choose a username (min 3 chars)"
              class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              :disabled="loading"
              autocomplete="username"
            />
          </div>
          <div class="mb-6">
            <label class="text-sm text-gray-400 mb-2 block">Password</label>
            <input
              v-model="password"
              type="password"
              placeholder="Choose a password (min 6 chars)"
              class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              :disabled="loading"
              autocomplete="new-password"
            />
          </div>
          <button
            type="submit"
            class="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loading || !username || !password"
          >
            {{ loading ? 'Creating...' : 'Create Admin Account' }}
          </button>
        </form>
      </div>

      <!-- Login Card -->
      <div v-else class="bg-gray-800 rounded-xl p-8 border border-gray-700 shadow-xl">
        <h2 class="text-xl font-semibold text-white mb-6">Admin Login</h2>

        <div v-if="error" class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {{ error }}
        </div>

        <form @submit.prevent="handleLogin">
          <div class="mb-5">
            <label class="text-sm text-gray-400 mb-2 block">Username</label>
            <input
              v-model="username"
              type="text"
              placeholder="Enter username"
              class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              :disabled="loading"
              autocomplete="username"
            />
          </div>
          <div class="mb-6">
            <label class="text-sm text-gray-400 mb-2 block">Password</label>
            <input
              v-model="password"
              type="password"
              placeholder="Enter password"
              class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              :disabled="loading"
              autocomplete="current-password"
            />
          </div>
          <button
            type="submit"
            class="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loading || !username || !password"
          >
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { login, setupAdmin, getAuthStatus, getToken, setToken } from '../api.js'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const needsSetup = ref(false)

onMounted(async () => {
  // If already logged in, redirect to dashboard
  if (getToken()) {
    router.push('/')
    return
  }

  // Check auth status to determine if we need setup or login
  try {
    const status = await getAuthStatus()
    if (!status.has_admin) {
      needsSetup.value = true
    }
  } catch (e) {
    // If status check fails, assume login
    needsSetup.value = false
  }
})

async function handleSetup() {
  loading.value = true
  error.value = ''
  try {
    const res = await setupAdmin(username.value, password.value)
    setToken(res.access_token)
    router.push('/')
  } catch (e) {
    if (e.response && e.response.data && e.response.data.detail) {
      error.value = e.response.data.detail
    } else {
      error.value = 'Setup failed: ' + (e.message || 'Unknown error')
    }
  }
  loading.value = false
}

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const res = await login(username.value, password.value)
    setToken(res.access_token)
    router.push('/')
  } catch (e) {
    if (e.response && e.response.status === 401) {
      error.value = 'Invalid username or password'
    } else {
      error.value = 'Login failed: ' + (e.message || 'Unknown error')
    }
  }
  loading.value = false
}
</script>