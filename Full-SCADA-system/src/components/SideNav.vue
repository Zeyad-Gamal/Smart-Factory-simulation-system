<script setup>
import { useAppStore } from '../stores/app'
import { useRoute } from 'vue-router'

const app = useAppStore()
const route = useRoute()

const navLinks = [
  { to: '/', icon: 'home', label: 'Home' },
  { to: '/scada', icon: 'dashboard', label: 'SCADA Panel' },
  { to: '/data-trend', icon: 'show_chart', label: 'Data Trend' },
  { to: '/alert-history', icon: 'notifications_active', label: 'Alerts' },
  { to: '/report', icon: 'description', label: 'Report' },
  { to: null, icon: 'menu_book', label: 'Documentation', external: true },
]
</script>

<template>
  <Teleport to="body">
    <!-- Overlay -->
    <div
      class="fixed inset-0 bg-[#050505]/50 z-[90] backdrop-blur-[2px] transition-opacity duration-500"
      :class="app.isMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'"
      @click="app.closeMenu"
    />

    <!-- Panel -->
    <aside
      class="fixed inset-y-0 right-0 z-[100] flex flex-col w-80 bg-[#0d0d12]/70 backdrop-blur-[40px] border-l border-outline-variant/20 shadow-[0_24px_48px_-12px_rgba(5,5,5,0.6)] transition-transform duration-500 ease-in-out"
      :class="app.isMenuOpen ? 'translate-x-0' : 'translate-x-full'"
    >
      <!-- Header -->
      <div class="p-5 pb-4 sm:p-8 sm:pb-6 shrink-0">
        <div class="flex items-center justify-between mb-4 sm:mb-6">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
              <span class="material-symbols-outlined text-[#0d0d12]" style="font-variation-settings: 'FILL' 1">precision_manufacturing</span>
            </div>
            <div>
              <h2 class="text-xl font-black text-primary tracking-tight">SYSTEM ACCESS</h2>
              <p class="text-[10px] font-label uppercase tracking-[0.2em] text-on-surface-variant/50">Precision Control</p>
            </div>
          </div>
          <button class="text-on-surface-variant/60 hover:text-primary transition-colors active:scale-95 bg-transparent border-none cursor-pointer" @click="app.closeMenu">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="bg-surface-container-high/40 rounded-lg p-4 flex items-center gap-4 border border-outline-variant/20">
          <div class="w-2 h-2 rounded-full bg-primary animate-pulse" style="box-shadow: 0 0 8px #f4a25b"></div>
          <span class="text-xs font-label uppercase tracking-widest text-on-surface">System Online</span>
        </div>
      </div>

      <!-- Nav Links -->
      <nav class="flex-grow flex flex-col px-2 overflow-y-auto">
        <template v-for="link in navLinks" :key="link.label">
          <router-link
            v-if="!link.external"
            :to="link.to"
            class="flex items-center gap-4 px-6 py-4 transition-all duration-300 no-underline"
            :class="route.path === link.to
              ? 'bg-primary/10 text-primary border-l-4 border-primary'
              : 'text-on-surface-variant/70 hover:bg-white/5 hover:text-primary'"
            @click="app.closeMenu"
          >
            <span class="material-symbols-outlined">{{ link.icon }}</span>
            <span class="text-sm font-medium tracking-wide font-headline">{{ link.label }}</span>
            <div v-if="route.path === link.to" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary"></div>
          </router-link>
          <a
            v-else
            href="javascript:void(0)"
            class="flex items-center gap-4 text-on-surface-variant/70 px-6 py-4 hover:bg-white/5 hover:text-primary transition-all duration-300 no-underline"
            @click="app.closeMenu"
          >
            <span class="material-symbols-outlined">{{ link.icon }}</span>
            <span class="text-sm font-medium tracking-wide font-headline">{{ link.label }}</span>
          </a>
        </template>
      </nav>

      <!-- Footer -->
      <div class="p-5 sm:p-8 border-t border-outline-variant/10 shrink-0">
        <div class="flex justify-between items-end">
          <div class="space-y-1">
            <p class="text-[10px] font-label text-on-surface-variant uppercase tracking-widest">Version</p>
            <p class="text-xs font-bold text-on-surface tabular-nums">v4.82.0-FPS</p>
          </div>
          <button class="text-primary hover:text-secondary transition-colors bg-transparent border-none cursor-pointer">
            <span class="material-symbols-outlined">logout</span>
          </button>
        </div>
      </div>
    </aside>
  </Teleport>
</template>
