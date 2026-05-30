<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">{{ t('settings.title') }}</h2>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <h3 class="text-lg font-semibold mb-4">{{ t('settings.proxyConfig') }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.host') }}</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.host }}</div>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.port') }}</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.port }}</div>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.proxyUrl') }}</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm break-all">{{ config.proxy_url || t('common.notConfigured') }}</div>
        </div>
      </div>
    </div>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <h3 class="text-lg font-semibold mb-4">{{ t('settings.healthCheck') }}</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.checkInterval') }}</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.health_check_interval }}s</div>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.maxErrors') }}</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.health_check_max_errors }}</div>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.checkTimeout') }}</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.health_check_timeout }}s</div>
        </div>
      </div>
    </div>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <h3 class="text-lg font-semibold">{{ t('settings.routing') }}</h3>
        <button
          @click="saveSettings"
          :disabled="saving"
          class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ saving ? t('common.saving') : t('common.save') }}
        </button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.maxRetry') }}</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.max_retry_count }}</div>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.keyCooldown') }}</label>
          <input
            v-model.number="form.key_cooldown_minutes"
            type="number"
            min="1"
            step="1"
            class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:border-indigo-500 focus:outline-none"
          >
          <p class="text-gray-500 text-xs mt-2">{{ t('settings.cooldownHint', { count: cooldownLabel }) }}</p>
        </div>
      </div>
    </div>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <h3 class="text-lg font-semibold mb-4">{{ t('settings.logRetention') }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.retentionDays') }}</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ t('settings.days', { count: config.log_retention_days }) }}</div>
        </div>
      </div>
      <p class="text-gray-500 text-xs mt-2">{{ t('settings.retentionHint', { count: config.log_retention_days }) }}</p>
    </div>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
      <h3 class="text-lg font-semibold mb-4">{{ t('settings.configNotes') }}</h3>
      <div class="text-gray-400 text-sm space-y-2">
        <p>{{ t('settings.configManaged') }}</p>
        <ul class="list-disc list-inside space-y-1 mt-2">
          <li><code class="text-indigo-400 break-all">KEYROUTER_PORT</code> - {{ t('settings.envPort') }}</li>
          <li><code class="text-indigo-400 break-all">KEYROUTER_HEALTH_CHECK_INTERVAL</code> - {{ t('settings.envHealthInterval') }}</li>
          <li><code class="text-indigo-400 break-all">KEYROUTER_HEALTH_CHECK_MAX_ERRORS</code> - {{ t('settings.envHealthErrors') }}</li>
          <li><code class="text-indigo-400 break-all">KEYROUTER_MAX_RETRY_COUNT</code> - {{ t('settings.envRetry') }}</li>
          <li><code class="text-indigo-400 break-all">KEYROUTER_KEY_COOLDOWN_SECONDS</code> - {{ t('settings.envCooldown') }}</li>
          <li><code class="text-indigo-400 break-all">KEYROUTER_PROXY_URL</code> - {{ t('settings.envProxy') }}</li>
          <li><code class="text-indigo-400 break-all">KEYROUTER_LOG_RETENTION_DAYS</code> - {{ t('settings.envRetention') }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { getConfig, updateConfig } from '../api.js'
import { t } from '../i18n.js'

const config = ref({})
const form = ref({ key_cooldown_minutes: 15 })
const saving = ref(false)
const cooldownLabel = computed(() => {
  const seconds = Number(form.value.key_cooldown_minutes || 15) * 60
  if (seconds % 60 === 0) {
    return t('settings.minutes', { count: seconds / 60 })
  }
  return `${seconds}s`
})

function fillForm(nextConfig) {
  const seconds = Number(nextConfig.key_cooldown_seconds || 900)
  form.value.key_cooldown_minutes = Math.max(1, Math.round(seconds / 60))
}

async function loadConfig() {
  config.value = await getConfig()
  fillForm(config.value)
}

async function saveSettings() {
  saving.value = true
  try {
    const minutes = Math.max(1, Number(form.value.key_cooldown_minutes || 15))
    await updateConfig({ key_cooldown_seconds: Math.round(minutes * 60) })
    await loadConfig()
  } catch (e) {
    alert(t('common.operationFailed', { message: e.response?.data?.detail || e.message }))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await loadConfig()
})
</script>
