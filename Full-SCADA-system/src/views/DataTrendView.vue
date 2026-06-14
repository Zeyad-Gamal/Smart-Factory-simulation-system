<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'

// API config



// ===== Category definitions =====
const categoryKeys = [
  'cumulativeOutput',
  'instantaneousRate',
  'motorLoad',
  'vibration',
  'temperature',
  'machineLoad',
  'ptValues',
]

const categoryLabels = {
  cumulativeOutput: 'Cumulative Output',
  instantaneousRate: 'Instantaneous Rate',
  motorLoad: 'Motor Load',
  vibration: 'Vibration',
  temperature: 'Temperature',
  machineLoad: 'Machine Load',
  ptValues: 'PT Values',
}

// ===== State =====
const activeCategoryKey = ref('cumulativeOutput')
const selectedDate = ref(getToday())
const maxDate = ref(getToday())
const loading = ref(false)
const chartData = ref([])
const expandedStat = ref(null)
const isHoveringChart = ref(false)
const chartRef = ref(null)

const chartStats = reactive({ max: 0, min: 0, avg: 0, changeRate: 0 })
const demoBaseValues = ref({})
let updateTimerId = null

// ===== Computed =====
const activeCategory = computed(() => categoryLabels[activeCategoryKey.value])
const seriesColors = ['#f4a25b', '#5de6ff', '#67ccff', '#ff716c', '#4ad8f0', '#c5dbff']

const indicatorColor = computed(() => ({
  cumulativeOutput: '#f4a25b',
  instantaneousRate: '#5de6ff',
  motorLoad: '#67ccff',
  vibration: '#ff716c',
  temperature: '#4ad8f0',
  machineLoad: '#c5dbff',
  ptValues: '#ff716c',
}[activeCategoryKey.value] || '#f4a25b'))

// ===== Helper =====
function getToday() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`
}

function getUniqueNames() {
  const names = []
  const seen = new Set()
  chartData.value.forEach(item => {
    if (item.name && !seen.has(item.name)) { seen.add(item.name); names.push(item.name) }
  })
  return names
}
function getUniqueNameCount() { return getUniqueNames().length }
function formatValue(value) {
  if (value === undefined || value === null) return '–'
  if (typeof value === 'number') return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return value
}

// ===== DEMO data config (factory machines) =====
const FORCE_DEMO = false

const categoryConfig = {
  'Cumulative Output': [
    { name: 'Total Output A', base: 58400, range: 50 },
    { name: 'Total Output B', base: 47300, range: 40 },
    { name: 'Total Output C', base: 62100, range: 60 },
  ],
  'Instantaneous Rate': [
    { name: 'Output Rate A (u/hr)', base: 320, range: 30 },
    { name: 'Output Rate B (u/hr)', base: 280, range: 25 },
    { name: 'Output Rate C (u/hr)', base: 410, range: 40 },
  ],
  'Motor Load': [
    { name: 'Motor Load (%)', base: 74, range: 12 },
  ],
  'Vibration': [
    { name: 'Vibration (mm/s)', base: 3.2, range: 1.5 },
  ],
  'Temperature': [
    { name: 'Spindle Temp (°C)', base: 68, range: 8 },
    { name: 'Ambient Temp (°C)', base: 26, range: 3 },
  ],
  'Machine Load': [
    { name: 'Hopper Level (m)', base: 0.85, range: 0.4 },
    { name: 'Buffer Level (m)', base: 4.2, range: 1.0 },
  ],
  'PT Values': [
    { name: 'PT1 (bar)', base: 7.0, range: 1.0 },
    { name: 'PT2 (bar)', base: 4.5, range: 0.8 },
    { name: 'PT3 (bar)', base: 7.0, range: 0.5 },
    { name: 'PT4 (bar)', base: 5.5, range: 1.0 },
  ],
}

function generateDemoData() {
  const category = activeCategory.value
  const now = new Date()
  const data = []
  const lines = categoryConfig[category] || []

  lines.forEach(line => {
    const key = `${category}_${line.name}`
    if (!demoBaseValues.value[key]) demoBaseValues.value[key] = line.base
    demoBaseValues.value[key] += (Math.random() - 0.5) * line.range * 0.05
  })

  for (let i = 24; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 3600000)
    const timeStr = `${t.getHours().toString().padStart(2,'0')}:00`
    lines.forEach(line => {
      const key = `${category}_${line.name}`
      const baseVal = demoBaseValues.value[key]
      const sinWave = Math.sin((24 - i) / 15) * line.range * 0.3
      const noise = (Math.random() - 0.5) * line.range * 0.2
      data.push({ name: line.name, time: timeStr, value: (baseVal + sinWave + noise).toFixed(2) })
    })
  }
  return data
}

// async function fetchData(showLoading = false) {
//   if (showLoading) loading.value = true
//   // if (FORCE_DEMO) {
//   //   chartData.value = generateDemoData()
//   //   calculateStats()
//   //   if (showLoading) setTimeout(() => { loading.value = false }, 300)
//   //   return
//   // }

//   const res = await axios.get(`/api/scada/history?date=${selectedDate.value}`, {
//   params: {
//     category: activeCategoryKey.value,
//     date: selectedDate.value
//   }
// })

// chartData.value = res.data
//   try {
//     // chartData.value = generateDemoData()
//     const res = await axios.get('/api/scada/history', {
//   params: {
//     category: activeCategoryKey.value,
//     date: selectedDate.value
//   }
// })

// chartData.value = res.data
// calculateStats()
//     calculateStats()
//   } finally {
//     if (showLoading) setTimeout(() => { loading.value = false }, 500)
//   }
// }

let isFetching = false

async function fetchData(showLoading = false) {
  if (isFetching) return

  isFetching = true

  if (showLoading) {
    loading.value = true
  }

  try {
    const response = await fetch(
      `/api/scada/history?date=${selectedDate.value}`
    )

    const apiData = await response.json()

    const rawData = Array.isArray(apiData)
      ? apiData
      : apiData.data || []

    console.log('RAW API DATA =>', rawData)

    /*
      FIX:
      We identify sensor index INSIDE EACH TIMESTAMP.

      Example at 14:00:
      pressure -> Pressure 1
      pressure -> Pressure 2
      pressure -> Pressure 3
      pressure -> Pressure 4

      Then at 14:01 reset numbering again.
    */

    const timeGroups = {}

    const transformedData = rawData.map((item) => {
      const time = item.time
      const baseName = item.name?.toLowerCase() || 'unknown'

      if (!timeGroups[time]) {
        timeGroups[time] = {}
      }

      if (!timeGroups[time][baseName]) {
        timeGroups[time][baseName] = 1
      } else {
        timeGroups[time][baseName]++
      }

      const index = timeGroups[time][baseName]

      let sensorName = baseName

      if (baseName === 'pressure') {
        sensorName = `Pressure ${index}`
      }

      else if (baseName === 'rpm') {
        sensorName = `RPM ${index}`
      }

      else if (baseName === 'level') {
        sensorName = 'Level'
      }

      else if (baseName === 'total') {
        sensorName = 'Total'
      }

      return {
        name: sensorName,
        time: item.time,
        value: Number(item.value),
      }
    })

    /*
      CATEGORY FILTERS
    */

    const categoryMap = {
      cumulativeOutput: [
        'Total',
      ],

      instantaneousRate: [
        'RPM 1',
        'RPM 2',
      ],

      motorLoad: [
        'RPM 1',
        'RPM 2',
      ],

      vibration: [
        'Pressure 1',
      ],

      temperature: [
        'Pressure 2',
      ],

      machineLoad: [
        'Level',
      ],

      ptValues: [
        'Pressure 1',
        'Pressure 2',
        'Pressure 3',
        'Pressure 4',
      ],
    }

    const allowed =
      categoryMap[activeCategoryKey.value] || []

    chartData.value = transformedData.filter(item =>
      allowed.includes(item.name)
    )

    console.log('FINAL CHART DATA =>', chartData.value)

    calculateStats()
  }
  catch (err) {
    console.error('Chart API Error:', err)

    chartData.value = []
  }
  finally {
    if (showLoading) {
      setTimeout(() => {
        loading.value = false
      }, 300)
    }

    isFetching = false
  }
}

function calculateStats() {
  if (!chartData.value.length) { Object.assign(chartStats, { max: 0, min: 0, avg: 0, changeRate: 0 }); return }
  const values = chartData.value.map(item => parseFloat(item.value)).filter(v => !isNaN(v))
  if (!values.length) return
  const max = Math.max(...values), min = Math.min(...values)
  const avg = values.reduce((s, v) => s + v, 0) / values.length
  Object.assign(chartStats, { max, min, avg, changeRate: 0 })
}

function preprocessChartData() {
  const nameGroups = {}
  chartData.value.forEach(item => {
    if (!nameGroups[item.name]) nameGroups[item.name] = []
    nameGroups[item.name].push({ x: item.time, y: parseFloat(item.value) || 0 })
  })
  return Object.keys(nameGroups).map(name => ({
    name, data: nameGroups[name].sort((a, b) => a.x.localeCompare(b.x))
  }))
}

const chartSeries = computed(() => {
  if (!chartData.value.length) return []
  const seriesData = preprocessChartData()
  const allTimes = [...new Set(chartData.value.map(d => d.time))].sort()
  return seriesData.map(s => ({
    name: s.name,
    data: allTimes.map(t => { const pt = s.data.find(p => p.x === t); return pt ? pt.y : null })
  }))
})

const chartCategories = computed(() => {
  if (!chartData.value.length) return []
  return [...new Set(chartData.value.map(d => d.time))].sort()
})

const chartOptions = computed(() => ({
  chart: {
    type: 'line', height: 600, fontFamily: 'Inter, sans-serif',
    animations: { enabled: true, easing: 'linear', speed: 800, dynamicAnimation: { enabled: true, speed: 1000 } },
    events: {
      mouseMove() { isHoveringChart.value = true },
      mouseLeave() { isHoveringChart.value = false; fetchData(false) },
    },
    toolbar: { show: false }, zoom: { enabled: true, type: 'x' }, background: 'transparent',
  },
  stroke: { curve: 'straight', width: 3 },
  colors: seriesColors,
  dataLabels: { enabled: false },
  markers: { size: 5, strokeWidth: 2, strokeColors: '#0d0d12', hover: { size: 8 } },
  grid: {
    show: true, borderColor: '#1a2640', strokeDashArray: 3, position: 'back',
    xaxis: { lines: { show: true } }, yaxis: { lines: { show: true } },
    padding: { top: 10, right: 10, bottom: 10, left: 10 },
  },
  xaxis: {
    labels: { show: true, style: { colors: '#9eabc8', fontSize: '12px', fontFamily: 'Space Grotesk, sans-serif' } },
    axisBorder: { show: true, color: '#1a2640' }, axisTicks: { show: true, color: '#1a2640' },
  },
  yaxis: {
    labels: {
      style: { colors: '#9eabc8', fontSize: '12px', fontFamily: 'Space Grotesk, sans-serif' },
      formatter(val) { return val != null ? val.toFixed(2) : '' },
    },
    axisBorder: { show: true, color: '#1a2640' },
  },
  tooltip: {
    theme: 'dark', shared: false, intersect: true,
    y: { formatter(val) { return val != null ? val.toFixed(2) : '' } },
    style: { fontSize: '12px', fontFamily: 'Inter, sans-serif' },
  },
  legend: {
    show: true, position: 'top', horizontalAlign: 'right',
    fontSize: '12px', fontFamily: 'Inter, sans-serif',
    labels: { colors: '#9eabc8' },
    markers: { width: 8, height: 8, radius: 8 },
    itemMargin: { horizontal: 8, vertical: 2 },
    onItemClick: { toggleDataSeries: true },
  },
  responsive: [
    { breakpoint: 768, options: { chart: { height: 400 }, xaxis: { tickAmount: 8, labels: { rotate: -45 } }, markers: { size: 3 } } },
    { breakpoint: 480, options: { chart: { height: 300 }, xaxis: { tickAmount: 4, labels: { rotate: -45 } }, markers: { size: 2 }, stroke: { width: 2 } } },
  ],
}))

function setActiveCategory(key) { activeCategoryKey.value = key; fetchData(true) }

function exportData() {
  if (!chartData.value.length) { alert('No data to export'); return }
  const nameGroups = {}
  chartData.value.forEach(item => { if (!nameGroups[item.name]) nameGroups[item.name] = []; nameGroups[item.name].push(item) })
  const allTimes = [...new Set(chartData.value.map(item => item.time))].sort()
  const names = Object.keys(nameGroups)
  let csv = 'data:text/csv;charset=utf-8,Time,' + names.join(',') + '\n'
  allTimes.forEach(time => {
    csv += time + ',' + names.map(name => { const pt = chartData.value.find(i => i.time === time && i.name === name); return pt ? pt.value : '' }).join(',') + '\n'
  })
  const link = document.createElement('a')
  link.setAttribute('href', encodeURI(csv))
  link.setAttribute('download', `${activeCategory.value}_${selectedDate.value}.csv`)
  document.body.appendChild(link); link.click(); document.body.removeChild(link)
}

const statCards = computed(() => [
  { key: 'max', label: 'MAXIMUM VALUE', short: 'Max', value: formatValue(chartStats.max), unit: '' },
  { key: 'min', label: 'MINIMUM VALUE', short: 'Min', value: formatValue(chartStats.min), unit: '' },
  { key: 'avg', label: 'AVERAGE VALUE', short: 'Avg', value: formatValue(chartStats.avg), unit: '' },
  { key: 'pts', label: 'DATA POINTS', short: 'Points', value: String(chartData.value.length), unit: 'log' },
  { key: 'lines', label: 'DATA LINES', short: 'Lines', value: String(getUniqueNameCount()).padStart(2,'0'), unit: 'streams' },
])

watch(selectedDate, () => fetchData(true))
onMounted(() => { fetchData(true); updateTimerId = setInterval(() => { if (!isHoveringChart.value) fetchData(false) }, 2000) })
onBeforeUnmount(() => { if (updateTimerId) clearInterval(updateTimerId) })
</script>

<template>
  <div class="relative min-h-[calc(100vh-3.5rem)]">
    <!-- Factory Background -->
    <div class="fixed inset-0 z-[-2] bg-gradient-to-b from-[#0d0d12] to-[#111318]" />

    <div class="px-4 md:px-8 pt-6 pb-12">
      <!-- Category Buttons -->
      <div class="flex gap-2 md:gap-3 mb-6 md:justify-center overflow-x-auto pb-2 md:flex-wrap scrollbar-hide">
        <button
          v-for="key in categoryKeys" :key="key"
          @click="setActiveCategory(key)"
          :class="[
            'px-4 py-2 md:px-5 md:py-2.5 rounded-full text-xs md:text-sm font-medium transition-all duration-300 border whitespace-nowrap flex-shrink-0',
            activeCategoryKey === key
              ? 'bg-primary/20 text-primary border-primary/40 shadow-[0_0_12px_rgba(244,162,91,0.15)]'
              : 'bg-surface-container-high/60 text-on-surface-variant border-outline-variant/20 hover:bg-primary/10 hover:text-primary hover:border-primary/30',
          ]"
        >{{ categoryLabels[key] }}</button>
      </div>

      <!-- Date Picker -->
      <div class="flex justify-center mb-8">
        <div class="glass-panel rounded-full px-6 py-3 flex items-center gap-3">
          <span class="material-symbols-outlined text-primary text-sm">calendar_today</span>
          <input type="date" class="bg-transparent border-none text-on-surface font-medium text-sm focus:outline-none tabular-nums cursor-pointer" v-model="selectedDate" :max="maxDate" />
        </div>
      </div>

      <!-- Chart Card -->
      <section class="mb-8 relative">
        <div class="chart-glass-panel glass-panel rounded-2xl md:rounded-3xl overflow-hidden min-h-[350px] md:min-h-[500px] flex flex-col relative">
          <!-- Chart Header -->
          <div class="p-4 md:p-6 flex justify-between items-center border-b border-primary/10">
            <div class="hidden md:flex items-center gap-6 flex-wrap">
              <div v-for="(s, idx) in chartSeries" :key="s.name" class="flex items-center gap-2">
                <span class="w-3 h-3 rounded-full" :style="{ backgroundColor: seriesColors[idx % seriesColors.length], boxShadow: `0 0 8px ${seriesColors[idx % seriesColors.length]}cc` }" />
                <span class="text-xs font-bold uppercase tracking-widest text-on-surface/70">{{ s.name }}</span>
              </div>
            </div>
            <span class="md:hidden text-xs font-bold text-primary uppercase tracking-widest">{{ categoryLabels[activeCategoryKey] }}</span>
            <div class="flex gap-2">
              <button class="p-2 hover:bg-white/5 rounded-lg transition-colors" @click="exportData"><span class="material-symbols-outlined text-on-surface-variant">download</span></button>
              <button class="p-2 hover:bg-white/5 rounded-lg transition-colors" @click="fetchData(true)"><span class="material-symbols-outlined text-on-surface-variant">refresh</span></button>
            </div>
          </div>

          <!-- Chart Area -->
          <div class="flex-1 chart-grid relative p-4">
            <apexchart ref="chartRef" type="line" :options="chartOptions" :series="chartSeries" :height="chartOptions.chart.height" />
            <div v-if="loading" class="absolute inset-0 flex flex-col items-center justify-center bg-background/60 backdrop-blur-sm z-10">
              <div class="spinner" /><p class="text-on-surface-variant text-sm">Loading data...</p>
            </div>
            <div v-if="!loading && chartData.length === 0" class="absolute inset-0 flex flex-col items-center justify-center bg-background/60 backdrop-blur-sm z-10">
              <span class="material-symbols-outlined text-on-surface-variant/40 text-5xl mb-4">show_chart</span>
              <p class="text-on-surface-variant text-sm">No data available for selected date</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Stats Grid -->
      <section class="flex flex-wrap gap-2 md:gap-4 lg:gap-6 lg:grid lg:grid-cols-5">
        <div
          v-for="stat in statCards" :key="stat.key"
          @click="expandedStat = expandedStat === stat.key ? null : stat.key"
          class="bg-white/[0.05] backdrop-blur-xl rounded-xl md:rounded-2xl border border-white/5 min-w-0 overflow-hidden cursor-pointer transition-all duration-400 ease-[cubic-bezier(0.4,0,0.2,1)] lg:h-28 lg:col-span-1"
          :class="[
            expandedStat === stat.key ? 'basis-full p-4 md:p-5 border-primary/30 bg-primary/[0.08] order-first'
              : expandedStat && expandedStat !== stat.key ? 'basis-[calc(50%-4px)] md:basis-auto p-3 md:p-5 opacity-70'
              : 'basis-[calc(33.333%-6px)] md:basis-auto p-3 md:p-5',
          ]"
        >
          <div class="flex items-center justify-between mb-1 md:mb-2">
            <span class="text-[9px] md:text-xs font-bold text-on-surface/50 uppercase tracking-wider">{{ expandedStat === stat.key ? stat.label : stat.short }}</span>
            <span v-if="expandedStat === stat.key" class="material-symbols-outlined text-primary/40 text-sm">close</span>
          </div>
          <div class="flex items-baseline gap-1">
            <span class="font-bold font-body text-primary drop-shadow-[0_0_12px_rgba(244,162,91,0.3)] tabular-nums transition-all duration-300" :class="expandedStat === stat.key ? 'text-3xl md:text-4xl' : 'text-base md:text-2xl lg:text-3xl truncate'">{{ stat.value }}</span>
            <span v-if="stat.unit" class="text-[8px] md:text-[10px] text-primary/60 font-mono flex-shrink-0">{{ stat.unit }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
.chart-grid {
  background-image: linear-gradient(rgba(244,162,91,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(244,162,91,0.04) 1px, transparent 1px);
  background-size: 40px 40px;
}
.spinner { border: 3px solid rgba(244,162,91,0.2); border-radius: 50%; border-top: 3px solid #f4a25b; width: 40px; height: 40px; animation: spin 1s linear infinite; margin-bottom: 1rem; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.tabular-nums { font-variant-numeric: tabular-nums; }
.duration-400 { transition-duration: 400ms; }
input[type='date']::-webkit-calendar-picker-indicator { filter: invert(1) brightness(0.8); cursor: pointer; }
</style>

<style>
.apexcharts-tooltip { background: rgba(13,13,18,0.9) !important; backdrop-filter: blur(16px) !important; border: 1px solid rgba(244,162,91,0.15) !important; border-radius: 12px !important; box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important; color: #e8e8f0 !important; }
.apexcharts-tooltip-title { background: rgba(244,162,91,0.08) !important; border-bottom: 1px solid rgba(244,162,91,0.1) !important; color: #9eabc8 !important; font-family: 'Space Grotesk', sans-serif !important; }
.apexcharts-tooltip-text-y-value { color: #f4a25b !important; font-weight: 700 !important; }
.apexcharts-tooltip-series-group { padding: 4px 10px !important; }
.apexcharts-xaxistooltip { background: rgba(13,13,18,0.9) !important; border: 1px solid rgba(244,162,91,0.15) !important; color: #9eabc8 !important; }
</style>
