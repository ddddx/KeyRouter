<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">Settings</h2>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <h3 class="text-lg font-semibold mb-4">Proxy Configuration</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Host</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.host }}</div>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Port</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.port }}</div>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Proxy URL</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.proxy_url || 'Not configured' }}</div>
        </div>
      </div>
    </div>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <h3 class="text-lg font-semibold mb-4">Health Check</h3>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Check Interval</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.health_check_interval }}s</div>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Max Errors Before Disable</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.health_check_max_errors }}</div>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Check Timeout</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.health_check_timeout }}s</div>
        </div>
      </div>
    </div>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <h3 class="text-lg font-semibold mb-4">Routing</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Max Retry Count</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.max_retry_count }}</div>
        </div>
      </div>
    </div>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <h3 class="text-lg font-semibold mb-4">Log Retention</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Retention Days</label>
          <div class="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm">{{ config.log_retention_days }} days</div>
        </div>
      </div>
      <p class="text-gray-500 text-xs mt-2">Logs older than {{ config.log_retention_days }} days are automatically cleaned up once per day.</p>
    </div>

    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
      <h3 class="text-lg font-semibold mb-4">Configuration Notes</h3>
      <div class="text-gray-400 text-sm space-y-2">
        <p>Configuration is managed via environment variables. Set the following before starting:</p>
        <ul class="list-disc list-inside space-y-1 mt-2">
          <li><code class="text-indigo-400">KEYROUTER_PORT</code> — Server port (default: 8000)</li>
          <li><code class="text-indigo-400">KEYROUTER_HEALTH_CHECK_INTERVAL</code> — Health check interval in seconds (default: 300)</li>
          <li><code class="text-indigo-400">KEYROUTER_HEALTH_CHECK_MAX_ERRORS</code> — Max errors before marking key as error (default: 3)</li>
          <li><code class="text-indigo-400">KEYROUTER_MAX_RETRY_COUNT</code> — Max retry attempts per request (default: 3)</li>
          <li><code class="text-indigo-400">KEYROUTER_PROXY_URL</code> — HTTP proxy for outbound requests (default: none)</li>
          <li><code class="text-indigo-400">KEYROUTER_LOG_RETENTION_DAYS</code> — Log retention in days (default: 30)</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getConfig } from '../api.js'

const config = ref({})
onMounted(async () => {
  config.value = await getConfig()
})
</script>