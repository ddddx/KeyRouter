<template>
  <div>
    <div class="flex flex-wrap items-center gap-3 mb-6">
      <button @click="$router.push('/channels')" class="text-gray-400 hover:text-white transition-colors">← {{ t('common.back') }}</button>
      <h2 class="text-2xl font-bold">{{ channel.name }}</h2>
      <span v-if="channel.enabled" class="px-2 py-0.5 bg-green-600/20 text-green-400 text-xs rounded-full">{{ t('common.active') }}</span>
      <span v-else class="px-2 py-0.5 bg-red-600/20 text-red-400 text-xs rounded-full">{{ t('common.disabled') }}</span>
    </div>

    <!-- Channel info -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div>
          <div class="text-gray-400 text-sm">{{ t('channels.baseUrl') }}</div>
          <div class="text-white text-sm mt-1 break-all">{{ channel.base_url }}</div>
        </div>
        <div>
          <div class="text-gray-400 text-sm">{{ t('channels.strategy') }}</div>
          <div class="text-white text-sm mt-1">{{ strategyLabel(channel.strategy) }}</div>
        </div>
        <div>
          <div class="text-gray-400 text-sm">{{ t('channels.weight') }}</div>
          <div class="text-white text-sm mt-1">{{ channel.weight }}</div>
        </div>
        <div>
          <div class="text-gray-400 text-sm">{{ t('channels.keys') }}</div>
          <div class="text-white text-sm mt-1">{{ keys.length }} {{ t('common.total') }} · {{ keys.filter(k => k.status === 'active').length }} {{ t('common.active') }}</div>
        </div>
      </div>
    </div>

    <!-- Edit channel -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
        <h3 class="text-lg font-semibold">{{ t('channels.edit') }}</h3>
        <button
          @click="saveChannel"
          :disabled="saving"
          class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ saving ? t('common.saving') : t('channels.save') }}
        </button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('channels.name') }}</label>
          <input v-model="editData.name" type="text" :aria-label="t('channels.name')" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
        </div>
        <div class="sm:col-span-2">
          <label class="text-sm text-gray-400 mb-1 block">{{ t('channels.baseUrl') }}</label>
          <input v-model="editData.base_url" type="url" :aria-label="t('channels.baseUrl')" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
          <p class="text-xs text-gray-500 mt-1">{{ t('channels.baseUrlHint') }}</p>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('channels.strategy') }}</label>
          <select v-model="editData.strategy" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
            <option value="round_robin">{{ strategyLabel('round_robin') }}</option>
            <option value="weighted">{{ strategyLabel('weighted') }}</option>
            <option value="random">{{ strategyLabel('random') }}</option>
            <option value="least_used">{{ strategyLabel('least_used') }}</option>
          </select>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('channels.weight') }}</label>
          <input v-model.number="editData.weight" type="number" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm" min="1">
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">{{ t('common.status') }}</label>
          <div class="flex items-center gap-2 mt-2">
            <button @click="toggleEnabled" :class="editData.enabled ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-600 hover:bg-gray-500'" class="px-4 py-2 rounded-lg text-sm font-medium transition-colors" type="button">
              {{ editData.enabled ? t('common.enabled') : t('common.disabled') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Channel Stats -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6" v-if="channelStats">
      <h3 class="text-lg font-semibold mb-3">{{ t('channels.channelStats') }}</h3>
      <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-4">
        <div>
          <div class="text-gray-400 text-xs">{{ t('channels.requests') }}</div>
          <div class="text-white font-bold">{{ channelStats.total_requests }}</div>
        </div>
        <div>
          <div class="text-gray-400 text-xs">{{ t('common.success') }}</div>
          <div class="text-green-400 font-bold">{{ channelStats.success_requests }}</div>
        </div>
        <div>
          <div class="text-gray-400 text-xs">{{ t('common.failed') }}</div>
          <div class="text-red-400 font-bold">{{ channelStats.failed_requests }}</div>
        </div>
        <div>
          <div class="text-gray-400 text-xs">{{ t('dashboard.successRate') }}</div>
          <div class="text-white font-bold">{{ channelStats.success_rate }}%</div>
        </div>
        <div>
          <div class="text-gray-400 text-xs">{{ t('channels.avgRt') }}</div>
          <div class="text-indigo-400 font-bold">{{ channelStats.avg_response_time_ms }}ms</div>
        </div>
        <div>
          <div class="text-gray-400 text-xs">{{ t('logs.tokens') }}</div>
          <div class="text-yellow-400 font-bold">{{ channelStats.total_tokens }}</div>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <div class="text-gray-400 text-xs">{{ t('channels.keyCount') }}</div>
          <div class="text-white">{{ channelStats.key_count }} ({{ channelStats.active_key_count }} {{ t('common.active') }}, {{ channelStats.error_key_count }} {{ t('common.error') }})</div>
        </div>
      </div>
    </div>

    <!-- Key Statistics Table -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <h3 class="text-lg font-semibold">{{ t('channels.keyStats') }}</h3>
        <div class="flex flex-wrap gap-3">
          <button @click="showBatchAdd = true" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors">
            + {{ t('channels.batchAddKeys') }}
          </button>
          <button @click="purgeErrorKeys" class="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg text-sm font-medium transition-colors">
            {{ t('channels.purgeErrorKeys') }}
          </button>
        </div>
      </div>

      <div v-if="keys.length === 0" class="text-gray-400 text-center py-8">
        {{ t('channels.noKeys') }}
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-gray-400 border-b border-gray-700">
              <th class="py-2 px-3 text-left">Key</th>
              <th class="py-2 px-3 text-left">{{ t('common.status') }}</th>
              <th class="py-2 px-3 text-left">{{ t('channels.requests') }}</th>
              <th class="py-2 px-3 text-left">{{ t('common.success') }}</th>
              <th class="py-2 px-3 text-left">{{ t('common.failed') }}</th>
              <th class="py-2 px-3 text-left">{{ t('channels.rate') }}</th>
              <th class="py-2 px-3 text-left">{{ t('channels.avgRt') }}</th>
              <th class="py-2 px-3 text-left">{{ t('logs.tokens') }}</th>
              <th class="py-2 px-3 text-left">{{ t('channels.lastUsed') }}</th>
              <th class="py-2 px-3 text-left">{{ t('common.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="k in keys" class="border-b border-gray-700/50 hover:bg-gray-700/30">
              <td class="py-2 px-3 text-gray-300 font-mono text-xs">{{ k.value_masked }}</td>
              <td class="py-2 px-3">
                <span :class="statusClass(k.status)" class="px-2 py-0.5 rounded-full text-xs">{{ keyStatusLabel(k.status) }}</span>
              </td>
              <td class="py-2 px-3 text-gray-300">{{ k.total_requests }}</td>
              <td class="py-2 px-3 text-green-400">{{ k.success_requests }}</td>
              <td class="py-2 px-3 text-red-400">{{ k.failed_requests }}</td>
              <td class="py-2 px-3">
                <span :class="k.success_rate >= 95 ? 'text-green-400' : k.success_rate >= 80 ? 'text-yellow-400' : 'text-red-400'">{{ k.success_rate }}%</span>
              </td>
              <td class="py-2 px-3 text-gray-300">{{ k.avg_response_time_ms }}ms</td>
              <td class="py-2 px-3 text-yellow-400">{{ k.total_tokens }}</td>
              <td class="py-2 px-3 text-gray-400 text-xs">{{ formatTime(k.last_used) }}</td>
              <td class="py-2 px-3">
                <div class="flex gap-2">
                  <button v-if="k.status === 'error'" @click="activateKey(k.id)" class="text-xs px-2 py-1 bg-green-600/20 text-green-400 rounded hover:bg-green-600/30 transition-colors">{{ t('common.active') }}</button>
                  <button v-if="k.status === 'active'" @click="disableKey(k.id)" class="text-xs px-2 py-1 bg-gray-600/20 text-gray-400 rounded hover:bg-gray-600/30 transition-colors">{{ t('common.disabled') }}</button>
                  <button @click="deleteKey(k.id)" class="text-xs px-2 py-1 bg-red-600/20 text-red-400 rounded hover:bg-red-600/30 transition-colors">{{ t('common.delete') }}</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Batch Add Keys Modal -->
    <div v-if="showBatchAdd" class="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
      <div class="bg-gray-800 rounded-xl p-6 w-[calc(100vw-2rem)] max-w-[560px] border border-gray-700">
        <h3 class="text-lg font-semibold mb-4">{{ t('channels.batchAddKeys') }}</h3>
        <p class="text-gray-400 text-sm mb-3">{{ t('channels.pasteKeys') }}</p>
        <textarea v-model="batchKeys" rows="8" class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm resize-none" placeholder="sk-xxx1,sk-xxx2&#10;sk-xxx3"></textarea>
        <div class="flex justify-end gap-3 mt-4">
          <button @click="showBatchAdd = false" class="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">{{ t('common.cancel') }}</button>
          <button @click="submitBatchKeys" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors">{{ t('channels.addKeys') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getChannel, updateChannel, getKeys, batchCreateKeys, updateKey, deleteKey as deleteKeyApi, batchDeleteKeys, getChannelStats } from '../api.js'
import { strategyLabel, t } from '../i18n.js'

const route = useRoute()
const channelId = parseInt(route.params.id)
const channel = ref({ name: '', base_url: '', strategy: '', enabled: true, weight: 1, key_count: 0, active_key_count: 0 })
const keys = ref([])
const channelStats = ref(null)
const editData = ref({ name: '', base_url: '', strategy: '', weight: 1, enabled: true })
const showBatchAdd = ref(false)
const batchKeys = ref('')
const saving = ref(false)

function statusClass(status) {
  if (status === 'active') return 'bg-green-600/20 text-green-400'
  if (status === 'error') return 'bg-red-600/20 text-red-400'
  return 'bg-gray-600/20 text-gray-400'
}

function formatTime(ts) {
  if (!ts) return '-'
  return ts.replace('T', ' ').substring(0, 19)
}

function keyStatusLabel(status) {
  if (status === 'active') return t('common.active')
  if (status === 'inactive') return t('common.inactive')
  if (status === 'error') return t('common.error')
  return status
}

function normalizeBaseUrl(url) {
  return url.trim().replace(/\/+$/, '').replace(/(?:\/v1)+$/i, '')
}

async function refresh() {
  channel.value = await getChannel(channelId)
  editData.value.name = channel.value.name
  editData.value.base_url = channel.value.base_url
  editData.value.strategy = channel.value.strategy
  editData.value.weight = channel.value.weight
  editData.value.enabled = channel.value.enabled
  keys.value = await getKeys({ channel_id: channelId })
  try {
    channelStats.value = await getChannelStats(channelId)
  } catch (e) {
    channelStats.value = null
  }
}

async function saveChannel() {
  saving.value = true
  try {
    await updateChannel(channelId, {
      ...editData.value,
      base_url: normalizeBaseUrl(editData.value.base_url),
    })
    await refresh()
  } catch (e) {
    alert(t('channels.saveFailed', { message: e.response?.data?.detail || e.message }))
  } finally {
    saving.value = false
  }
}

async function toggleEnabled() {
  editData.value.enabled = !editData.value.enabled
}

async function activateKey(keyId) {
  await updateKey(keyId, { status: 'active' })
  await refresh()
}

async function disableKey(keyId) {
  await updateKey(keyId, { status: 'inactive' })
  await refresh()
}

async function deleteKey(keyId) {
  if (!confirm(t('channels.deleteKeyConfirm'))) return
  await deleteKeyApi(keyId)
  await refresh()
}

async function purgeErrorKeys() {
  if (!confirm(t('channels.purgeConfirm'))) return
  await batchDeleteKeys({ channel_id: channelId, status: 'error' })
  await refresh()
}

async function submitBatchKeys() {
  if (!batchKeys.value.trim()) return
  try {
    await batchCreateKeys({ keys: batchKeys.value, channel_id: channelId, weight: 1 })
    showBatchAdd.value = false
    batchKeys.value = ''
    await refresh()
  } catch (e) {
    alert(t('common.operationFailed', { message: e.response?.data?.detail || e.message }))
  }
}

onMounted(refresh)
</script>
