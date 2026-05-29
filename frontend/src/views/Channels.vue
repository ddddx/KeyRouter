<template>
  <div>
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
      <h2 class="text-2xl font-bold">Channels</h2>
      <button @click="showAddModal = true" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors">
        + Add Channel
      </button>
    </div>

    <div v-if="loading" class="text-gray-400">Loading...</div>
    <div v-else-if="channels.length === 0" class="text-gray-400 text-center py-12">
      No channels yet. Click "Add Channel" to create one.
    </div>
    <div v-else class="grid grid-cols-1 gap-4">
      <div v-for="ch in channels" class="bg-gray-800 rounded-xl p-5 border border-gray-700 hover:border-indigo-500/50 transition-colors cursor-pointer"
           @click="$router.push(`/channels/${ch.id}`)">
        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-3">
              <h3 class="text-lg font-semibold">{{ ch.name }}</h3>
              <span v-if="ch.enabled" class="px-2 py-0.5 bg-green-600/20 text-green-400 text-xs rounded-full">Active</span>
              <span v-else class="px-2 py-0.5 bg-red-600/20 text-red-400 text-xs rounded-full">Disabled</span>
            </div>
            <div class="text-gray-400 text-sm mt-1 break-all">{{ ch.base_url }}</div>
          </div>
          <div class="flex flex-wrap items-center gap-4 lg:gap-6">
            <div class="text-center">
              <div class="text-gray-400 text-xs">Strategy</div>
              <div class="text-white text-sm font-medium">{{ ch.strategy }}</div>
            </div>
            <div class="text-center">
              <div class="text-gray-400 text-xs">Keys</div>
              <div class="text-white text-sm font-medium">{{ ch.key_count }}</div>
            </div>
            <div class="text-center">
              <div class="text-gray-400 text-xs">Active</div>
              <div class="text-green-400 text-sm font-medium">{{ ch.active_key_count }}</div>
            </div>
            <button @click.stop="deleteChannel(ch.id)" class="p-2 text-red-400 hover:text-red-300 hover:bg-red-600/10 rounded-lg transition-colors">
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Channel Modal -->
    <div v-if="showAddModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
      <div class="bg-gray-800 rounded-xl p-6 w-[calc(100vw-2rem)] max-w-[480px] border border-gray-700">
        <h3 class="text-lg font-semibold mb-4">Add Channel</h3>
        <div class="space-y-4">
          <div>
            <label class="text-sm text-gray-400 mb-1 block">Name</label>
            <input v-model="newChannel.name" class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none" placeholder="e.g. OpenAI Official">
          </div>
          <div>
            <label class="text-sm text-gray-400 mb-1 block">Base URL</label>
            <input v-model="newChannel.base_url" class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none" placeholder="https://api.openai.com">
          </div>
          <div>
            <label class="text-sm text-gray-400 mb-1 block">Strategy</label>
            <select v-model="newChannel.strategy" class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none">
              <option value="round_robin">Round Robin</option>
              <option value="weighted">Weighted</option>
              <option value="random">Random</option>
              <option value="least_used">Least Used</option>
            </select>
          </div>
          <div>
            <label class="text-sm text-gray-400 mb-1 block">Weight</label>
            <input v-model.number="newChannel.weight" type="number" class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none" min="1">
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button @click="showAddModal = false" class="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors">Cancel</button>
          <button @click="addChannel" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors">Create</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getChannels, createChannel, deleteChannel as deleteChannelApi } from '../api.js'

const channels = ref([])
const loading = ref(true)
const showAddModal = ref(false)
const newChannel = ref({ name: '', base_url: '', strategy: 'round_robin', weight: 1 })

async function refresh() {
  loading.value = true
  channels.value = await getChannels()
  loading.value = false
}

async function addChannel() {
  try {
    await createChannel(newChannel.value)
    showAddModal.value = false
    newChannel.value = { name: '', base_url: '', strategy: 'round_robin', weight: 1 }
    await refresh()
  } catch (e) {
    alert('Error: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteChannel(id) {
  if (!confirm('Delete this channel and all its keys?')) return
  await deleteChannelApi(id)
  await refresh()
}

onMounted(refresh)
</script>
