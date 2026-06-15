<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as XLSX from 'xlsx'

// ─── Config ───
const API_BASE = '/api/scada/history'

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const buttonKeys = ['cumulativeOutput', 'instantaneousRate', 'otherValues', 'ptValues']
const buttonLabels = {
  cumulativeOutput: 'Cumulative Output',
  instantaneousRate: 'Instantaneous Rate',
  otherValues: 'Other Values',
  ptValues: 'PT Values',
}
const activeButton = ref('cumulativeOutput')

const selectedDate = ref(todayStr())

const isLoading = ref(true)
const errorMessage = ref('')
const searchData = ref([]) // [{ name, time, value }]

const showDetailModal = ref(false)
const clickDate = ref('')
const detailData = ref([])

const showDateRangeModal = ref(false)
const startDate = ref('')
const endDate = ref('')
const formatOption = ref('xlsx')

// ─── Table column definitions ───
const tableColumns = {
  cumulativeOutput: {
    headers: ['Time', 'Total Output A (units)', 'Total Output B (units)', 'Total Output C (units)'],
    fields: ['outputA', 'outputB', 'outputC'],
  },
  instantaneousRate: {
    headers: ['Time', 'Output Rate A (u/hr)', 'Motor Speed A (RPM)', 'Motor Speed B (RPM)'],
    fields: ['rateA', 'motorSpeedA', 'motorSpeedB'],
  },
  otherValues: {
    headers: ['Time', 'Motor Load (%)', 'Vibration (mm/s)', 'Hopper Level (m)', 'Buffer Level (m)'],
    fields: ['motorLoad', 'vibration', 'hopperLevel', 'bufferLevel'],
  },
  ptValues: {
    headers: ['Time', 'PT1 (bar)', 'PT2 (bar)', 'PT3 (bar)', 'PT4 (bar)'],
    fields: ['PT1', 'PT2', 'PT3', 'PT4'],
  },
}

// ─── Maps each field to { type, index } — Nth occurrence of that `name`/type within a timestamp ───
// Based on observed order for "05:56": rpm, rate, total, total, total, level, level,
// pressure, rpm, load, vibration, pressure, pressure, pressure
const fieldToOccurrence = {
  cumulativeOutput: {
    outputA: { type: 'total', index: 0 },
    outputB: { type: 'total', index: 1 },
    outputC: { type: 'total', index: 2 },
  },
  instantaneousRate: {
    rateA:       { type: 'rate', index: 0 },
    motorSpeedA: { type: 'rpm',  index: 0 },
    motorSpeedB: { type: 'rpm',  index: 1 },
  },
  otherValues: {
    motorLoad:   { type: 'load',      index: 0 },
    vibration:   { type: 'vibration', index: 0 },
    hopperLevel: { type: 'level',     index: 0 },
    bufferLevel: { type: 'level',     index: 1 },
  },
  ptValues: {
    PT1: { type: 'pressure', index: 0 },
    PT2: { type: 'pressure', index: 1 },
    PT3: { type: 'pressure', index: 2 },
    PT4: { type: 'pressure', index: 3 },
  },
}

// Decimal places used when displaying each field
const fieldDecimals = {
  outputA: 0, outputB: 0, outputC: 0,
  rateA: 1, motorSpeedA: 0, motorSpeedB: 0,
  motorLoad: 1, vibration: 2, hopperLevel: 2, bufferLevel: 2,
  PT1: 1, PT2: 1, PT3: 1, PT4: 1,
}

function fmt(value, decimals) {
  if (value === undefined || value === null || Number.isNaN(value)) return '0'
  return decimals === 0 ? String(Math.round(value)) : value.toFixed(decimals)
}

// ─── Group raw items by time, preserving original order, then extract by occurrence index ───
function buildRowsFromItems(items) {
  const byTime = {}
  items.forEach(item => {
    if (!byTime[item.time]) byTime[item.time] = []
    byTime[item.time].push(item)
  })

  const rows = {}
  for (const [time, timeItems] of Object.entries(byTime)) {
    rows[time] = { time }
    // For each (key) -> list of matching items of that type, in order
    const seenByType = {}
    timeItems.forEach(it => {
      if (!seenByType[it.name]) seenByType[it.name] = []
      seenByType[it.name].push(it)
    })
    rows[time].__byType = seenByType
  }
  return rows
}

function extractField(rowByType, type, index) {
  const arr = rowByType?.[type]
  if (!arr || arr[index] === undefined) return undefined
  return parseFloat(arr[index].value)
}

// ─── Fetch data for the selected date ───
async function fetchData() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const res = await fetch(`${API_BASE}?date=${selectedDate.value}`)
    if (!res.ok) throw new Error(`Request failed (${res.status})`)
    const json = await res.json()
    searchData.value = Array.isArray(json) ? json : (json.data || [])
  } catch (err) {
    console.error('Fetch error:', err)
    errorMessage.value = 'Could not load data for this date.'
    searchData.value = []
  } finally {
    isLoading.value = false
  }
}

// ─── Build the active table: one row per Time, columns = mapped sensors ───
const activeTableData = computed(() => {
  const cols = tableColumns[activeButton.value]
  const mapping = fieldToOccurrence[activeButton.value]
  if (!cols || !mapping) return []

  const rows = buildRowsFromItems(searchData.value)

  return Object.entries(rows)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([time, row]) => {
      const out = { time }
      for (const field of cols.fields) {
        const { type, index } = mapping[field]
        const val = extractField(row.__byType, type, index)
        out[field] = fmt(val, fieldDecimals[field] ?? 2)
      }
      return out
    })
})

const activeHeaders = computed(() => tableColumns[activeButton.value]?.headers || [])
const activeFields = computed(() => tableColumns[activeButton.value]?.fields || [])
const activeColSpan = computed(() => activeHeaders.value.length)

function setActive(btn) { activeButton.value = btn }

function onRowClick(row) {
  clickDate.value = `${selectedDate.value} ${row.time}`
  detailData.value = [row]
  showDetailModal.value = true
}

// ─── Excel export modal ───
function openDateRangeModal() {
  startDate.value = selectedDate.value
  endDate.value = selectedDate.value
  showDateRangeModal.value = true
}

async function fetchRange(start, end) {
  const dates = []
  const cur = new Date(start)
  const last = new Date(end)
  while (cur <= last) {
    dates.push(`${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, '0')}-${String(cur.getDate()).padStart(2, '0')}`)
    cur.setDate(cur.getDate() + 1)
  }

  const results = await Promise.all(dates.map(async (date) => {
    try {
      const res = await fetch(`${API_BASE}?date=${date}`)
      if (!res.ok) return []
      const json = await res.json()
      const items = Array.isArray(json) ? json : (json.data || [])
      return items.map(item => ({ ...item, date }))
    } catch {
      return []
    }
  }))

  return results.flat()
}

async function generateReport() {
  if (!startDate.value || !endDate.value) { alert('Please select start and end dates'); return }
  if (new Date(startDate.value) > new Date(endDate.value)) { alert('Start date cannot be after end date'); return }

  showDateRangeModal.value = false
  isLoading.value = true
  try {
    const rangeData = await fetchRange(startDate.value, endDate.value)
    if (rangeData.length === 0) {
      alert('No data found for the selected date range.')
      return
    }

    // Group by date+time, preserving order per group
    const byDateTime = {}
    rangeData.forEach(item => {
      const key = `${item.date}_${item.time}`
      if (!byDateTime[key]) byDateTime[key] = { date: item.date, time: item.time, items: [] }
      byDateTime[key].items.push(item)
    })

    // Pre-index occurrences per group
    const indexed = Object.values(byDateTime).map(group => {
      const seenByType = {}
      group.items.forEach(it => {
        if (!seenByType[it.name]) seenByType[it.name] = []
        seenByType[it.name].push(it)
      })
      return { date: group.date, time: group.time, byType: seenByType }
    }).sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time))

    const workbook = XLSX.utils.book_new()

    if (formatOption.value === 'xlsx') {
      Object.entries(tableColumns).forEach(([key, cols]) => {
        const mapping = fieldToOccurrence[key]
        const rows = [['Date', 'Time', ...cols.headers.slice(1)]]
        indexed.forEach(group => {
          const rowVals = cols.fields.map(field => {
            const { type, index } = mapping[field]
            const val = extractField(group.byType, type, index)
            return val !== undefined ? val.toFixed(2) : 0
          })
          rows.push([group.date, group.time, ...rowVals])
        })
        XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(rows), buttonLabels[key])
      })
      XLSX.writeFile(workbook, `Factory_Report_MultiSheet_${startDate.value}_${endDate.value}.xlsx`)
    } else {
      const allHeaders = []
      const allFieldDefs = [] // { key, field }
      Object.entries(tableColumns).forEach(([key, cols]) => {
        cols.fields.forEach((field, idx) => {
          allHeaders.push(cols.headers[idx + 1])
          allFieldDefs.push({ key, field })
        })
      })

      const rows = [['Date', 'Time', ...allHeaders]]
      indexed.forEach(group => {
        const rowVals = allFieldDefs.map(({ key, field }) => {
          const { type, index } = fieldToOccurrence[key][field]
          const val = extractField(group.byType, type, index)
          return val !== undefined ? val.toFixed(2) : 0
        })
        rows.push([group.date, group.time, ...rowVals])
      })

      XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(rows), 'Factory Data')
      XLSX.writeFile(workbook, `Factory_Report_Single_${startDate.value}_${endDate.value}.xlsx`)
    }

    alert('Report generated and downloaded successfully.')
  } catch (err) {
    console.error('Export error:', err)
    alert('Report export failed. Please try again.')
  } finally {
    isLoading.value = false
  }
}

watch(selectedDate, fetchData)

let refreshTimer = null
onMounted(() => { fetchData(); refreshTimer = setInterval(fetchData, 60000) })
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })
</script>

<template>
  <!-- Background -->
  <div class="fixed inset-0 -z-10">
    <div class="absolute inset-0 bg-gradient-to-b from-[#0d0d12] to-[#111318]"></div>
    <div class="absolute inset-0 opacity-20" style="background-image: radial-gradient(circle at 50% -20%, rgba(244,162,91,0.12) 0%, transparent 60%)"></div>
  </div>

  <div class="max-w-[1400px] mx-auto px-4 md:px-6 pt-4 pb-8">
    <!-- Title -->
    <div class="hidden md:block text-center my-6">
      <h1 class="text-3xl lg:text-4xl font-bold text-on-surface font-headline">
        {{ selectedDate }} Daily Report
      </h1>
      <h2 class="text-lg text-on-surface-variant font-medium mt-1">{{ buttonLabels[activeButton] }}</h2>
    </div>

    <!-- Category Buttons -->
    <div class="flex items-center gap-2 sm:gap-2.5 mb-4 px-4 overflow-x-auto scrollbar-hide">
      <button
        v-for="key in buttonKeys" :key="key"
        @click="setActive(key)"
        class="shrink-0 px-4 sm:px-6 py-2 sm:py-2.5 rounded-[10px] text-[13px] sm:text-[15px] font-label transition-all duration-200 backdrop-blur-lg whitespace-nowrap"
        :class="activeButton === key
          ? 'bg-primary/15 border border-primary/40 text-primary font-bold shadow-[0_0_12px_rgba(244,162,91,0.15)]'
          : 'bg-white/[0.03] border border-white/[0.08] text-white/60 font-medium hover:border-white/20 hover:text-white/80'"
      >{{ buttonLabels[key] }}</button>
    </div>

    <!-- Date Picker + Export Row -->
    <div class="flex items-center justify-between gap-2 mb-6 px-2">
      <div class="flex items-center gap-2 bg-white/[0.03] border border-white/[0.06] rounded-xl py-2 sm:py-2.5 px-3 sm:px-4 backdrop-blur-xl min-w-0">
        <span class="material-symbols-outlined text-primary text-lg sm:text-xl">calendar_today</span>
        <input
          type="date"
          v-model="selectedDate"
          class="bg-transparent border-none text-on-surface text-sm sm:text-base font-semibold cursor-pointer outline-none px-1 py-0.5 font-label"
        />
      </div>

      <button
        @click="openDateRangeModal()"
        class="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-6 py-2.5 sm:py-3 rounded-xl border-none cursor-pointer font-bold text-xs sm:text-[15px] shrink-0 transition-transform duration-200 hover:scale-[1.02]"
        style="background: linear-gradient(135deg, #f4a25b, #c97a30); color: #1a0800; box-shadow: 0 0 15px rgba(244,162,91,0.25);"
      >
        <span class="material-symbols-outlined text-lg sm:text-xl">file_download</span>
        <span class="hidden sm:inline">Excel Export</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex justify-center py-16">
      <div class="w-10 h-10 border-[3px] border-primary/20 border-t-primary rounded-full animate-spin"></div>
    </div>

    <!-- Error -->
    <div v-else-if="errorMessage" class="text-center py-16 text-white/60">
      <span class="material-symbols-outlined text-5xl block mb-3 opacity-30">error</span>
      <div class="text-base font-semibold mb-1">{{ errorMessage }}</div>
      <div class="text-xs opacity-60">Check the API connection and try again.</div>
    </div>

    <!-- Table -->
    <section v-else class="mx-0 sm:mx-2 rounded-2xl overflow-hidden relative backdrop-blur-2xl border border-white/5" style="background: rgba(255,255,255,0.02); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);">
      <div class="absolute top-0 left-0 w-full h-0.5" style="background: linear-gradient(to right, transparent, rgba(244,162,91,0.4), transparent)"></div>
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse font-label">
          <thead class="bg-white/[0.03]">
            <tr>
              <th v-for="header in activeHeaders" :key="header" class="px-3 sm:px-7 py-3 sm:py-4 text-[10px] sm:text-[11px] font-bold text-primary tracking-wider uppercase whitespace-nowrap">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="activeTableData.length === 0">
              <td :colspan="activeColSpan" class="text-center py-16 text-white/40">
                <span class="material-symbols-outlined text-5xl block mb-3 opacity-30">database</span>
                <div class="text-base font-semibold mb-1">No data available</div>
                <div class="text-xs opacity-60">No records found for this date</div>
              </td>
            </tr>
            <tr
              v-for="row in activeTableData" :key="row.time"
              @click="onRowClick(row)"
              class="cursor-pointer border-b border-white/[0.04] transition-colors duration-200 hover:bg-primary/[0.04]"
            >
              <td class="px-3 sm:px-7 py-2.5 sm:py-3.5 font-medium text-on-surface whitespace-nowrap text-xs sm:text-sm">{{ row.time }}</td>
              <td v-for="field in activeFields" :key="field" class="px-3 sm:px-7 py-2.5 sm:py-3.5 font-medium text-xs sm:text-[15px] text-on-surface/80 whitespace-nowrap">{{ row[field] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Detail Modal -->
    <div v-show="showDetailModal" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
      <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="showDetailModal = false"></div>
      <div class="relative z-10 w-full max-w-lg bg-surface-container-high border border-white/10 rounded-2xl shadow-2xl max-h-[85vh] flex flex-col">
        <div class="flex items-center justify-between p-6 border-b border-white/10">
          <h5 class="text-lg font-bold text-primary flex items-center gap-2 m-0">
            <span class="material-symbols-outlined">schedule</span>
            {{ clickDate }}
          </h5>
          <button class="text-white/60 hover:text-primary transition-colors bg-transparent border-none cursor-pointer" @click="showDetailModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-6 space-y-3">
          <div v-for="field in activeFields" :key="field" class="flex items-center justify-between px-4 py-3 rounded-lg bg-black/15">
            <span class="text-sm text-white/60">{{ tableColumns[activeButton].headers[activeFields.indexOf(field) + 1] }}</span>
            <span class="text-sm font-semibold text-primary/90">{{ detailData[0]?.[field] ?? '0' }}</span>
          </div>
        </div>
        <div class="p-4 border-t border-white/10 flex justify-end">
          <button class="px-5 py-2 rounded-lg bg-white/5 text-white/70 hover:bg-white/10 transition-colors text-sm border border-white/10 cursor-pointer" @click="showDetailModal = false">Close</button>
        </div>
      </div>
    </div>

    <!-- Excel Export Modal -->
    <div v-show="showDateRangeModal" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
      <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="showDateRangeModal = false"></div>
      <div class="relative z-10 w-full max-w-md bg-surface-container-high border border-white/10 rounded-2xl shadow-2xl">
        <div class="flex items-center justify-between p-6 border-b border-white/10">
          <h5 class="text-lg font-bold text-primary flex items-center gap-2 m-0">
            <span class="material-symbols-outlined">date_range</span>
            Select Report Date Range
          </h5>
          <button class="text-white/60 hover:text-primary transition-colors bg-transparent border-none cursor-pointer" @click="showDateRangeModal = false"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="p-6 space-y-5">
          <div>
            <label class="block text-sm text-white/60 mb-2">Start Date</label>
            <input type="date" v-model="startDate" class="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white text-sm outline-none focus:border-primary/40 transition-colors" />
          </div>
          <div>
            <label class="block text-sm text-white/60 mb-2">End Date</label>
            <input type="date" v-model="endDate" class="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white text-sm outline-none focus:border-primary/40 transition-colors" />
          </div>
          <div>
            <h4 class="text-sm font-bold text-white/80 mb-3">Report Format</h4>
            <div class="space-y-2">
              <div class="flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all" :class="formatOption === 'xlsx' ? 'bg-primary/10 border-primary/30' : 'bg-white/[0.03] border-white/10 hover:border-white/20'" @click="formatOption = 'xlsx'">
                <input type="radio" name="format" value="xlsx" v-model="formatOption" class="accent-primary" />
                <span class="material-symbols-outlined text-primary">table_view</span>
                <div><div class="text-sm font-medium text-white">Multi-sheet Excel</div><div class="text-xs text-white/50">Each category on separate worksheets</div></div>
              </div>
              <div class="flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all" :class="formatOption === 'csv' ? 'bg-primary/10 border-primary/30' : 'bg-white/[0.03] border-white/10 hover:border-white/20'" @click="formatOption = 'csv'">
                <input type="radio" name="format" value="csv" v-model="formatOption" class="accent-primary" />
                <span class="material-symbols-outlined text-primary">grid_on</span>
                <div><div class="text-sm font-medium text-white">Single-sheet Excel</div><div class="text-xs text-white/50">All data merged into one worksheet</div></div>
              </div>
            </div>
          </div>
        </div>
        <div class="p-4 border-t border-white/10 flex justify-end gap-3">
          <button class="px-5 py-2.5 rounded-lg bg-white/5 text-white/70 hover:bg-white/10 transition-colors text-sm border border-white/10 cursor-pointer" @click="showDateRangeModal = false">Cancel</button>
          <button class="px-5 py-2.5 rounded-lg text-sm font-bold transition-all border-none cursor-pointer" style="background: linear-gradient(135deg, #f4a25b, #c97a30); color: #1a0800;" @click="generateReport">Generate Report</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
table tbody tr { transition: background-color 0.2s ease; }
input[type="date"] { color-scheme: dark; }
</style>
