<template>
  <div>
    <div class="flex items-center gap-3 mb-6">
      <button @click="$router.push('/channels')" class="text-gray-400 hover:text-white transition-colors">← Back</button>
      <h2 class="text-2xl font-bold">{{ channel.name }}</h2>
      <span v-if="channel.enabled" class="px-2 py-0.5 bg-green-600/20 text-green-400 text-xs rounded-full">Active</span>
      <span v-else class="px-2 py-0.5 bg-red-600/20 text-red-400 text-xs rounded-full">Disabled</span>
    </div>

    <!-- Channel info -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <div class="grid grid-cols-4 gap-4">
        <div>
          <div class="text-gray-400 text-sm">Base URL</div>
          <div class="text-white text-sm mt-1">{{ channel.base_url }}</div>
        </div>
        <div>
          <div class="text-gray-400 text-sm">Strategy</div>
          <div class="text-white text-sm mt-1">{{ channel.strategy }}</div>
        </div>
        <div>
          <div class="text-gray-400 text-sm">Weight</div>
          <div class="text-white text-sm mt-1">{{ channel.weight }}</div>
        </div>
        <div>
          <div class="text-gray-400 text-sm">Keys</div>
          <div class="text-white text-sm mt-1">{{ keys.length }} total · {{ keys.filter(k => k.status === 'active').length }} active</div>
        </div>
      </div>
    </div>

    <!-- Edit channel -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <h3 class="text-lg font-semibold mb-3">Edit Channel</h3>
      <div class="grid grid-cols-4 gap-4">
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Strategy</label>
          <select v-model="editData.strategy" @change="saveChannel" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm">
            <option value="round_robin">Round Robin</option>
            <option value="weighted">Weighted</option>
            <option value="random">Random</option>
            <option value="least_used">Least Used</option>
          </select>
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Weight</label>
          <input v-model.number="editData.weight" @change="saveChannel" type="number" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm" min="1">
        </div>
        <div>
          <label class="text-sm text-gray-400 mb-1 block">Enabled</label>
          <div class="flex items-center gap-2 mt-2">
            <button @click="toggleEnabled" :class="editData.enabled ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-600 hover:bg-gray-500'" class="px-4 py-2 rounded-lg text-sm font-medium transition-colors">
              {{ editData.enabled ? 'Enabled' : 'Disabled' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Keys table -->
    <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold">Keys</h3>
        <div class="flex gap-3">
          <button @click="showBatchAdd = true" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors">
            + Batch Add Keys
          </button>
          <button @click="purgeErrorKeys" class="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg text-sm font-medium transition-colors">
            Purge Error Keys
          </button>
        </div>
      </div>

      <div v-if="keys.length === 0" class="text-gray-400 text-center py-8">
        No keys added yet.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-gray-400 border-b border-gray-700">
              <th class="py-2 px-3 text-left">Key</th>
              <th class="py-2 px-3 text-left">Status</th>
              <th class="py-2 px-3 text-left">Weight</th>
              <th class="py-2 px-3 text-left">Requests</th>
              <th class="py-2 px-3 text-left">Success</th>
              <th class="py-2 px-3 text-left">Avg RT</th>
              <th class="py-2 px-3 text-left">Errors</th>
              <th class="py-2 px-3 text-left">Last Used</th>
              <th class="py-2 px-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="k in keys" class="border-b border-gray-700/50 hover:bg-gray-700/30">
              <td class="py-2 px-3 text-gray-300 font-mono text-xs">{{ maskKey(k.value) }}</td>
              <td class="py-2 px-3">
                <span :class="statusClass(k.status)" class="px-2 py-0.5 rounded-full text-xs">{{ k.status }}</span>
              </td>
              <td class="py-2 px-3 text-gray-300">{{ k.weight }}</td>
              <td class="py-2 px-3 text-gray-300">{{ k.total_requests }}</td>
              <td class="py-2 px-3 text-gray-300">{{ k.success_requests }}</td>
              <td class="py-2 px-3 text-gray-300">{{ k.avg_response_time.toFixed(2) }}s</td>
              <td class="py-2 px-3">
                <span :class="k.error_count > 0 ? 'text-red-400' : 'text-gray-400'">{{ k.error_count }}</span>
              </td>
              <td class="py-2 px-3 text-gray-400 text-xs">{{ formatTime(k.last_used) }}</td>
              <td class="py-2 px-3">
                <div class="flex gap-2">
                  <button v-if="k.status === 'error'" @click="activateKey(k.id)" class="text-xs px-2 py-1 bg-green-600/20 text-green-400 rounded hover:bg-green-600/30 transition-colors">Activate</button>
                  <button v-if="k.status === 'active'" @click="disableKey(k.id)" class="text-xs px-2 py-1 bg-gray-600/20 text-gray-400 rounded hover:bg-gray-600/30 transition-colors">Disable</button>
                  <button @click="deleteKey(k.id)" class="text-xs px-2 py-1 bg-red-600/20 text-red-400 rounded hover:bg-red-600/30 transition-colors">Delete</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Batch Add Keys Modal -->
    <div v-if="showBatchAdd" class="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
      <div class="bg-gray-800 rounded-xl p-6 w-[560px] border border-gray-700">
        <h3 class="text-lg font-semibold mb-4">Batch Add Keys</h3>
        <p class="text-gray-400 text-sm mb-3">Paste keys below, separated by commas or new lines:</p>
        <textarea v-model="batchKeys" rows="8" class="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none text-sm resize-none" placeholder="sk-xxx1,sk-xxx2&#10;sk-xxx3"></textarea>
        <div class="flex justify-end gap-3 mt-4">
          <button @click="showBatchAdd = false" class="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">Cancel</button>
          <button @click="submitBatchKeys" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors">Add Keys</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { getChannel, updateChannel, getKeys, batchCreateKeys, updateKey, deleteKey as deleteKeyApi, batchDeleteKeys, getChannelStats } from '../api.js'

const route = useRoute()
const channelId = parseInt(route.params.id)
const channel = ref({ name: '', base_url: '', strategy: '', enabled: true, weight: 1, key_count: 0, active_key_count: 0 })
const keys = ref([])
const editData = ref({ strategy: '', weight: 1, enabled: true })
const showBatchAdd = ref(false)
const batchKeys = ref('')

function maskKey(val) {
  if (!val) return ''
  if (val.length <= 8) return val
  return val.substring(0, 6) + '...' + val.substring(val.length - 4)
}

function statusClass(status) {
  if (status === 'active') return 'bg-green-600/20 text-green-400'
  if (status === 'error') return 'bg-red-600/20 text-red-400'
  return 'bg-gray-600/20 text-gray-400'
}

function formatTime(ts) {
  if (!ts) return '-'
  return ts.replace('T', ' ').substring(0, 19)
}

async function refresh() {
  channel.value = await getChannel(channelId)
  editData.value.strategy = channel.value.strategy
  editData.value.weight = channel.value.weight
  editData.value.enabled = channel.value.enabled
  keys.value = await getKeys({ channel_id: channelId })
}

async function saveChannel() {
  await updateChannel(channelId, editData.value)
  await refresh()
}

async function toggleEnabled() {
  editData.value.enabled = !editData.value.enabled
  await saveChannel()
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
  if (!confirm('Delete this key?')) return
  await deleteKeyApi(keyId)
  await refresh()
}

async function purgeErrorKeys() {
  if (!confirm('Delete all error keys in this channel?')) return
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
    alert('Error: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(refresh)
</script>