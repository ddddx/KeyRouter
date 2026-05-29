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

      <!-- Login Card -->
      <div class="bg-gray-800 rounded-xl p-8 border border-gray-700 shadow-xl">
        <h2 class="text-xl font-semibold text-white mb-6">Admin Login</h2>

        <div v-if="error" class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {{ error }}
        </div>

        <div v-if="mustChangePassword" class="mb-4 px-4 py-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm">
          ⚠️ Default password detected. Please change your password after login.
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

        <div class="mt-4 text-center text-xs text-gray-500">
          Default: admin / admin123
        </div>
      </div>

      <!-- Change Password Dialog -->
      <div v-if="showChangePassword" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div class="bg-gray-800 rounded-xl p-8 border border-gray-700 shadow-xl w-full max-w-md">
          <h2 class="text-xl font-semibold text-white mb-2">Change Password</h2>
          <p class="text-sm text-yellow-400 mb-6">You must change your default password before continuing.</p>

          <div v-if="changeError" class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {{ changeError }}
          </div>

          <form @submit.prevent="handleChangePassword">
            <div class="mb-4">
              <label class="text-sm text-gray-400 mb-2 block">Old Password</label>
              <input
                v-model="oldPassword"
                type="password"
                placeholder="Current password"
                class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                :disabled="changeLoading"
              />
            </div>
            <div class="mb-4">
              <label class="text-sm text-gray-400 mb-2 block">New Password</label>
              <input
                v-model="newPassword"
                type="password"
                placeholder="New password (min 6 characters)"
                class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                :disabled="changeLoading"
              />
            </div>
            <div class="mb-6">
              <label class="text-sm text-gray-400 mb-2 block">Confirm New Password</label>
              <input
                v-model="confirmPassword"
                type="password"
                placeholder="Confirm new password"
                class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                :disabled="changeLoading"
              />
            </div>
            <button
              type="submit"
              class="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              :disabled="changeLoading || !oldPassword || !newPassword || !confirmPassword || newPassword !== confirmPassword"
            >
              {{ changeLoading ? 'Changing...' : 'Change Password' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { login, changePassword, getToken, setToken, clearToken } from '../api.js'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const mustChangePassword = ref(false)

// Change password dialog
const showChangePassword = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const changeLoading = ref(false)
const changeError = ref('')

onMounted(() => {
  // If already logged in, redirect to dashboard
  if (getToken()) {
    router.push('/')
  }
})

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const res = await login(username.value, password.value)
    setToken(res.access_token)
    mustChangePassword.value = res.must_change_password

    if (res.must_change_password) {
      showChangePassword.value = true
      oldPassword.value = password.value
    } else {
      router.push('/')
    }
  } catch (e) {
    if (e.response && e.response.status === 401) {
      error.value = 'Invalid username or password'
    } else {
      error.value = 'Login failed: ' + (e.message || 'Unknown error')
    }
  }
  loading.value = false
}

async function handleChangePassword() {
  if (newPassword.value !== confirmPassword.value) {
    changeError.value = 'Passwords do not match'
    return
  }
  if (newPassword.value.length < 6) {
    changeError.value = 'New password must be at least 6 characters'
    return
  }

  changeLoading.value = true
  changeError.value = ''
  try {
    const res = await changePassword(oldPassword.value, newPassword.value)
    // Update token after password change
    setToken(res.access_token)
    showChangePassword.value = false
    router.push('/')
  } catch (e) {
    if (e.response && e.response.data && e.response.data.detail) {
      changeError.value = e.response.data.detail
    } else {
      changeError.value = 'Failed to change password'
    }
  }
  changeLoading.value = false
}
</script>