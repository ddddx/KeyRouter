<template>
  <div>
    <h2 class="text-2xl font-bold mb-6">Dashboard</h2>
    <div v-if="loading" class="text-gray-400">Loading...</div>
    <div v-else>
      <!-- Top stats cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="text-gray-400 text-sm mb-1">Total Requests</div>
          <div class="text-3xl font-bold text-white">{{ stats.total_requests }}</div>
          <div class="text-xs text-gray-500 mt-1">{{ stats.success_requests }} success / {{ stats.failed_requests }} failed</div>
        </div>
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="text-gray-400 text-sm mb-1">Success Rate</div>
          <div class="text-3xl font-bold text-green-400">{{ stats.success_rate }}%</div>
          <div class="text-xs text-red-400 mt-1">Error rate: {{ stats.error_rate }}%</div>
        </div>
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="text-gray-400 text-sm mb-1">Avg Response Time</div>
          <div class="text-3xl font-bold text-indigo-400">{{ stats.avg_response_time_ms }}ms</div>
        </div>
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="text-gray-400 text-sm mb-1">Total Tokens</div>
          <div class="text-3xl font-bold text-yellow-400">{{ stats.total_tokens }}</div>
          <div class="text-xs text-gray-500 mt-1">{{ stats.total_prompt_tokens }} prompt / {{ stats.total_completion_tokens }} completion</div>
        </div>
      </div>

      <!-- Channel / Key stats -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <h3 class="text-lg font-semibold mb-3">Channels</h3>
          <div class="flex justify-between items-center mb-2">
            <span class="text-gray-400">Total</span>
            <span class="text-white font-bold">{{ stats.total_channels }}</span>
          </div>
          <div class="flex justify-between items-center">
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

      <!-- Trend Charts -->
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-6">
        <!-- Hourly Trend -->
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
            <h3 class="text-lg font-semibold">Hourly Trend (48h)</h3>
            <div class="flex gap-2 text-xs">
              <span class="text-green-400">● Success</span>
              <span class="text-red-400">● Failed</span>
            </div>
          </div>
          <div class="h-48 flex items-end gap-px overflow-x-auto" v-if="stats.hourly_trend && stats.hourly_trend.length > 0">
            <div v-for="h in stats.hourly_trend" class="flex flex-col items-center justify-end min-w-[8px] flex-1 h-full relative">
              <div class="w-full bg-green-500/80 rounded-t" :style="{ height: barHeight(h.success, maxHourly) + '%' }"></div>
              <div class="w-full bg-red-500/80 rounded-t" :style="{ height: barHeight(h.failed, maxHourly) + '%' }"></div>
            </div>
          </div>
          <div v-else class="h-48 flex items-center justify-center text-gray-500 text-sm">No data yet</div>
          <div class="flex justify-between text-xs text-gray-500 mt-2" v-if="stats.hourly_trend && stats.hourly_trend.length > 0">
            <span>{{ stats.hourly_trend[0]?.time }}</span>
            <span>{{ stats.hourly_trend[stats.hourly_trend.length - 1]?.time }}</span>
          </div>
        </div>

        <!-- Daily Trend -->
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
            <h3 class="text-lg font-semibold">Daily Trend (30d)</h3>
            <div class="flex gap-2 text-xs">
              <span class="text-green-400">● Success</span>
              <span class="text-red-400">● Failed</span>
            </div>
          </div>
          <div class="h-48 flex items-end gap-1 overflow-x-auto" v-if="stats.daily_trend && stats.daily_trend.length > 0">
            <div v-for="d in stats.daily_trend" class="flex flex-col items-center justify-end min-w-[10px] flex-1 h-full relative">
              <div class="w-full bg-green-500/80 rounded-t" :style="{ height: barHeight(d.success, maxDaily) + '%' }"></div>
              <div class="w-full bg-red-500/80 rounded-t" :style="{ height: barHeight(d.failed, maxDaily) + '%' }"></div>
            </div>
          </div>
          <div v-else class="h-48 flex items-center justify-center text-gray-500 text-sm">No data yet</div>
          <div class="flex justify-between text-xs text-gray-500 mt-2" v-if="stats.daily_trend && stats.daily_trend.length > 0">
            <span>{{ stats.daily_trend[0]?.time }}</span>
            <span>{{ stats.daily_trend[stats.daily_trend.length - 1]?.time }}</span>
          </div>
        </div>
      </div>

      <!-- Model Stats -->
      <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6" v-if="stats.model_stats && stats.model_stats.length > 0">
        <h3 class="text-lg font-semibold mb-3">Model Usage Statistics</h3>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-gray-400 border-b border-gray-700">
                <th class="py-2 px-3 text-left">Model</th>
                <th class="py-2 px-3 text-left">Requests</th>
                <th class="py-2 px-3 text-left">Success</th>
                <th class="py-2 px-3 text-left">Failed</th>
                <th class="py-2 px-3 text-left">Success Rate</th>
                <th class="py-2 px-3 text-left">Avg RT</th>
                <th class="py-2 px-3 text-left">Tokens</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in stats.model_stats" class="border-b border-gray-700/50 hover:bg-gray-700/30">
                <td class="py-2 px-3 text-gray-300 font-medium">{{ m.model }}</td>
                <td class="py-2 px-3 text-gray-300">{{ m.total_requests }}</td>
                <td class="py-2 px-3 text-green-400">{{ m.success_requests }}</td>
                <td class="py-2 px-3 text-red-400">{{ m.failed_requests }}</td>
                <td class="py-2 px-3">
                  <span :class="m.success_rate >= 95 ? 'text-green-400' : m.success_rate >= 80 ? 'text-yellow-400' : 'text-red-400'">{{ m.success_rate }}%</span>
                </td>
                <td class="py-2 px-3 text-gray-300">{{ m.avg_response_time_ms }}ms</td>
                <td class="py-2 px-3 text-yellow-400">{{ m.total_tokens }}</td>
              </tr>
            </tbody>
          </table>
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
                <th class="py-2 px-3 text-left">Source IP</th>
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
                <td class="py-2 px-3 text-gray-300">{{ err.source_ip || '-' }}</td>
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
import { ref, computed, onMounted } from 'vue'
import { getDashboardStats } from '../api.js'

const stats = ref({})
const loading = ref(true)

function formatTime(ts) {
  if (!ts) return '-'
  return ts.replace('T', ' ').substring(0, 19)
}

const maxHourly = computed(() => {
  if (!stats.value.hourly_trend) return 1
  return Math.max(...stats.value.hourly_trend.map(h => h.total), 1)
})

const maxDaily = computed(() => {
  if (!stats.value.daily_trend) return 1
  return Math.max(...stats.value.daily_trend.map(d => d.total), 1)
})

function barHeight(value, max) {
  if (!max) return 0
  return Math.max(2, (value / max) * 90) // leave 10% padding at top
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
