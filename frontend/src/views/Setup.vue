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

      <!-- Setup Card -->
      <div class="bg-gray-800 rounded-xl p-8 border border-gray-700 shadow-xl">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-lg bg-indigo-600/20 flex items-center justify-center text-xl">🛡️</div>
          <h2 class="text-xl font-semibold text-white">Initial Setup</h2>
        </div>
        <p class="text-sm text-gray-400 mb-6">
          Welcome! Create your admin account to start managing KeyRouter.
          This step is only available on first use.
        </p>

        <div v-if="error" class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {{ error }}
        </div>

        <form @submit.prevent="handleSetup">
          <div class="mb-5">
            <label class="text-sm text-gray-400 mb-2 block">Admin Username</label>
            <input
              v-model="username"
              type="text"
              placeholder="Choose a username (min 3 characters)"
              class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              :disabled="loading"
              autocomplete="username"
            />
          </div>
          <div class="mb-5">
            <label class="text-sm text-gray-400 mb-2 block">Password</label>
            <input
              v-model="password"
              type="password"
              placeholder="Choose a password (min 6 characters)"
              class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              :disabled="loading"
              autocomplete="new-password"
            />
          </div>
          <div class="mb-6">
            <label class="text-sm text-gray-400 mb-2 block">Confirm Password</label>
            <input
              v-model="confirmPassword"
              type="password"
              placeholder="Confirm your password"
              class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              :disabled="loading"
              autocomplete="new-password"
            />
            <div v-if="confirmPassword && password !== confirmPassword" class="text-red-400 text-xs mt-1">
              Passwords do not match
            </div>
          </div>
          <button
            type="submit"
            class="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loading || !username || !password || !confirmPassword || username.length < 3 || password.length < 6 || password !== confirmPassword"
          >
            {{ loading ? 'Creating...' : 'Create Admin Account' }}
          </button>
        </form>
      </div>

      <!-- Info -->
      <div class="mt-4 text-center text-xs text-gray-500">
        After setup, you will be automatically logged in.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { setupAdmin, getAuthStatus, setToken, clearToken } from '../api.js'

const router = useRouter()
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')

onMounted(async () => {
  // Check if setup is still needed
  try {
    const status = await getAuthStatus()
    if (status.has_admin) {
      // Already has admin, redirect to login
      router.push('/login')
    }
  } catch (e) {
    console.error('Failed to check auth status', e)
  }
})

async function handleSetup() {
  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }

  loading.value = true
  error.value = ''
  try {
    const res = await setupAdmin(username.value, password.value)
    // Auto-login: save token and go to dashboard
    setToken(res.access_token)
    router.push('/')
  } catch (e) {
    if (e.response) {
      if (e.response.status === 403) {
        // Admin already exists, redirect to login
        router.push('/login')
        return
      }
      if (e.response.data && e.response.data.detail) {
        error.value = e.response.data.detail
      } else {
        error.value = 'Setup failed'
      }
    } else {
      error.value = 'Network error: ' + (e.message || 'Unknown error')
    }
  }
  loading.value = false
}
</script>