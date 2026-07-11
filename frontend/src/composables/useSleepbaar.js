/**
 * useSleepbaar — hét gedeelde sleep-gedrag voor zwevende overlays (LI038 gate 2 v2).
 *
 * Geconvergeerd uit de twee identieke inline-instanties van de Landschapskaart (LI025-legenda +
 * LI034-klik-popup) op het moment dat de proces-popup de derde afnemer werd (n≥2-discipline).
 * Semantiek is exact het bewezen kaart-patroon:
 * - `pos = { x: null, y: null }` — null = de CSS-standaardpositie; slepen zet een absolute
 *   viewport-positie (consument bindt `position: fixed; left/top` zodra `x !== null`).
 * - Positie-init bij de éérste drag uit `getBoundingClientRect()` (niet `?? 0`) — anders springt
 *   het paneel bij de eerste beweging naar de hoek.
 * - Een mousedown op een knop/link/input start géén drag (acties blijven gewoon klikbaar).
 * - mousemove/mouseup op `document` (slepen loopt door buiten het paneel); listeners opgeruimd
 *   bij unmount. `reset()` = terug naar de standaardpositie (spiegel van de wisSet-reset).
 *
 * Aanroepen binnen setup() (registreert onMounted/onBeforeUnmount).
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

export function useSleepbaar({ negeer = 'button, a, input' } = {}) {
  const pos = ref({ x: null, y: null })
  const dragging = ref(false)
  let _offset = { x: 0, y: 0 }

  function onMousedown(e) {
    if (e.target?.closest?.(negeer)) return // acties in het paneel werken gewoon
    if (pos.value.x === null) {
      const r = e.currentTarget?.getBoundingClientRect?.()
      if (r) pos.value = { x: r.left, y: r.top }
    }
    dragging.value = true
    _offset = { x: e.clientX - (pos.value.x ?? 0), y: e.clientY - (pos.value.y ?? 0) }
    e.preventDefault?.()
  }
  function onMousemove(e) {
    if (!dragging.value) return
    pos.value = { x: e.clientX - _offset.x, y: e.clientY - _offset.y }
  }
  function onMouseup() {
    dragging.value = false
  }
  function reset() {
    pos.value = { x: null, y: null }
  }

  onMounted(() => {
    document.addEventListener('mousemove', onMousemove)
    document.addEventListener('mouseup', onMouseup)
  })
  onBeforeUnmount(() => {
    document.removeEventListener('mousemove', onMousemove)
    document.removeEventListener('mouseup', onMouseup)
  })

  return { pos, dragging, onMousedown, onMousemove, onMouseup, reset }
}
