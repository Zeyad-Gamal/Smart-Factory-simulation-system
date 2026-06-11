<script setup>
import { useAppStore } from '../stores/app'
const app = useAppStore()

const cards = [
  { to: '/scada', icon: 'dashboard', title: 'SCADA Panel', sub: 'Control Interface', color: 'primary', accent: 'rgba(244,162,91,0.5)', glow: 'rgba(244,162,91,0.2)', module: '01' },
  { to: '/data-trend', icon: 'query_stats', title: 'Data Trend', sub: 'Telemetry Analysis', color: 'secondary', accent: 'rgba(93,230,255,0.5)', glow: 'rgba(93,230,255,0.2)', module: '02' },
  { to: '/alert-history', icon: 'warning', title: 'Alerts', sub: 'Critical Events', color: 'error', accent: 'rgba(255,180,171,0.5)', glow: 'rgba(255,180,171,0.2)', module: '03' },
  { to: '/report', icon: 'analytics', title: 'Report', sub: 'Compliance Docs', color: 'tertiary', accent: 'rgba(197,219,255,0.5)', glow: 'rgba(197,219,255,0.2)', module: '04' },
  { to: '/', icon: 'terminal', title: 'System SOP', sub: 'Operational Manuals', color: 'primary', accent: 'rgba(244,162,91,0.5)', glow: 'rgba(244,162,91,0.2)', module: '05', external: true },
]
</script>

<template>
  <!-- Factory Background -->
  <div class="factory-bg"></div>
  <div class="factory-grid-overlay"></div>
  <div class="scanline-overlay"></div>

  <!-- HUD Corner Labels -->
  <div class="fixed top-4 left-4 font-label text-[8px] text-primary/20 tracking-widest z-30">
    PLANT: FACILITY_01 · ZONE_A
  </div>
  <div class="fixed top-4 right-4 font-label text-[8px] text-primary/20 tracking-widest z-30">
    FPS_V4.2.0_SECURE
  </div>

  <!-- Top Bar -->
  <header class="fixed top-0 left-0 w-full z-40 flex justify-between items-center px-6 md:px-12 py-6 md:py-8 bg-transparent">
    <div class="flex flex-col">
      <span class="text-xs font-bold tracking-[0.4em] text-secondary font-label uppercase">Monitor &amp; Control</span>
      <span class="text-sm font-black tracking-widest text-primary mt-1">FACTORY PRECISION SYSTEMS</span>
    </div>
    <div class="flex items-center gap-3">
      <!-- Mobile hamburger -->
      <button
        class="md:hidden glass-card-tech p-4 rounded-full flex items-center justify-center hover:bg-surface-container-high active:scale-95 group relative cursor-pointer border-none"
        @click="app.toggleMenu"
      >
        <span class="material-symbols-outlined text-primary group-hover:text-secondary" style="font-variation-settings: 'FILL' 0">menu</span>
      </button>
    </div>
  </header>

  <!-- Main Content -->
  <main class="relative z-10 h-screen flex flex-col items-center justify-center px-8 -mt-14">
    <div class="text-center mb-16 max-w-4xl">
      <div class="inline-flex items-center gap-4 mb-8">
        <div class="h-px w-16 bg-gradient-to-r from-transparent to-outline-variant"></div>
        <span class="font-label text-[10px] tracking-[0.6em] text-primary/40 uppercase">Industrial Intelligence</span>
        <div class="h-px w-16 bg-gradient-to-l from-transparent to-outline-variant"></div>
      </div>

      <div class="factory-title">
        <h1 class="font-headline font-black text-5xl md:text-9xl tracking-tighter text-on-surface mb-2 flex flex-col items-center">
          <span>Factory SCADA</span>
          <span class="text-xl md:text-3xl font-light tracking-[0.2em] md:tracking-[0.3em] text-on-surface/60 mt-4 md:mt-6 font-label">
            Industrial Machine Monitoring System
          </span>
        </h1>
      </div>

      <div class="flex items-center justify-center gap-8 mt-16">
        <div class="h-px w-32 bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
        <div class="relative">
          <span class="material-symbols-outlined text-primary text-lg" style="font-variation-settings: 'FILL' 1; animation: spin 4s linear infinite; display:inline-block">settings</span>
          <div class="absolute inset-0 bg-primary/20 blur-xl rounded-full"></div>
        </div>
        <div class="h-px w-32 bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
      </div>

      <p class="mt-8 font-label text-xs tracking-[0.4em] text-secondary uppercase opacity-70">
        Precision Telemetry · Automated Analysis · Smart Manufacturing
      </p>
    </div>

    <!-- Navigation Cards -->
    <div class="hidden md:grid md:grid-cols-5 gap-4 w-full max-w-[1400px] px-4">
      <router-link
        v-for="card in cards"
        :key="card.module"
        :to="card.to"
        class="glass-card-tech group relative overflow-hidden p-8 rounded-lg cursor-pointer hover:-translate-y-2 block no-underline transition-transform duration-300"
        :style="{ '--card-accent': card.accent, '--card-glow': card.glow }"
      >
        <div class="absolute top-0 right-0 p-2 font-label text-[8px] uppercase" :class="`text-${card.color}/20`">
          Module_{{ card.module }}
        </div>
        <div class="mb-8">
          <span class="material-symbols-outlined text-5xl transition-transform duration-700 group-hover:scale-110" :class="`text-${card.color}`" style="font-variation-settings: 'FILL' 0">{{ card.icon }}</span>
        </div>
        <h3 class="font-headline font-bold text-lg text-on-surface transition-colors tracking-tight" :class="`group-hover:text-${card.color}`">{{ card.title }}</h3>
        <p class="text-[10px] text-on-surface-variant mt-2 leading-relaxed font-label uppercase tracking-widest opacity-60">{{ card.sub }}</p>
      </router-link>
    </div>
  </main>

  <!-- Footer Stats -->
  <footer class="fixed bottom-0 left-0 w-full z-40 flex flex-col md:flex-row justify-between items-start md:items-end px-6 md:px-12 py-6 md:py-10 bg-transparent gap-3 md:gap-0">
    <div class="flex gap-8 md:gap-20">
      <div class="flex flex-col">
        <div class="flex items-center gap-2 mb-1">
          <span class="font-label text-[9px] tracking-widest text-on-surface-variant uppercase">Output Rate</span>
          <span class="w-1 h-1 rounded-full bg-primary"></span>
        </div>
        <span class="font-headline font-black text-3xl text-primary tabular-nums">482.5
          <span class="text-xs font-light ml-1 opacity-50">units/h</span>
        </span>
      </div>
      <div class="flex flex-col border-l border-outline-variant/20 pl-4 md:pl-10">
        <div class="flex items-center gap-2 mb-1">
          <span class="font-label text-[9px] tracking-widest text-on-surface-variant uppercase">Motor Load</span>
          <span class="w-1 h-1 rounded-full bg-secondary"></span>
        </div>
        <span class="font-headline font-black text-3xl text-secondary tabular-nums">74.2
          <span class="text-xs font-light ml-1 opacity-50">%</span>
        </span>
      </div>
      <div class="flex flex-col border-l border-outline-variant/20 pl-4 md:pl-10">
        <div class="flex items-center gap-2 mb-1">
          <span class="font-label text-[9px] tracking-widest text-on-surface-variant uppercase">Temperature</span>
          <span class="w-1 h-1 rounded-full bg-on-surface/50"></span>
        </div>
        <span class="font-headline font-black text-3xl text-on-surface tabular-nums">68.4
          <span class="text-xs font-light ml-1 opacity-50">°C</span>
        </span>
      </div>
    </div>
    <div class="flex flex-col items-end">
      <div class="flex gap-4 mb-4">
        <div class="glass-card-tech px-3 py-1 rounded-full flex items-center gap-2">
          <div class="w-1.5 h-1.5 rounded-full bg-primary" style="box-shadow: 0 0 8px #f4a25b"></div>
          <span class="font-label text-[9px] tracking-widest text-primary uppercase">STATUS: NOMINAL</span>
        </div>
      </div>
      <p class="font-label text-[9px] font-medium tracking-[0.2em] uppercase text-on-surface/30">
        © 2024 FACTORY PRECISION SYSTEMS · INDUSTRIAL OPS
      </p>
    </div>
  </footer>
</template>

<style scoped>
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.factory-bg {
  position: fixed; inset: 0;
  background: radial-gradient(ellipse at 20% 50%, rgba(244,162,91,0.06) 0%, transparent 60%),
    radial-gradient(ellipse at 80% 20%, rgba(93,230,255,0.05) 0%, transparent 50%),
    linear-gradient(180deg, #0d0d12 0%, #111318 100%);
  z-index: -2;
}
.factory-grid-overlay {
  position: fixed; inset: 0;
  background-image: linear-gradient(rgba(244,162,91,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(244,162,91,0.04) 1px, transparent 1px);
  background-size: 80px 80px;
  pointer-events: none; z-index: -1;
}
.scanline-overlay {
  position: fixed; inset: 0;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px);
  pointer-events: none; z-index: -1;
}
.factory-title {
  position: relative;
  filter: drop-shadow(0 0 10px rgba(244,162,91,0.3));
}
.glass-card-tech {
  background: rgba(14,14,14,0.4);
  backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(133,148,144,0.15);
  transition: all 0.5s cubic-bezier(0.4,0,0.2,1);
}
.glass-card-tech:hover {
  background: rgba(14,14,14,0.6);
  border-color: var(--card-accent);
  box-shadow: 0 0 30px -5px var(--card-glow);
}
</style>
