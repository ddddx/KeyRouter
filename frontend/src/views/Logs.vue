<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">{{ t('logs.title') }}</h2>

    <!-- Filters -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('logs.channel') }}</label>
          <select v-model="filters.channel_id" @change="refresh" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
            <option value="">{{ t('logs.allChannels') }}</option>
            <option v-for="ch in channels" :value="ch.id">{{ ch.name }}</option>
          </select>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('logs.model') }}</label>
          <select v-model="filters.model" @change="refresh" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
            <option value="">{{ t('logs.allModels') }}</option>
            <option v-for="m in modelList" :value="m">{{ m }}</option>
          </select>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('logs.status') }}</label>
          <select v-model="filters.status_filter" @change="refresh" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
            <option value="">{{ t('logs.all') }}</option>
            <option value="success">{{ t('common.success') }}</option>
            <option value="failed">{{ t('common.failed') }}</option>
            <option value="200">{{ t('logs.ok') }}</option>
            <option value="429">{{ t('logs.rateLimited') }}</option>
            <option value="401">{{ t('logs.authFailed') }}</option>
            <option value="500">{{ t('logs.serverError') }}</option>
          </select>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('logs.startTime') }}</label>
          <input v-model="filters.start_time" @change="refresh" type="datetime-local" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('logs.endTime') }}</label>
          <input v-model="filters.end_time" @change="refresh" type="datetime-local" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
        </div>
        <div class="flex flex-wrap items-end gap-3">
          <button @click="refresh" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors">{{ t('common.refresh') }}</button>
          <button @click="exportCSV" class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium transition-colors">⬇ {{ t('logs.exportCsv') }}</button>
        </div>
      </div>
    </div>

    <!-- Logs table -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
      <div v-if="loading" class="text-gray-400">{{ t('common.loading') }}</div>
      <div v-else-if="logs.entries.length === 0" class="text-gray-400 text-center py-8">
        {{ t('logs.empty') }}
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-gray-400 border-b border-gray-700">
              <th class="py-2 px-3 text-left">{{ t('logs.time') }}</th>
              <th class="py-2 px-3 text-left">{{ t('logs.channel') }}</th>
              <th class="py-2 px-3 text-left">Key</th>
              <th class="py-2 px-3 text-left">{{ t('logs.model') }}</th>
              <th class="py-2 px-3 text-left">{{ t('logs.tokens') }}</th>
              <th class="py-2 px-3 text-left">RT (ms)</th>
              <th class="py-2 px-3 text-left">{{ t('logs.status') }}</th>
              <th class="py-2 px-3 text-left">{{ t('logs.success') }}</th>
              <th class="py-2 px-3 text-left">{{ t('logs.stream') }}</th>
              <th class="py-2 px-3 text-left">{{ t('logs.sourceIp') }}</th>
              <th class="py-2 px-3 text-left">{{ t('logs.error') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in logs.entries" class="border-b border-gray-700/50 hover:bg-gray-700/30">
              <td class="py-2 px-3 text-gray-300 text-xs">{{ formatTime(l.timestamp) }}</td>
              <td class="py-2 px-3 text-gray-300">{{ l.channel || '-' }}</td>
              <td class="py-2 px-3 text-gray-300 font-mono text-xs">{{ l.key || '-' }}</td>
              <td class="py-2 px-3 text-gray-300">{{ l.model || '-' }}</td>
              <td class="py-2 px-3 text-yellow-400">{{ l.total_tokens }}</td>
              <td class="py-2 px-3 text-gray-300">{{ l.response_time_ms }}ms</td>
              <td class="py-2 px-3">
                <span :class="l.status_code < 400 ? 'text-green-400' : 'text-red-400'" class="font-medium">{{ l.status_code }}</span>
              </td>
              <td class="py-2 px-3">
                <span :class="l.is_success ? 'text-green-400' : 'text-red-400'">{{ l.is_success ? '✓' : '✗' }}</span>
              </td>
              <td class="py-2 px-3 text-gray-300">{{ l.is_streaming ? '✓' : '-' }}</td>
              <td class="py-2 px-3 text-gray-400 text-xs">{{ l.source_ip || '-' }}</td>
              <td class="py-2 px-3 text-red-300 text-xs truncate max-w-xs">{{ l.error_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mt-4 text-sm text-gray-400">
        <span>{{ t('logs.showing', { shown: logs.entries.length, total: logs.total }) }}</span>
        <div class="flex gap-2">
          <button v-if="filters.offset > 0" @click="prevPage" class="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">← {{ t('logs.prev') }}</button>
          <button v-if="logs.entries.length >= filters.limit" @click="nextPage" class="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">{{ t('logs.next') }} →</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getLogs, exportLogsCSV, getChannels } from '../api.js'
import { t } from '../i18n.js'

const channels = ref([])
const modelList = ref([])
const logs = ref({ total: 0, entries: [] })
const loading = ref(true)
const filters = ref({
  channel_id: '',
  model: '',
  status_filter: '',
  start_time: '',
  end_time: '',
  limit: 100,
  offset: 0,
})

function formatTime(ts) {
  if (!ts) return '-'
  return ts.replace('T', ' ').substring(0, 19)
}

function buildParams() {
  const p = {}
  if (filters.value.channel_id) p.channel_id = filters.value.channel_id
  if (filters.value.model) p.model = filters.value.model
  if (filters.value.start_time) p.start_time = filters.value.start_time
  if (filters.value.end_time) p.end_time = filters.value.end_time
  // Status filter
  const sf = filters.value.status_filter
  if (sf === 'success') p.is_success = true
  else if (sf === 'failed') p.is_success = false
  else if (sf) p.status_code = parseInt(sf)
  p.limit = filters.value.limit
  p.offset = filters.value.offset
  return p
}

async function refresh() {
  loading.value = true
  logs.value = await getLogs(buildParams())
  // Collect models from current logs for filter dropdown
  const models = new Set()
  for (const e of logs.value.entries) {
    if (e.model) models.add(e.model)
  }
  modelList.value = [...models].sort()
  loading.value = false
}

function nextPage() {
  filters.value.offset += filters.value.limit
  refresh()
}

function prevPage() {
  filters.value.offset = Math.max(0, filters.value.offset - filters.value.limit)
  refresh()
}

async function exportCSV() {
  try {
    const blob = await exportLogsCSV(buildParams())
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `keyrouter_logs_${new Date().toISOString().slice(0,10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert(t('logs.exportFailed', { message: e.message }))
  }
}

onMounted(async () => {
  channels.value = await getChannels()
  await refresh()
})
</script>
