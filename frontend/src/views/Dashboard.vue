<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">Dashboard</h2>
    <div v-if="loading" class="text-gray-400">Loading...</div>
    <div v-else>
      <!-- Top stats cards -->
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="text-gray-400 text-sm mb-1">Total Requests</div>
          <div class="text-3xl font-bold text-white">{{ stats.total_requests }}</div>
        </div>
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="text-gray-400 text-sm mb-1">Success Rate</div>
          <div class="text-3xl font-bold text-green-400">{{ 100 - stats.error_rate }}%</div>
        </div>
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="text-gray-400 text-sm mb-1">Avg Response Time</div>
          <div class="text-3xl font-bold text-indigo-400">{{ stats.avg_response_time }}s</div>
        </div>
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="text-gray-400 text-sm mb-1">Total Tokens</div>
          <div class="text-3xl font-bold text-yellow-400">{{ stats.total_tokens }}</div>
        </div>
      </div>

      <!-- Channel / Key stats -->
      <div class="grid grid-cols-3 gap-4 mb-6">
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 class="text-lg font-semibold mb-3">Channels</h3>
          <div class="flex justify-between items-center mb-2">
            <span class="text-gray-400">Total</span>
            <span class="text-white font-bold">{{ stats.total_channels }}</span>
          </div>
          <div class="flex justify-between items-center mb-2">
            <span class="text-gray-400">Active</span>
            <span class="text-green-400 font-bold">{{ stats.active_channels }}</span>
          </div>
        </div>
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 class="text-lg font-semibold mb-3">Keys</h3>
          <div class="flex justify-between items-center mb-2">
            <span class="text-gray-400">Total</span>
            <span class="text-white font-bold">{{ stats.total_keys }}</span>
          </div>
          <div class="flex justify-between items-center mb-2">
            <span class="text-gray-400">Active</span>
            <span class="text-green-400 font-bold">{{ stats.active_keys }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-400">Error</span>
            <span class="text-red-400 font-bold">{{ stats.error_keys }}</span>
          </div>
        </div>
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 class="text-lg font-semibold mb-3">Error Rate</h3>
          <div class="flex items-center justify-center h-24">
            <div class="text-5xl font-bold" :class="stats.error_rate > 10 ? 'text-red-400' : stats.error_rate > 5 ? 'text-yellow-400' : 'text-green-400'">
              {{ stats.error_rate }}%
            </div>
          </div>
        </div>
      </div>

      <!-- Recent errors -->
      <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
        <h3 class="text-lg font-semibold mb-3">Recent Errors</h3>
        <div v-if="stats.recent_errors && stats.recent_errors.length === 0" class="text-gray-400 text-center py-4">
          No recent errors ✅
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-gray-400 border-b border-gray-700">
                <th class="py-2 px-3 text-left">Time</th>
                <th class="py-2 px-3 text-left">Channel</th>
                <th class="py-2 px-3 text-left">Key</th>
                <th class="py-2 px-3 text-left">Model</th>
                <th class="py-2 px-3 text-left">Status</th>
                <th class="py-2 px-3 text-left">Error</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="err in stats.recent_errors" class="border-b border-gray-700/50 hover:bg-gray-700/30">
                <td class="py-2 px-3 text-gray-300">{{ formatTime(err.timestamp) }}</td>
                <td class="py-2 px-3 text-gray-300">{{ err.channel || '-' }}</td>
                <td class="py-2 px-3 text-gray-300">{{ err.key || '-' }}</td>
                <td class="py-2 px-3 text-gray-300">{{ err.model || '-' }}</td>
                <td class="py-2 px-3 text-red-400">{{ err.status_code }}</td>
                <td class="py-2 px-3 text-red-300 truncate max-w-xs">{{ err.error_message || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDashboardStats } from '../api.js'

const stats = ref({})
const loading = ref(true)

function formatTime(ts) {
  if (!ts) return '-'
  return ts.replace('T', ' ').substring(0, 19)
}

onMounted(async () => {
  try {
    stats.value = await getDashboardStats()
  } catch (e) {
    console.error(e)
  }
  loading.value = false
})
</script>