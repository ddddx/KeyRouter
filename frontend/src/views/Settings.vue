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
      <h3 class="text-lg font-semibold mb-4">{{ t('settings.routing') }}</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('settings.maxRetry') }}</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.max_retry_count }}</div>
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
          <li><code class="text-indigo-400 break-all">KEYROUTER_PROXY_URL</code> - {{ t('settings.envProxy') }}</li>
          <li><code class="text-indigo-400 break-all">KEYROUTER_LOG_RETENTION_DAYS</code> - {{ t('settings.envRetention') }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getConfig } from '../api.js'
import { t } from '../i18n.js'

const config = ref({})
onMounted(async () => {
  config.value = await getConfig()
})
</script>
