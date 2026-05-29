<template>
  <div>
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
      <h1 class="text-2xl font-bold">对外 Key 管理</h1>
      <div class="flex flex-wrap gap-3">
        <button @click="showCreateModal = true" class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium">
          + 创建 Key
        </button>
        <button @click="showBatchModal = true" class="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm font-medium">
          + 批量生成
        </button>
      </div>
    </div>

    <!-- Filter -->
    <div class="flex flex-col sm:flex-row gap-3 sm:gap-4 mb-4">
      <select v-model="filterChannel" @change="fetchKeys" class="bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200">
        <option value="">全部渠道</option>
        <option value="none">未绑定渠道</option>
        <option v-for="ch in channels" :key="ch.id" :value="ch.id">{{ ch.name }}</option>
      </select>
      <select v-model="filterEnabled" @change="fetchKeys" class="bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200">
        <option value="">全部状态</option>
        <option value="true">已启用</option>
        <option value="false">已禁用</option>
      </select>
    </div>

    <!-- Table -->
    <div class="bg-gray-800 rounded-xl border border-gray-700 overflow-x-auto">
      <table class="w-full min-w-[900px] text-sm">
        <thead class="bg-gray-900 text-gray-400">
          <tr>
            <th class="px-4 py-3 text-left font-medium">名称</th>
            <th class="px-4 py-3 text-left font-medium">Key</th>
            <th class="px-4 py-3 text-left font-medium">绑定渠道</th>
            <th class="px-4 py-3 text-left font-medium">状态</th>
            <th class="px-4 py-3 text-left font-medium">限速 (req/min)</th>
            <th class="px-4 py-3 text-left font-medium">额度</th>
            <th class="px-4 py-3 text-left font-medium">请求次数</th>
            <th class="px-4 py-3 text-left font-medium">过期时间</th>
            <th class="px-4 py-3 text-left font-medium">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-700">
          <tr v-for="ak in apiKeys" :key="ak.id" class="hover:bg-gray-700/50">
            <td class="px-4 py-3 text-gray-300">{{ ak.name || '-' }}</td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <span class="text-gray-400 text-xs font-mono">{{ ak.value_masked }}</span>
                <button @click="copyKey(ak.value)" class="text-gray-500 hover:text-indigo-400 transition-colors" title="复制完整Key">
                  📋
                </button>
              </div>
            </td>
            <td class="px-4 py-3 text-gray-300">{{ ak.channel_name || '自动匹配' }}</td>
            <td class="px-4 py-3">
              <span :class="statusBadge(ak.status)">{{ statusLabel(ak.status) }}</span>
            </td>
            <td class="px-4 py-3 text-gray-300">{{ ak.rate_limit || '不限' }}</td>
            <td class="px-4 py-3 text-gray-300">
              <span v-if="ak.total_quota !== null">
                {{ formatMoney(ak.used_quota) }} / {{ formatMoney(ak.total_quota) }}
                <span class="text-xs text-gray-500">({{ quotaPercent(ak) }}%)</span>
              </span>
              <span v-else class="text-gray-500">不限</span>
            </td>
            <td class="px-4 py-3 text-gray-300">{{ ak.total_requests }}</td>
            <td class="px-4 py-3 text-gray-300">{{ ak.expires_at ? formatDate(ak.expires_at) : '永不过期' }}</td>
            <td class="px-4 py-3">
              <div class="flex gap-2">
                <button @click="toggleEnabled(ak)" :class="ak.enabled ? 'text-yellow-500 hover:text-yellow-400' : 'text-green-500 hover:text-green-400'" :title="ak.enabled ? '禁用' : '启用'">
                  {{ ak.enabled ? '🔒' : '🔓' }}
                </button>
                <button @click="deleteKey(ak)" class="text-red-500 hover:text-red-400" title="删除">🗑️</button>
              </div>
            </td>
          </tr>
          <tr v-if="apiKeys.length === 0">
            <td colspan="9" class="px-4 py-8 text-center text-gray-500">暂无对外 Key，点击上方按钮创建</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50" @click.self="showCreateModal = false">
      <div class="bg-gray-800 rounded-xl border border-gray-600 p-6 w-[calc(100vw-2rem)] max-w-md">
        <h2 class="text-lg font-bold mb-4">创建对外 Key</h2>
        <div class="space-y-3">
          <div>
            <label class="block text-sm text-gray-400 mb-1">备注名称</label>
            <input v-model="createForm.name" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" placeholder="可选" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">绑定渠道</label>
            <select v-model="createForm.channel_id" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200">
              <option value="">自动匹配（根据 model 选择渠道）</option>
              <option v-for="ch in channels" :key="ch.id" :value="ch.id">{{ ch.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">限速 (req/min)</label>
            <input v-model="createForm.rate_limit" type="number" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" placeholder="不限" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">总额度 ($)</label>
            <input v-model="createForm.total_quota" type="number" step="0.01" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" placeholder="不限" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">过期时间</label>
            <input v-model="createForm.expires_at" type="datetime-local" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">自定义 Key 前缀</label>
            <input v-model="createForm.prefix" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" placeholder="sk-keyrouter-" />
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button @click="showCreateModal = false" class="px-4 py-2 text-gray-400 hover:text-gray-200 text-sm">取消</button>
          <button @click="createSingleKey" class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium" :disabled="creating">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Batch Create Modal -->
    <div v-if="showBatchModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50" @click.self="showBatchModal = false">
      <div class="bg-gray-800 rounded-xl border border-gray-600 p-6 w-[calc(100vw-2rem)] max-w-md">
        <h2 class="text-lg font-bold mb-4">批量生成对外 Key</h2>
        <div class="space-y-3">
          <div>
            <label class="block text-sm text-gray-400 mb-1">数量 (1-100)</label>
            <input v-model="batchForm.count" type="number" min="1" max="100" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">名称前缀</label>
            <input v-model="batchForm.name_prefix" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" placeholder="可选，如 test- → test-1, test-2, ..." />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">绑定渠道</label>
            <select v-model="batchForm.channel_id" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200">
              <option value="">自动匹配</option>
              <option v-for="ch in channels" :key="ch.id" :value="ch.id">{{ ch.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">限速 (req/min)</label>
            <input v-model="batchForm.rate_limit" type="number" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" placeholder="不限" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">总额度 ($)</label>
            <input v-model="batchForm.total_quota" type="number" step="0.01" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" placeholder="不限" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">过期时间</label>
            <input v-model="batchForm.expires_at" type="datetime-local" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">自定义 Key 前缀</label>
            <input v-model="batchForm.prefix" class="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200" placeholder="sk-keyrouter-" />
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button @click="showBatchModal = false" class="px-4 py-2 text-gray-400 hover:text-gray-200 text-sm">取消</button>
          <button @click="batchCreateKeys" class="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-sm font-medium" :disabled="creating">
            {{ creating ? '生成中...' : '批量生成' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Copy toast -->
    <div v-if="copyToast" class="fixed top-4 right-4 bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm z-50 shadow-lg">
      ✅ Key 已复制到剪贴板
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getChannels, getApiKeys, createApiKey, batchCreateApiKeys, updateApiKey, deleteApiKey } from '../api.js'

const apiKeys = ref([])
const channels = ref([])
const filterChannel = ref('')
const filterEnabled = ref('')
const showCreateModal = ref(false)
const showBatchModal = ref(false)
const creating = ref(false)
const copyToast = ref(false)

const createForm = ref({
  name: '',
  channel_id: '',
  rate_limit: null,
  total_quota: null,
  expires_at: '',
  prefix: '',
})

const batchForm = ref({
  count: 5,
  name_prefix: '',
  channel_id: '',
  rate_limit: null,
  total_quota: null,
  expires_at: '',
  prefix: '',
})

onMounted(async () => {
  await fetchChannels()
  await fetchKeys()
})

async function fetchChannels() {
  try {
    channels.value = await getChannels()
  } catch (e) {
    console.error('Failed to fetch channels', e)
  }
}

async function fetchKeys() {
  try {
    const params = {}
    if (filterChannel.value === 'none') {
      // Fetch all, then filter client-side for null channel_id
    } else if (filterChannel.value) {
      params.channel_id = filterChannel.value
    }
    if (filterEnabled.value) {
      params.enabled = filterEnabled.value
    }
    let keys = await getApiKeys(params)
    if (filterChannel.value === 'none') {
      keys = keys.filter(k => k.channel_id === null)
    }
    apiKeys.value = keys
  } catch (e) {
    console.error('Failed to fetch api keys', e)
  }
}

async function createSingleKey() {
  creating.value = true
  try {
    const data = {
      name: createForm.value.name || null,
      channel_id: createForm.value.channel_id ? parseInt(createForm.value.channel_id) : null,
      rate_limit: createForm.value.rate_limit ? parseInt(createForm.value.rate_limit) : null,
      total_quota: createForm.value.total_quota ? parseFloat(createForm.value.total_quota) : null,
      expires_at: createForm.value.expires_at || null,
      prefix: createForm.value.prefix || null,
    }
    const result = await createApiKey(data)
    // Auto-copy the new key value
    await copyKey(result.value)
    showCreateModal.value = false
    createForm.value = { name: '', channel_id: '', rate_limit: null, total_quota: null, expires_at: '', prefix: '' }
    await fetchKeys()
  } catch (e) {
    alert('创建失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

async function batchCreateKeys() {
  creating.value = true
  try {
    const data = {
      count: parseInt(batchForm.value.count) || 5,
      name_prefix: batchForm.value.name_prefix || null,
      channel_id: batchForm.value.channel_id ? parseInt(batchForm.value.channel_id) : null,
      rate_limit: batchForm.value.rate_limit ? parseInt(batchForm.value.rate_limit) : null,
      total_quota: batchForm.value.total_quota ? parseFloat(batchForm.value.total_quota) : null,
      expires_at: batchForm.value.expires_at || null,
      prefix: batchForm.value.prefix || null,
    }
    const results = await batchCreateApiKeys(data)
    alert(`成功生成 ${results.length} 个对外 Key`)
    showBatchModal.value = false
    batchForm.value = { count: 5, name_prefix: '', channel_id: '', rate_limit: null, total_quota: null, expires_at: '', prefix: '' }
    await fetchKeys()
  } catch (e) {
    alert('批量生成失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

async function toggleEnabled(ak) {
  try {
    await updateApiKey(ak.id, { enabled: !ak.enabled })
    await fetchKeys()
  } catch (e) {
    alert('操作失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteKey(ak) {
  if (!confirm(`确定删除对外 Key "${ak.name || ak.value_masked}"？此操作不可恢复。`)) return
  try {
    await deleteApiKey(ak.id)
    await fetchKeys()
  } catch (e) {
    alert('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function copyKey(value) {
  try {
    await navigator.clipboard.writeText(value)
    copyToast.value = true
    setTimeout(() => { copyToast.value = false }, 2000)
  } catch (e) {
    // Fallback for older browsers
    const textarea = document.createElement('textarea')
    textarea.value = value
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    copyToast.value = true
    setTimeout(() => { copyToast.value = false }, 2000)
  }
}

function statusBadge(status) {
  const map = {
    active: 'px-2 py-1 rounded text-xs font-medium bg-green-900/50 text-green-400',
    disabled: 'px-2 py-1 rounded text-xs font-medium bg-gray-700 text-gray-400',
    expired: 'px-2 py-1 rounded text-xs font-medium bg-yellow-900/50 text-yellow-400',
    exhausted: 'px-2 py-1 rounded text-xs font-medium bg-red-900/50 text-red-400',
  }
  return map[status] || map.active
}

function statusLabel(status) {
  const map = { active: '✅ 可用', disabled: '🔒 禁用', expired: '⏰ 过期', exhausted: '🚫 额度耗尽' }
  return map[status] || status
}

function quotaPercent(ak) {
  if (!ak.total_quota) return 0
  return Math.min(100, Math.round((ak.used_quota || 0) / ak.total_quota * 100))
}

function formatMoney(value) {
  return Number(value || 0).toFixed(2)
}

function formatDate(dt) {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 19)
}
</script>
