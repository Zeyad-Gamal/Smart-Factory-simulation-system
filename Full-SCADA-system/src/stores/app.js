import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const isMenuOpen = ref(false)
  const isDemoMode = ref(true)
  const currentTimestamp = ref('')

  function updateClock() {
    const now = new Date()
    currentTimestamp.value = now.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  updateClock()
  setInterval(updateClock, 1000)

  function toggleMenu() { isMenuOpen.value = !isMenuOpen.value }
  function closeMenu() { isMenuOpen.value = false }

  return { isMenuOpen, isDemoMode, currentTimestamp, toggleMenu, closeMenu }
})
