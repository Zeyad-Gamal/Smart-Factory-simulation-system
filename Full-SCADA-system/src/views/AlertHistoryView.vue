<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// ── Config ────────────────────────────────────────────────────
const LARAVEL_URL  = '/api/'   // change if deployed
const SOC_URL      = 'http://localhost:5000'   // change if deployed
const POLL_INTERVAL = 5000                     // ms

// ── State ─────────────────────────────────────────────────────
const alerts          = ref([])
const loading         = ref(true)
const error           = ref(null)
const selectedAlert   = ref(null)
const filterSeverity  = ref('all')
const filterStatus    = ref('all')
const sortBy          = ref('newest')
const searchQuery     = ref('')
const mobileTab       = ref('list')
let   pollTimer       = null
let   socPollTimer    = null

// ── Severity config ───────────────────────────────────────────
const SEV = {
  critical: { label: 'Critical', textClass: 'text-red-400',   bgClass: 'bg-red-500/15',   borderClass: 'border-red-500/40',   dot: '#f87171' },
  high:     { label: 'High',     textClass: 'text-orange-400', bgClass: 'bg-orange-500/15', borderClass: 'border-orange-500/40', dot: '#fb923c' },
  medium:   { label: 'Medium',   textClass: 'text-yellow-400', bgClass: 'bg-yellow-500/15', borderClass: 'border-yellow-500/40', dot: '#facc15' },
  low:      { label: 'Low',      textClass: 'text-green-400',  bgClass: 'bg-green-500/15',  borderClass: 'border-green-500/40',  dot: '#4ade80' },
  info:     { label: 'Info',     textClass: 'text-blue-400',   bgClass: 'bg-blue-500/15',   borderClass: 'border-blue-500/40',   dot: '#60a5fa' },
}

function sevCfg(sev) {
  return SEV[(sev || 'info').toLowerCase()] || SEV.info
}

// ── Data fetching ─────────────────────────────────────────────

// Merge new alerts into existing list without duplicates
function mergeAlerts(newItems) {
  const existing = new Set(alerts.value.map(a => a.decision_id))
  const fresh = newItems.filter(a => !existing.has(a.decision_id))
  if (fresh.length > 0) {
    alerts.value = [...fresh, ...alerts.value]
  }
}

// 1. Fetch from Laravel (resolved decisions stored in DB)
async function fetchFromLaravel() {
  try {
    const res  = await fetch(`${LARAVEL_URL}soc/alerts`)
    const data = await res.json()
    mergeAlerts(data.data || data || [])
  } catch (e) {
    // Laravel may not be ready yet — silent fail
  }
}

// 2. Fetch directly from SOC (decisions/history endpoint)
async function fetchFromSOC() {
  try {
    const res  = await fetch(`${SOC_URL}/api/decisions/history?limit=100`)
    const data = await res.json()
    if (data.status === 'ok') {
      mergeAlerts(data.decisions || [])
    }
  } catch (e) {
    // SOC may not be running — silent fail
  }
}

async function fetchAll() {
  loading.value = true
  error.value   = null
  try {
    await Promise.allSettled([fetchFromLaravel(), fetchFromSOC()])
  } finally {
    loading.value = false
  }
}

async function pollSOCLive() {
  // Also check pending decisions from SOC
  try {
    const res  = await fetch(`${SOC_URL}/api/decisions/pending`)
    const data = await res.json()
    if (data.status === 'ok') {
      mergeAlerts(data.decisions || [])
    }
  } catch (e) {}
  // And history for newly resolved ones
  await fetchFromSOC()
}

// ── Computed ──────────────────────────────────────────────────
const filteredAlerts = computed(() => {
  let list = [...alerts.value]

  if (filterSeverity.value !== 'all') {
    list = list.filter(a => (a.severity || '').toLowerCase() === filterSeverity.value)
  }
  if (filterStatus.value !== 'all') {
    list = list.filter(a => (a.status || '').toLowerCase() === filterStatus.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(a =>
      (a.threat_type  || '').toLowerCase().includes(q) ||
      (a.decision     || '').toLowerCase().includes(q) ||
      (a.reasoning    || '').toLowerCase().includes(q) ||
      (a.extra?.machine_name || '').toLowerCase().includes(q) ||
      (a.extra?.sensor_name  || '').toLowerCase().includes(q)
    )
  }

  if (sortBy.value === 'newest') {
    list.sort((a, b) => new Date(b.created || 0) - new Date(a.created || 0))
  } else if (sortBy.value === 'severity') {
    const order = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    list.sort((a, b) => (order[a.severity] ?? 5) - (order[b.severity] ?? 5))
  } else if (sortBy.value === 'confidence') {
    list.sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
  }

  return list
})

// KPIs
const kpiTotal    = computed(() => alerts.value.length)
const kpiCritical = computed(() => alerts.value.filter(a => a.severity === 'critical').length)
const kpiApproved = computed(() => alerts.value.filter(a => a.status === 'approved').length)
const kpiPending  = computed(() => alerts.value.filter(a => a.status === 'pending').length)

const threatBreakdown = computed(() => {
  const map = {}
  alerts.value.forEach(a => {
    const t = a.threat_type || 'Unknown'
    map[t] = (map[t] || 0) + 1
  })
  return Object.entries(map)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([name, count]) => ({ name, count }))
})

const maxThreatCount = computed(() =>
  Math.max(1, ...threatBreakdown.value.map(t => t.count))
)

// ── Helpers ───────────────────────────────────────────────────
function fmtDateTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('en-GB', { hour12: false })
  } catch { return iso }
}

function fmtTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleTimeString('en-GB', { hour12: false })
  } catch { return iso }
}

function shortId(id) {
  return (id || '').slice(0, 8).toUpperCase()
}

function selectAlert(alert) {
  selectedAlert.value = alert
  if (window.innerWidth < 1024) mobileTab.value = 'detail'
}

// ── Lifecycle ─────────────────────────────────────────────────
onMounted(() => {
  fetchAll()
  pollTimer    = setInterval(fetchFromLaravel, POLL_INTERVAL)
  socPollTimer = setInterval(pollSOCLive, POLL_INTERVAL)
})

onUnmounted(() => {
  clearInterval(pollTimer)
  clearInterval(socPollTimer)
})
</script>

<template>
  <div class="relative min-h-[calc(100vh-3.5rem)]">

    <!-- Background -->
    <div class="fixed inset-0 bg-gradient-to-b from-[#0d0d12] to-[#111318] pointer-events-none z-0"></div>

    <div class="relative z-10 max-w-[1440px] mx-auto px-4 md:px-8 py-6 md:py-8">

      <!-- Page Title -->
      <div class="hidden md:flex flex-col mb-6 md:mb-8">
        <div class="flex items-center gap-3 mb-1">
          <div class="w-9 h-9 rounded-xl bg-red-500/15 border border-red-500/30 flex items-center justify-center">
            <span class="material-symbols-outlined text-red-400 text-xl">security</span>
          </div>
          <h1 class="text-2xl md:text-3xl font-headline font-bold text-on-surface tracking-tight">
            SOC Alerts
          </h1>
          <!-- Live indicator -->
          <div class="flex items-center gap-1.5 ml-2 px-2.5 py-1 rounded-full bg-green-500/10 border border-green-500/20">
            <span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-ping absolute"></span>
            <span class="w-1.5 h-1.5 rounded-full bg-green-400 relative"></span>
            <span class="text-green-400 text-[10px] font-bold tracking-wider">LIVE</span>
          </div>
        </div>
        <p class="text-on-surface-variant text-sm">
          Real-time from the Security Operations Center — SCADA threat analysis.
        </p>
      </div>

      <!-- KPI Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6 mb-4 md:mb-8">

        <!-- Total Alerts -->
        <div class="glass-panel bg-white/[0.03] backdrop-blur-xl rounded-xl md:rounded-2xl p-3 md:p-5 border border-white/5 hover:border-primary/30 transition-all">
          <div class="flex items-center gap-2 md:flex-col md:items-start">
            <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg md:rounded-xl bg-primary/15 flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-primary text-lg md:text-xl">notifications</span>
            </div>
            <div class="min-w-0 md:mt-3">
              <p class="text-on-surface-variant text-[10px] md:text-xs font-medium uppercase tracking-wider mb-0.5 md:mb-2">Total Alerts</p>
              <span class="text-2xl md:text-4xl font-headline font-bold text-primary tabular-nums">{{ kpiTotal }}</span>
            </div>
          </div>
        </div>

        <!-- Critical -->
        <div class="glass-panel bg-white/[0.03] backdrop-blur-xl rounded-xl md:rounded-2xl p-3 md:p-5 border border-white/5 hover:border-red-500/30 transition-all">
          <div class="flex items-center gap-2 md:flex-col md:items-start">
            <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg md:rounded-xl bg-red-500/15 flex items-center justify-center shrink-0 relative">
              <span class="material-symbols-outlined text-red-400 text-lg md:text-xl">crisis_alert</span>
              <span v-if="kpiCritical > 0" class="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-red-500 animate-ping"></span>
              <span v-if="kpiCritical > 0" class="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-red-500"></span>
            </div>
            <div class="min-w-0 md:mt-3">
              <p class="text-on-surface-variant text-[10px] md:text-xs font-medium uppercase tracking-wider mb-0.5 md:mb-2">Critical</p>
              <span class="text-2xl md:text-4xl font-headline font-bold text-red-400 tabular-nums">{{ kpiCritical }}</span>
            </div>
          </div>
        </div>

        <!-- Approved -->
        <div class="glass-panel bg-white/[0.03] backdrop-blur-xl rounded-xl md:rounded-2xl p-3 md:p-5 border border-white/5 hover:border-green-500/30 transition-all">
          <div class="flex items-center gap-2 md:flex-col md:items-start">
            <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg md:rounded-xl bg-green-500/15 flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-green-400 text-lg md:text-xl">check_circle</span>
            </div>
            <div class="min-w-0 md:mt-3">
              <p class="text-on-surface-variant text-[10px] md:text-xs font-medium uppercase tracking-wider mb-0.5 md:mb-2">Approved</p>
              <span class="text-2xl md:text-4xl font-headline font-bold text-green-400 tabular-nums">{{ kpiApproved }}</span>
            </div>
          </div>
        </div>

        <!-- Pending -->
        <div class="glass-panel bg-white/[0.03] backdrop-blur-xl rounded-xl md:rounded-2xl p-3 md:p-5 border border-white/5 hover:border-yellow-500/30 transition-all">
          <div class="flex items-center gap-2 md:flex-col md:items-start">
            <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg md:rounded-xl bg-yellow-500/15 flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-yellow-400 text-lg md:text-xl">pending</span>
            </div>
            <div class="min-w-0 md:mt-3">
              <p class="text-on-surface-variant text-[10px] md:text-xs font-medium uppercase tracking-wider mb-0.5 md:mb-2">Pending</p>
              <span class="text-2xl md:text-4xl font-headline font-bold text-yellow-400 tabular-nums">{{ kpiPending }}</span>
            </div>
          </div>
        </div>

      </div>

      <!-- Filter Bar -->
      <div class="glass-panel bg-white/[0.03] rounded-xl mb-4 md:mb-6 p-3 md:p-4 border border-white/5">
        <div class="flex flex-col md:flex-row md:items-center gap-2 md:gap-4">

          <!-- Search -->
          <div class="flex items-center gap-2 flex-1 bg-white/5 px-3 py-2 rounded-lg border border-white/10 hover:border-primary/40 transition-colors">
            <span class="material-symbols-outlined text-sm text-primary">search</span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search threats, machines, sensors..."
              class="bg-transparent text-xs md:text-sm text-on-surface border-none outline-none flex-1 placeholder:text-on-surface-variant/50"
            />
            <button v-if="searchQuery" @click="searchQuery = ''" class="text-on-surface-variant hover:text-error transition-colors">
              <span class="material-symbols-outlined text-sm">close</span>
            </button>
          </div>

          <div class="flex items-center gap-2 flex-wrap">
            <!-- Severity filter -->
            <select v-model="filterSeverity" class="bg-white/5 border border-white/10 text-xs md:text-sm text-on-surface rounded-lg px-3 py-2 outline-none cursor-pointer hover:border-primary/40 transition-colors">
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>

            <!-- Status filter -->
            <select v-model="filterStatus" class="bg-white/5 border border-white/10 text-xs md:text-sm text-on-surface rounded-lg px-3 py-2 outline-none cursor-pointer hover:border-primary/40 transition-colors">
              <option value="all">All Statuses</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="pending">Pending</option>
            </select>

            <!-- Sort -->
            <select v-model="sortBy" class="bg-white/5 border border-white/10 text-xs md:text-sm text-on-surface rounded-lg px-3 py-2 outline-none cursor-pointer hover:border-primary/40 transition-colors">
              <option value="newest">Newest First</option>
              <option value="severity">By Severity</option>
              <option value="confidence">By Confidence</option>
            </select>

            <!-- Refresh -->
            <button @click="fetchAll()" class="flex items-center gap-1.5 bg-primary/10 border border-primary/30 text-primary rounded-lg px-3 py-2 text-xs font-bold hover:bg-primary/20 transition-all">
              <span class="material-symbols-outlined text-sm" :class="loading ? 'animate-spin' : ''">refresh</span>
              <span class="hidden md:inline">Refresh</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Mobile Tab Switcher -->
      <div class="flex lg:hidden mb-4 glass-panel bg-white/[0.03] rounded-xl border border-white/5 p-1">
        <button @click="mobileTab = 'list'" class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition-all"
          :class="mobileTab === 'list' ? 'bg-primary/20 text-primary' : 'text-on-surface-variant'">
          <span class="material-symbols-outlined text-sm">list</span>Alerts
          <span v-if="filteredAlerts.length" class="bg-primary/20 text-primary text-[10px] px-1.5 py-0.5 rounded-full">{{ filteredAlerts.length }}</span>
        </button>
        <button @click="mobileTab = 'detail'" class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition-all"
          :class="mobileTab === 'detail' ? 'bg-primary/20 text-primary' : 'text-on-surface-variant'">
          <span class="material-symbols-outlined text-sm">info</span>Detail
        </button>
        <button @click="mobileTab = 'stats'" class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition-all"
          :class="mobileTab === 'stats' ? 'bg-primary/20 text-primary' : 'text-on-surface-variant'">
          <span class="material-symbols-outlined text-sm">bar_chart</span>Stats
        </button>
      </div>

      <!-- Main Layout -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">

        <!-- ── Alert List ── -->
        <div class="lg:col-span-5" :class="{ 'hidden lg:block': mobileTab !== 'list' }">
          <div class="glass-panel bg-white/[0.03] rounded-2xl border border-white/5 overflow-hidden flex flex-col" style="max-height: calc(100vh - 340px); min-height: 400px;">

            <div class="p-4 border-b border-white/5 flex items-center justify-between flex-shrink-0">
              <h2 class="text-sm font-bold font-headline">
                Alert Feed
                <span class="text-on-surface-variant font-normal ml-1 text-xs">({{ filteredAlerts.length }})</span>
              </h2>
              <div v-if="loading" class="flex items-center gap-1.5 text-xs text-on-surface-variant">
                <span class="material-symbols-outlined text-sm animate-spin text-primary">refresh</span>
                Loading...
              </div>
            </div>

            <!-- Empty state -->
            <div v-if="!loading && filteredAlerts.length === 0" class="flex-1 flex flex-col items-center justify-center p-8 text-on-surface-variant">
              <span class="material-symbols-outlined text-4xl mb-3 text-primary/30">security</span>
              <p class="text-sm font-medium">No alerts yet</p>
              <p class="text-xs mt-1 opacity-60">Waiting for SOC decisions...</p>
            </div>

            <!-- Alert items -->
            <div class="flex-1 overflow-y-auto custom-scrollbar divide-y divide-white/5">
              <div
                v-for="alert in filteredAlerts"
                :key="alert.decision_id"
                class="p-4 cursor-pointer transition-all hover:bg-white/[0.03]"
                :class="selectedAlert?.decision_id === alert.decision_id ? 'bg-primary/5 border-l-2 border-primary' : 'border-l-2 border-transparent'"
                @click="selectAlert(alert)"
              >
                <div class="flex items-start gap-3">

                  <!-- Severity dot -->
                  <div class="mt-1 flex-shrink-0">
                    <span class="w-2.5 h-2.5 rounded-full block" :style="{ background: sevCfg(alert.severity).dot }"></span>
                  </div>

                  <div class="flex-1 min-w-0">
                    <!-- Header row -->
                    <div class="flex items-center gap-2 mb-1 flex-wrap">
                      <span class="text-xs font-bold px-2 py-0.5 rounded-full"
                        :class="[sevCfg(alert.severity).bgClass, sevCfg(alert.severity).textClass]">
                        {{ (alert.severity || 'info').toUpperCase() }}
                      </span>
                      <!-- Status chip -->
                      <span class="text-[10px] font-bold px-2 py-0.5 rounded-full"
                        :class="alert.status === 'approved' ? 'bg-green-500/15 text-green-400' :
                                alert.status === 'rejected' ? 'bg-white/10 text-on-surface-variant' :
                                'bg-yellow-500/15 text-yellow-400'">
                        {{ (alert.status || 'pending').toUpperCase() }}
                      </span>
                      <span class="text-[10px] text-on-surface-variant ml-auto flex-shrink-0">{{ fmtTime(alert.created) }}</span>
                    </div>

                    <!-- Threat type -->
                    <p class="text-sm font-semibold truncate">{{ alert.threat_type || '—' }}</p>

                    <!-- Decision preview -->
                    <p class="text-xs text-on-surface-variant mt-0.5 truncate">{{ alert.decision || '—' }}</p>

                    <!-- Machine info -->
                    <div v-if="alert.extra?.machine_name" class="flex items-center gap-1 mt-1.5">
                      <span class="material-symbols-outlined text-[12px] text-primary/60">precision_manufacturing</span>
                      <span class="text-[10px] text-primary/60">{{ alert.extra.machine_name }}</span>
                      <span v-if="alert.extra?.sensor_name" class="text-[10px] text-on-surface-variant/50">· {{ alert.extra.sensor_name }}</span>
                    </div>
                  </div>

                  <!-- Confidence badge -->
                  <div class="flex-shrink-0 text-center">
                    <span class="text-xs font-bold tabular-nums" :class="sevCfg(alert.severity).textClass">
                      {{ alert.confidence || 0 }}%
                    </span>
                    <p class="text-[9px] text-on-surface-variant/50 mt-0.5">conf.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Right Column: Detail + Stats ── -->
        <div class="lg:col-span-7 flex flex-col gap-4">

          <!-- Detail Panel -->
          <div class="lg:block" :class="{ 'hidden': mobileTab === 'list' || mobileTab === 'stats' }">
            <div class="glass-panel bg-white/[0.03] rounded-2xl border overflow-hidden"
              :class="selectedAlert ? sevCfg(selectedAlert.severity).borderClass : 'border-white/5'">

              <!-- No selection -->
              <div v-if="!selectedAlert" class="flex flex-col items-center justify-center p-12 text-on-surface-variant">
                <span class="material-symbols-outlined text-4xl mb-3 text-primary/30">touch_app</span>
                <p class="text-sm">Select an alert to view details</p>
              </div>

              <!-- Detail content -->
              <div v-else>
                <!-- Header -->
                <div class="p-5 border-b border-white/5 flex items-start gap-4"
                  :class="sevCfg(selectedAlert.severity).bgClass">
                  <div class="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 border"
                    :class="[sevCfg(selectedAlert.severity).bgClass, sevCfg(selectedAlert.severity).borderClass]">
                    <span class="material-symbols-outlined text-2xl" :class="sevCfg(selectedAlert.severity).textClass">smart_toy</span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap mb-1">
                      <span class="text-xs font-bold px-2.5 py-1 rounded-full"
                        :class="[sevCfg(selectedAlert.severity).bgClass, sevCfg(selectedAlert.severity).textClass, sevCfg(selectedAlert.severity).borderClass, 'border']">
                        {{ (selectedAlert.severity || '').toUpperCase() }}
                      </span>
                      <span class="text-[10px] font-mono text-on-surface-variant">DEC-{{ shortId(selectedAlert.decision_id) }}</span>
                    </div>
                    <h3 class="text-base font-bold">{{ selectedAlert.threat_type || '—' }}</h3>
                    <p class="text-xs text-on-surface-variant mt-0.5">{{ fmtDateTime(selectedAlert.created) }}</p>
                  </div>
                  <!-- Status big chip -->
                  <span class="flex-shrink-0 text-xs font-bold px-3 py-1.5 rounded-full border"
                    :class="selectedAlert.status === 'approved'
                      ? 'bg-green-500/15 text-green-400 border-green-500/30'
                      : selectedAlert.status === 'rejected'
                      ? 'bg-white/10 text-on-surface-variant border-white/20'
                      : 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30'">
                    {{ (selectedAlert.status || 'PENDING').toUpperCase() }}
                  </span>
                </div>

                <!-- Body -->
                <div class="p-5 space-y-4">

                  <!-- Confidence bar -->
                  <div>
                    <div class="flex items-center justify-between mb-1.5">
                      <span class="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">AI Confidence</span>
                      <span class="text-sm font-bold tabular-nums" :class="sevCfg(selectedAlert.severity).textClass">
                        {{ selectedAlert.confidence || 0 }}%
                      </span>
                    </div>
                    <div class="h-2 bg-white/8 rounded-full overflow-hidden">
                      <div class="h-full rounded-full transition-all duration-700"
                        :style="{ width: (selectedAlert.confidence || 0) + '%', background: sevCfg(selectedAlert.severity).dot }">
                      </div>
                    </div>
                  </div>

                  <!-- Recommended Decision -->
                  <div>
                    <p class="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">Recommended Decision</p>
                    <div class="bg-primary/5 border border-primary/20 border-l-4 border-l-primary rounded-lg p-3">
                      <p class="text-sm font-semibold text-primary/90">{{ selectedAlert.decision || '—' }}</p>
                    </div>
                  </div>

                  <!-- Reasoning -->
                  <div>
                    <p class="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">Analysis Reasoning</p>
                    <div class="bg-white/3 border border-white/8 rounded-lg p-3">
                      <p class="text-sm text-on-surface-variant leading-relaxed">{{ selectedAlert.reasoning || '—' }}</p>
                    </div>
                  </div>

                  <!-- Sensor Data -->
                  <div v-if="selectedAlert.extra && Object.keys(selectedAlert.extra).length">
                    <p class="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">Sensor Data</p>
                    <div class="grid grid-cols-2 gap-2">
                      <div v-if="selectedAlert.extra.machine_name" class="bg-white/3 border border-white/8 rounded-lg p-3">
                        <p class="text-[10px] text-on-surface-variant mb-1">Machine</p>
                        <p class="text-sm font-semibold">{{ selectedAlert.extra.machine_name }}</p>
                      </div>
                      <div v-if="selectedAlert.extra.sensor_name" class="bg-white/3 border border-white/8 rounded-lg p-3">
                        <p class="text-[10px] text-on-surface-variant mb-1">Sensor</p>
                        <p class="text-sm font-semibold">{{ selectedAlert.extra.sensor_name }}</p>
                      </div>
                      <div v-if="selectedAlert.extra.sensor_type" class="bg-white/3 border border-white/8 rounded-lg p-3">
                        <p class="text-[10px] text-on-surface-variant mb-1">Type</p>
                        <p class="text-sm font-semibold capitalize">{{ selectedAlert.extra.sensor_type }}</p>
                      </div>
                      <div v-if="selectedAlert.extra.value !== undefined" class="bg-white/3 border border-white/8 rounded-lg p-3">
                        <p class="text-[10px] text-on-surface-variant mb-1">Value</p>
                        <p class="text-sm font-bold" :class="sevCfg(selectedAlert.severity).textClass">
                          {{ selectedAlert.extra.value }}
                        </p>
                      </div>
                    </div>
                  </div>

                  <!-- Operator Note -->
                  <div v-if="selectedAlert.operator_note">
                    <p class="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">Operator Note</p>
                    <div class="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-3 flex gap-2">
                      <span class="material-symbols-outlined text-yellow-400 text-sm flex-shrink-0 mt-0.5">sticky_note_2</span>
                      <p class="text-sm text-on-surface-variant">{{ selectedAlert.operator_note }}</p>
                    </div>
                  </div>

                  <!-- Timestamps -->
                  <div class="flex gap-4 text-[10px] text-on-surface-variant/50 font-mono pt-1 border-t border-white/5">
                    <span>Created: {{ fmtDateTime(selectedAlert.created) }}</span>
                    <span v-if="selectedAlert.resolved">Resolved: {{ fmtDateTime(selectedAlert.resolved) }}</span>
                  </div>

                </div>
              </div>
            </div>
          </div>

          <!-- Stats Panel — Threat Breakdown -->
          <div class="lg:block" :class="{ 'hidden': mobileTab === 'list' || mobileTab === 'detail' }">
            <div class="glass-panel bg-white/[0.03] rounded-2xl border border-white/5 p-5">
              <h3 class="text-sm font-bold mb-4 flex items-center gap-2">
                <span class="material-symbols-outlined text-primary text-base">bar_chart</span>
                Threat Breakdown
              </h3>

              <div v-if="threatBreakdown.length === 0" class="text-center py-6 text-on-surface-variant text-xs">
                No data yet
              </div>

              <div v-else class="space-y-3">
                <div v-for="threat in threatBreakdown" :key="threat.name" class="flex items-center gap-3">
                  <span class="text-xs text-on-surface-variant w-32 truncate flex-shrink-0">{{ threat.name }}</span>
                  <div class="flex-1 h-2 bg-white/8 rounded-full overflow-hidden">
                    <div class="h-full bg-primary/70 rounded-full transition-all duration-700"
                      :style="{ width: (threat.count / maxThreatCount * 100) + '%' }">
                    </div>
                  </div>
                  <span class="text-xs font-bold tabular-nums text-primary w-6 text-right flex-shrink-0">{{ threat.count }}</span>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
select option {
  background-color: #111318;
  color: #e8e8f0;
}
.bg-white\/8 { background-color: rgba(255,255,255,0.08); }
.bg-white\/3 { background-color: rgba(255,255,255,0.03); }
.border-white\/8 { border-color: rgba(255,255,255,0.08); }
</style>