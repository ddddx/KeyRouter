<template>
  <div class="min-h-screen bg-gray-900 flex items-center justify-center">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-white flex items-center justify-center gap-2">
          <span class="text-4xl">🔑</span> KeyRouter
        </h1>
        <p class="text-sm text-gray-400 mt-2">{{ t('app.subtitle') }}</p>
      </div>

      <!-- Setup Card (first time, no admin yet) -->
      <div v-if="needsSetup" class="bg-gray-800 rounded-xl p-8 border border-gray-700 shadow-xl">
        <h2 class="text-xl font-semibold text-white mb-2">🚀 {{ t('setup.title') }}</h2>
        <p class="text-sm text-gray-400 mb-6">{{ t('setup.description') }}</p>

        <div v-if="error" class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {{ error }}
        </div>

        <form @submit.prevent="handleSetup">
          <div class="mb-5">
            <label class="text-sm text-gray-400 mb-2 block">{{ t('setup.username') }}</label>
            <input
              v-model="username"
              type="text"
              :placeholder="t('setup.usernamePlaceholder')"
              class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              :disabled="loading"
              autocomplete="username"
            />
          </div>
          <div class="mb-6">
            <label class="text-sm text-gray-400 mb-2 block">{{ t('setup.password') }}</label>
            <input
              v-model="password"
              type="password"
              :placeholder="t('setup.passwordPlaceholder')"
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
            {{ loading ? t('common.creating') : t('setup.createAccount') }}
          </button>
        </form>
      </div>

      <!-- Login Card -->
      <div v-else class="bg-gray-800 rounded-xl p-8 border border-gray-700 shadow-xl">
        <h2 class="text-xl font-semibold text-white mb-6">{{ t('login.title') }}</h2>

        <div v-if="error" class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {{ error }}
        </div>

        <form @submit.prevent="handleLogin">
          <div class="mb-5">
            <label class="text-sm text-gray-400 mb-2 block">{{ t('setup.username') }}</label>
            <input
              v-model="username"
              type="text"
              :placeholder="t('login.usernamePlaceholder')"
              class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              :disabled="loading"
              autocomplete="username"
            />
          </div>
          <div class="mb-6">
            <label class="text-sm text-gray-400 mb-2 block">{{ t('setup.password') }}</label>
            <input
              v-model="password"
              type="password"
              :placeholder="t('login.passwordPlaceholder')"
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
            {{ loading ? t('login.signingIn') : t('login.signIn') }}
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
import { t } from '../i18n.js'

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
      error.value = t('setup.failed') + ': ' + (e.message || 'Unknown error')
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
      error.value = t('login.invalidCredentials')
    } else {
      error.value = t('login.failed', { message: e.message || 'Unknown error' })
    }
  }
  loading.value = false
}
</script>
