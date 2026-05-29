<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">Request Logs</h2>

    <!-- Filters -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <div class="grid grid-cols-4 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Channel</label>
          <select v-model="filters.channel_id" @change="refresh" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
            <option value="">All Channels</option>
            <option v-for="ch in channels" :value="ch.id">{{ ch.name }}</option>
          </select>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Status Code</label>
          <select v-model="filters.status_code" @change="refresh" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
            <option value="">All</option>
            <option value="200">200 (Success)</option>
            <option value="429">429 (Rate Limited)</option>
            <option value="401">401 (Auth Failed)</option>
            <option value="500">500 (Server Error)</option>
          </select>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Limit</label>
          <select v-model.number="filters.limit" @change="refresh" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="200">200</option>
          </select>
        </div>
        <div class="flex items-end">
          <button @click="refresh" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors">Refresh</button>
        </div>
      </div>
    </div>

    <!-- Logs table -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
      <div v-if="loading" class="text-gray-400">Loading...</div>
      <div v-else-if="logs.entries.length === 0" class="text-gray-400 text-center py-8">
        No request logs found.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-gray-400 border-b border-gray-700">
              <th class="py-2 px-3 text-left">Time</th>
              <th class="py-2 px-3 text-left">Channel</th>
              <th class="py-2 px-3 text-left">Key</th>
              <th class="py-2 px-3 text-left">Model</th>
              <th class="py-2 px-3 text-left">Tokens</th>
              <th class="py-2 px-3 text-left">RT</th>
              <th class="py-2 px-3 text-left">Status</th>
              <th class="py-2 px-3 text-left">Stream</th>
              <th class="py-2 px-3 text-left">Error</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in logs.entries" class="border-b border-gray-700/50 hover:bg-gray-700/30">
              <td class="py-2 px-3 text-gray-300 text-xs">{{ formatTime(l.timestamp) }}</td>
              <td class="py-2 px-3 text-gray-300">{{ l.channel || '-' }}</td>
              <td class="py-2 px-3 text-gray-300 font-mono text-xs">{{ l.key || '-' }}</td>
              <td class="py-2 px-3 text-gray-300">{{ l.model || '-' }}</td>
              <td class="py-2 px-3 text-gray-300">{{ (l.prompt_tokens || 0) + (l.completion_tokens || 0) }}</td>
              <td class="py-2 px-3 text-gray-300">{{ l.response_time ? l.response_time.toFixed(2) + 's' : '-' }}</td>
              <td class="py-2 px-3">
                <span :class="l.status_code < 400 ? 'text-green-400' : 'text-red-400'" class="font-medium">{{ l.status_code }}</span>
              </td>
              <td class="py-2 px-3 text-gray-300">{{ l.is_streaming ? '✓' : '-' }}</td>
              <td class="py-2 px-3 text-red-300 text-xs truncate max-w-xs">{{ l.error_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-between mt-4 text-sm text-gray-400">
        <span>Showing {{ logs.entries.length }} of {{ logs.total }} entries</span>
        <div class="flex gap-2">
          <button v-if="filters.offset > 0" @click="prevPage" class="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">← Previous</button>
          <button v-if="logs.entries.length >= filters.limit" @click="nextPage" class="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">Next →</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getLogs, getChannels } from '../api.js'

const channels = ref([])
const logs = ref({ total: 0, entries: [] })
const loading = ref(true)
const filters = ref({ channel_id: '', status_code: '', limit: 100, offset: 0 })

function formatTime(ts) {
  if (!ts) return '-'
  return ts.replace('T', ' ').substring(0, 19)
}

async function refresh() {
  loading.value = true
  const params = {}
  if (filters.value.channel_id) params.channel_id = filters.value.channel_id
  if (filters.value.status_code) params.status_code = filters.value.status_code
  params.limit = filters.value.limit
  params.offset = filters.value.offset
  logs.value = await getLogs(params)
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

onMounted(async () => {
  channels.value = await getChannels()
  await refresh()
})
</script>