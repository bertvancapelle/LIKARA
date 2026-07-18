/** Tests — popoverPositie (ADR-052 slice 3c): pure flip-/klemlogica, zonder layout-engine. */
import { describe, expect, it } from 'vitest'
import { berekenPopoverPositie } from '@/composables/popoverPositie'

const VP = { w: 1000, h: 800 }

describe('berekenPopoverPositie', () => {
  it('plaatst ONDER de trigger wanneer daar ruimte is', () => {
    const r = berekenPopoverPositie({
      trigger: { top: 80, bottom: 100, left: 40 },
      paneel: { width: 320, height: 200 },
      viewport: VP,
    })
    expect(r.plaatsBoven).toBe(false)
    expect(r.top).toBe(104) // bottom + gat
    expect(r.links).toBe(40)
  })

  it('flipt naar BOVEN de trigger wanneer er onder te weinig ruimte is', () => {
    const r = berekenPopoverPositie({
      trigger: { top: 750, bottom: 770, left: 40 },
      paneel: { width: 320, height: 200 },
      viewport: VP,
    })
    expect(r.plaatsBoven).toBe(true)
    expect(r.top).toBe(546) // 750 - 200 - gat(4)
  })

  it('klemt horizontaal binnen beeld aan de rechterrand', () => {
    const r = berekenPopoverPositie({
      trigger: { top: 80, bottom: 100, left: 900 },
      paneel: { width: 320, height: 200 },
      viewport: VP,
    })
    expect(r.links).toBe(1000 - 320 - 8) // viewport.w - paneel.width - marge
  })

  it('klemt horizontaal binnen beeld aan de linkerrand', () => {
    const r = berekenPopoverPositie({
      trigger: { top: 80, bottom: 100, left: -50 },
      paneel: { width: 320, height: 200 },
      viewport: VP,
    })
    expect(r.links).toBe(8) // marge
  })
})
