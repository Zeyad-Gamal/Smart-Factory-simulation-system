<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as XLSX from 'xlsx'

const today = new Date()
const currentYear = today.getFullYear()
const currentMonth = today.getMonth() + 1

const buttonKeys = ['cumulativeOutput', 'instantaneousRate', 'otherValues', 'ptValues']
const buttonLabels = {
  cumulativeOutput: 'Cumulative Output',
  instantaneousRate: 'Instantaneous Rate',
  otherValues: 'Other Values',
  ptValues: 'PT Values',
}
const activeButton = ref('cumulativeOutput')

const selectedYear = ref(currentYear)
const selectedMonth = ref(currentMonth)
const yearOptions = Array.from({ length: 11 }, (_, i) => currentYear - 5 + i)
const monthOptions = Array.from({ length: 12 }, (_, i) => i + 1)

const isLoading = ref(true)
const searchData = ref([])

const showDetailModal = ref(false)
const clickDate = ref('')
const detailData = ref([])

const showDateRangeModal = ref(false)
const startDate = ref('')
const endDate = ref('')
const formatOption = ref('xlsx')

// ─── Factory Category Definitions ───
const categories = [
  { name: 'Total Output A (units)', base: 58400, range: 100 },
  { name: 'Output Rate A (u/hr)',   base: 320,   range: 30 },
  { name: 'Total Output B (units)', base: 47300, range: 100 },
  { name: 'Motor Speed A (RPM)',    base: 1480,  range: 80 },
  { name: 'Total Output C (units)', base: 62100, range: 100 },
  { name: 'Output Rate B (u/hr)',   base: 280,   range: 25 },
  { name: 'Motor Load (%)',         base: 74,    range: 12 },
  { name: 'Vibration (mm/s)',       base: 3.2,   range: 1.5 },
  { name: 'Hopper Level (m)',       base: 0.85,  range: 0.4 },
  { name: 'Buffer Level (m)',       base: 4.2,   range: 1.0 },
  { name: 'PT1 (bar)', base: 7.0, range: 1.0 },
  { name: 'PT2 (bar)', base: 4.5, range: 1.0 },
  { name: 'PT3 (bar)', base: 7.0, range: 1.0 },
  { name: 'PT4 (bar)', base: 5.5, range: 1.0 },
]

const tableColumns = {
  cumulativeOutput: {
    headers: ['Date', 'Total Output A (units)', 'Total Output B (units)', 'Total Output C (units)'],
    fields: ['outputA', 'outputB', 'outputC'],
  },
  instantaneousRate: {
    headers: ['Date', 'Output Rate A (u/hr)', 'Motor Speed A (RPM)', 'Output Rate B (u/hr)'],
    fields: ['rateA', 'motorSpeedA', 'rateB'],
  },
  otherValues: {
    headers: ['Date', 'Motor Load (%)', 'Vibration (mm/s)', 'Hopper Level (m)', 'Buffer Level (m)'],
    fields: ['motorLoad', 'vibration', 'hopperLevel', 'bufferLevel'],
  },
  ptValues: {
    headers: ['Date', 'PT1 (bar)', 'PT2 (bar)', 'PT3 (bar)', 'PT4 (bar)'],
    fields: ['PT1', 'PT2', 'PT3', 'PT4'],
  },
}

const detailColumns = {
  cumulativeOutput:  ['Time', 'Total Output A', 'Total Output B', 'Total Output C'],
  instantaneousRate: ['Time', 'Output Rate A', 'Motor Speed A', 'Output Rate B'],
  otherValues:       ['Time', 'Motor Load (%)', 'Vibration', 'Hopper Level', 'Buffer Level'],
  ptValues:          ['Time', 'PT1', 'PT2', 'PT3', 'PT4'],
}

const nameFilters = {
  cumulativeOutput:  ['Total Output A (units)', 'Total Output B (units)', 'Total Output C (units)'],
  instantaneousRate: ['Output Rate A (u/hr)', 'Motor Speed A (RPM)', 'Output Rate B (u/hr)'],
  otherValues:       ['Motor Load (%)', 'Vibration (mm/s)', 'Hopper Level (m)', 'Buffer Level (m)'],
  ptValues:          ['PT1 (bar)', 'PT2 (bar)', 'PT3 (bar)', 'PT4 (bar)'],
}

// ─── Demo Data ───
function fetchData() {
  isLoading.value = true
  const year = selectedYear.value
  const month = String(selectedMonth.value).padStart(2, '0')
  const daysInMonth = new Date(year, selectedMonth.value, 0).getDate()
  const demoData = []
  let id = 1
  for (let d = 1; d <= daysInMonth; d++) {
    const date = `${year}-${month}-${String(d).padStart(2, '0')}`
    for (let h = 0; h < 24; h++) {
      const time = `${String(h).padStart(2, '0')}:00`
      for (const cat of categories) {
        const val = cat.base + (Math.random() - 0.5) * cat.range
        demoData.push({ id: String(id++), value: String(parseFloat(val.toFixed(2))), name: cat.name, date, time })
      }
    }
  }
  searchData.value = demoData
  isLoading.value = false
}

// ─── Computed Table Data ───
const organizedData = computed(() => {
  const fields = ['Total Output A (units)', 'Total Output B (units)', 'Total Output C (units)']
  const dates = [...new Set(searchData.value.map(i => i.date))]
  const processed = {}
  dates.forEach(d => { processed[d] = {}; fields.forEach(f => { processed[d][f] = { time: '', value: 0 } }) })
  searchData.value.forEach(entry => {
    if (fields.includes(entry.name)) {
      const cur = processed[entry.date][entry.name]
      if (!cur.time || entry.time > cur.time) processed[entry.date][entry.name] = { time: entry.time, value: entry.value }
    }
  })
  return Object.keys(processed).sort().map(date => ({
    date,
    outputA: Math.round(parseFloat(processed[date]['Total Output A (units)']?.value) || 0),
    outputB: Math.round(parseFloat(processed[date]['Total Output B (units)']?.value) || 0),
    outputC: Math.round(parseFloat(processed[date]['Total Output C (units)']?.value) || 0),
  }))
})

function computeDailyAvg(fieldNames) {
  const result = {}
  const dates = [...new Set(searchData.value.map(i => i.date))]
  dates.forEach(d => { result[d] = {}; fieldNames.forEach(f => { result[d][f] = { total: 0, count: 0 } }) })
  searchData.value.forEach(item => {
    if (fieldNames.includes(item.name)) {
      result[item.date][item.name].total += parseFloat(item.value) || 0
      result[item.date][item.name].count++
    }
  })
  return result
}

const organizedDataInstant = computed(() => {
  const fields = ['Output Rate A (u/hr)', 'Motor Speed A (RPM)', 'Output Rate B (u/hr)']
  const data = computeDailyAvg(fields)
  return Object.entries(data).sort((a, b) => a[0].localeCompare(b[0])).map(([date, v]) => ({
    date,
    rateA: ((v['Output Rate A (u/hr)']?.total || 0) / (v['Output Rate A (u/hr)']?.count || 1)).toFixed(1),
    motorSpeedA: Math.round((v['Motor Speed A (RPM)']?.total || 0) / (v['Motor Speed A (RPM)']?.count || 1)),
    rateB: ((v['Output Rate B (u/hr)']?.total || 0) / (v['Output Rate B (u/hr)']?.count || 1)).toFixed(1),
  }))
})

const organizedDataOthers = computed(() => {
  const fields = ['Motor Load (%)', 'Vibration (mm/s)', 'Hopper Level (m)', 'Buffer Level (m)']
  const data = computeDailyAvg(fields)
  return Object.entries(data).sort((a, b) => a[0].localeCompare(b[0])).map(([date, v]) => ({
    date,
    motorLoad: ((v['Motor Load (%)']?.total || 0) / (v['Motor Load (%)']?.count || 1)).toFixed(1),
    vibration: ((v['Vibration (mm/s)']?.total || 0) / (v['Vibration (mm/s)']?.count || 1)).toFixed(2),
    hopperLevel: ((v['Hopper Level (m)']?.total || 0) / (v['Hopper Level (m)']?.count || 1)).toFixed(2),
    bufferLevel: ((v['Buffer Level (m)']?.total || 0) / (v['Buffer Level (m)']?.count || 1)).toFixed(2),
  }))
})

const organizedDataPressure = computed(() => {
  const fields = ['PT1 (bar)', 'PT2 (bar)', 'PT3 (bar)', 'PT4 (bar)']
  const data = computeDailyAvg(fields)
  return Object.entries(data).sort((a, b) => a[0].localeCompare(b[0])).map(([date, v]) => ({
    date,
    PT1: ((v['PT1 (bar)']?.total || 0) / (v['PT1 (bar)']?.count || 1)).toFixed(1),
    PT2: ((v['PT2 (bar)']?.total || 0) / (v['PT2 (bar)']?.count || 1)).toFixed(1),
    PT3: ((v['PT3 (bar)']?.total || 0) / (v['PT3 (bar)']?.count || 1)).toFixed(1),
    PT4: ((v['PT4 (bar)']?.total || 0) / (v['PT4 (bar)']?.count || 1)).toFixed(1),
  }))
})

const activeTableData = computed(() => ({
  cumulativeOutput: organizedData.value,
  instantaneousRate: organizedDataInstant.value,
  otherValues: organizedDataOthers.value,
  ptValues: organizedDataPressure.value,
}[activeButton.value] || []))

const activeHeaders = computed(() => tableColumns[activeButton.value]?.headers || [])
const activeFields = computed(() => tableColumns[activeButton.value]?.fields || [])
const activeDetailHeaders = computed(() => detailColumns[activeButton.value] || [])
const activeDetailFields = computed(() => tableColumns[activeButton.value]?.fields || [])
const activeColSpan = computed(() => activeHeaders.value.length)

function setActive(btn) { activeButton.value = btn }

function onRowClick(date) {
  clickDate.value = date
  const filter = nameFilters[activeButton.value]
  const filtered = searchData.value.filter(item => item.date === date && filter.includes(item.name))
  const timeMap = {}
  filtered.forEach(item => {
    if (!timeMap[item.time]) timeMap[item.time] = {}
    const val = parseFloat(item.value) || 0
    if (activeButton.value === 'cumulativeOutput') {
      if (item.name === 'Total Output A (units)') timeMap[item.time].outputA = Math.round(val)
      else if (item.name === 'Total Output B (units)') timeMap[item.time].outputB = Math.round(val)
      else if (item.name === 'Total Output C (units)') timeMap[item.time].outputC = Math.round(val)
    } else if (activeButton.value === 'instantaneousRate') {
      if (item.name === 'Output Rate A (u/hr)') timeMap[item.time].rateA = val.toFixed(1)
      else if (item.name === 'Motor Speed A (RPM)') timeMap[item.time].motorSpeedA = Math.round(val)
      else if (item.name === 'Output Rate B (u/hr)') timeMap[item.time].rateB = val.toFixed(1)
    } else if (activeButton.value === 'otherValues') {
      if (item.name === 'Motor Load (%)') timeMap[item.time].motorLoad = val.toFixed(1)
      else if (item.name === 'Vibration (mm/s)') timeMap[item.time].vibration = val.toFixed(2)
      else if (item.name === 'Hopper Level (m)') timeMap[item.time].hopperLevel = val.toFixed(2)
      else if (item.name === 'Buffer Level (m)') timeMap[item.time].bufferLevel = val.toFixed(2)
    } else if (activeButton.value === 'ptValues') {
      if (item.name === 'PT1 (bar)') timeMap[item.time].PT1 = val.toFixed(1)
      else if (item.name === 'PT2 (bar)') timeMap[item.time].PT2 = val.toFixed(1)
      else if (item.name === 'PT3 (bar)') timeMap[item.time].PT3 = val.toFixed(1)
      else if (item.name === 'PT4 (bar)') timeMap[item.time].PT4 = val.toFixed(1)
    }
  })
  detailData.value = Object.keys(timeMap).sort().map(time => ({ time, ...timeMap[time] }))
  showDetailModal.value = true
}

function openDateRangeModal() {
  startDate.value = `${selectedYear.value}-${String(selectedMonth.value).padStart(2,'0')}-01`
  const lastDay = new Date(selectedYear.value, selectedMonth.value, 0).getDate()
  endDate.value = `${selectedYear.value}-${String(selectedMonth.value).padStart(2,'0')}-${String(lastDay).padStart(2,'0')}`
  showDateRangeModal.value = true
}

function generateReport() {
  if (!startDate.value || !endDate.value) { alert('Please select start and end dates'); return }
  if (new Date(startDate.value) > new Date(endDate.value)) { alert('Start date cannot be after end date'); return }
  showDateRangeModal.value = false
  try {
    const workbook = XLSX.utils.book_new()
    if (formatOption.value === 'xlsx') {
      const catDefs = {
        'Cumulative Output': ['Total Output A (units)', 'Total Output B (units)', 'Total Output C (units)'],
        'Instantaneous Rate': ['Output Rate A (u/hr)', 'Motor Speed A (RPM)', 'Output Rate B (u/hr)'],
        'Other Values': ['Motor Load (%)', 'Vibration (mm/s)', 'Hopper Level (m)', 'Buffer Level (m)'],
        'PT Values': ['PT1 (bar)', 'PT2 (bar)', 'PT3 (bar)', 'PT4 (bar)'],
      }
      Object.entries(catDefs).forEach(([category, fields]) => {
        const filtered = searchData.value.filter(item => fields.includes(item.name) && item.date >= startDate.value && item.date <= endDate.value)
        const grouped = {}
        filtered.forEach(item => {
          const key = `${item.date}_${item.time}`
          if (!grouped[key]) grouped[key] = { date: item.date, time: item.time }
          grouped[key][item.name] = parseFloat(item.value).toFixed(2)
        })
        const rows = [['Date', 'Time', ...fields]]
        Object.values(grouped).sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time)).forEach(row => {
          rows.push([row.date, row.time, ...fields.map(f => row[f] || 0)])
        })
        XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(rows), category)
      })
      XLSX.writeFile(workbook, `Factory_Report_MultiSheet_${startDate.value}_${endDate.value}.xlsx`)
    } else {
      const allFields = categories.map(c => c.name)
      const filtered = searchData.value.filter(item => allFields.includes(item.name) && item.date >= startDate.value && item.date <= endDate.value)
      const grouped = {}
      filtered.forEach(item => {
        const key = `${item.date}_${item.time}`
        if (!grouped[key]) grouped[key] = { date: item.date, time: item.time }
        grouped[key][item.name] = parseFloat(item.value).toFixed(2)
      })
      const rows = [['Date', 'Time', ...allFields]]
      Object.values(grouped).sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time)).forEach(row => {
        rows.push([row.date, row.time, ...allFields.map(f => row[f] || 0)])
      })
      XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(rows), 'Factory Data')
      XLSX.writeFile(workbook, `Factory_Report_Single_${startDate.value}_${endDate.value}.xlsx`)
    }
    alert('Report generated and downloaded successfully.')
  } catch (err) {
    console.error('Export error:', err)
    alert('[DEMO] Report export simulated.')
  }
}

watch([selectedYear, selectedMonth], fetchData)

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
        {{ selectedYear }}/{{ String(selectedMonth).padStart(2,'0') }} Monthly Report
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

    <!-- Year/Month + Export Row -->
    <div class="flex items-center justify-between gap-2 mb-6 px-2">
      <div class="flex items-center gap-0 bg-white/[0.03] border border-white/[0.06] rounded-xl py-2 sm:py-2.5 px-1 backdrop-blur-xl min-w-0">
        <div class="flex items-center px-2 sm:px-3.5">
          <span class="material-symbols-outlined text-primary text-lg sm:text-xl">calendar_today</span>
        </div>
        <select v-model="selectedYear" class="bg-transparent border-none text-on-surface text-sm sm:text-base font-semibold cursor-pointer outline-none px-1 py-0.5 font-label">
          <option v-for="year in yearOptions" :key="year" :value="year" class="bg-surface-container-high text-on-surface">{{ year }}</option>
        </select>
        <span class="text-white/30 text-xs sm:text-[15px] mx-0.5 sm:mx-1">Year</span>
        <select v-model="selectedMonth" class="bg-transparent border-none text-on-surface text-sm sm:text-base font-semibold cursor-pointer outline-none px-1 py-0.5 font-label">
          <option v-for="month in monthOptions" :key="month" :value="month" class="bg-surface-container-high text-on-surface">{{ month }}</option>
        </select>
        <span class="text-white/30 text-xs sm:text-[15px] mr-2 sm:mr-3.5">Month</span>
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
                <div class="text-xs opacity-60">No records found for this time period</div>
              </td>
            </tr>
            <tr
              v-for="row in activeTableData" :key="row.date"
              @click="onRowClick(row.date)"
              class="cursor-pointer border-b border-white/[0.04] transition-colors duration-200 hover:bg-primary/[0.04]"
            >
              <td class="px-3 sm:px-7 py-2.5 sm:py-3.5 font-medium text-on-surface whitespace-nowrap text-xs sm:text-sm">{{ row.date }}</td>
              <td v-for="field in activeFields" :key="field" class="px-3 sm:px-7 py-2.5 sm:py-3.5 font-medium text-xs sm:text-[15px] text-on-surface/80 whitespace-nowrap">{{ row[field] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Detail Modal -->
    <div v-show="showDetailModal" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
      <div class="fixed inset-0 bg-black/60 backdrop-blur-sm" @click="showDetailModal = false"></div>
      <div class="relative z-10 w-full max-w-3xl bg-surface-container-high border border-white/10 rounded-2xl shadow-2xl max-h-[85vh] flex flex-col">
        <div class="flex items-center justify-between p-6 border-b border-white/10">
          <h5 class="text-lg font-bold text-primary flex items-center gap-2 m-0">
            <span class="material-symbols-outlined">calendar_today</span>
            {{ clickDate }} — Daily Detail
          </h5>
          <button class="text-white/60 hover:text-primary transition-colors bg-transparent border-none cursor-pointer" @click="showDetailModal = false">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-6">
          <div class="rounded-lg overflow-y-auto max-h-[50vh] relative">
            <table class="w-full border-collapse table-fixed">
              <thead>
                <tr>
                  <th v-for="h in activeDetailHeaders" :key="h" class="sticky top-0 z-10 px-4 py-3 text-center text-white font-semibold border-b-2 border-primary/40" style="background-color: #1a1a22;">{{ h }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="detailData.length === 0">
                  <td :colspan="activeDetailHeaders.length" class="text-center py-8 text-on-surface-variant">
                    <span class="material-symbols-outlined text-3xl block mb-2 opacity-40">schedule</span>
                    <div class="font-semibold">No hourly data for this date</div>
                  </td>
                </tr>
                <tr v-else v-for="(item, idx) in detailData" :key="item.time" class="transition-colors hover:bg-primary/10" :class="idx % 2 === 0 ? 'bg-black/15' : 'bg-black/5'">
                  <td class="px-4 py-2.5 text-center font-medium bg-black/20 text-primary/80">{{ item.time }}</td>
                  <td v-for="field in activeDetailFields" :key="field" class="px-4 py-2.5 text-center text-on-surface/80">{{ item[field] || '0' }}</td>
                </tr>
              </tbody>
            </table>
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
