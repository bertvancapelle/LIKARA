/**
 * Tests — useSleepbaar (LI038 gate 2 v2): hét gedeelde overlay-sleep-gedrag, geconvergeerd
 * uit de kaart-legenda/-popup (de proces-diagram-popup is de derde afnemer). Dekt de vier
 * patroon-eisen: DOM-positie-init bij de eerste drag (geen sprong), knoppen/links/inputs
 * zijn geen greep, document-listeners (slepen loopt door buiten het paneel; opgeruimd bij
 * unmount) en reset() naar de CSS-standaardpositie.
 */
import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { useSleepbaar } from '@/composables/useSleepbaar'

const Host = defineComponent({
  setup() {
    return useSleepbaar()
  },
  template: '<div></div>',
})

const _beweeg = (x, y) => document.dispatchEvent(new MouseEvent('mousemove', { clientX: x, clientY: y }))
const _los = () => document.dispatchEvent(new MouseEvent('mouseup'))

describe('useSleepbaar', () => {
  it('start op de CSS-standaardpositie (null) en sleept relatief zonder sprong', () => {
    const w = mount(Host)
    expect(w.vm.pos).toEqual({ x: null, y: null })
    // Eerste drag: init uit de werkelijke DOM-positie (rect 1200,100), muis op 800,100.
    w.vm.onMousedown({
      clientX: 800, clientY: 100,
      target: { closest: () => null },
      currentTarget: { getBoundingClientRect: () => ({ left: 1200, top: 100 }) },
      preventDefault() {},
    })
    expect(w.vm.dragging).toBe(true)
    expect(w.vm.pos).toEqual({ x: 1200, y: 100 }) // geïnitialiseerd, niet (0,0)
    _beweeg(850, 120) // 50px rechts, 20px omlaag — via de DOCUMENT-listener
    expect(w.vm.pos).toEqual({ x: 1250, y: 120 }) // schuift relatief, springt niet naar de hoek
    _los()
    expect(w.vm.dragging).toBe(false)
    _beweeg(999, 999) // na mouseup beweegt er niets meer
    expect(w.vm.pos).toEqual({ x: 1250, y: 120 })
    w.unmount()
  })

  it('een mousedown op een knop/link/input start geen drag (acties blijven klikbaar)', () => {
    const w = mount(Host)
    w.vm.onMousedown({ target: { closest: (sel) => (sel.includes('button') ? {} : null) }, preventDefault() {} })
    expect(w.vm.dragging).toBe(false)
    expect(w.vm.pos).toEqual({ x: null, y: null })
    w.unmount()
  })

  it('reset() zet terug naar de standaardpositie; unmount ruimt de document-listeners op', () => {
    const w = mount(Host)
    w.vm.onMousedown({ clientX: 10, clientY: 10, target: { closest: () => null }, currentTarget: { getBoundingClientRect: () => ({ left: 5, top: 5 }) }, preventDefault() {} })
    _beweeg(20, 20)
    expect(w.vm.pos).toEqual({ x: 15, y: 15 })
    w.vm.reset()
    expect(w.vm.pos).toEqual({ x: null, y: null })
    // Unmount → listeners weg: een latere mousemove muteert niets meer (geen lek).
    w.vm.onMousedown({ clientX: 0, clientY: 0, target: { closest: () => null }, currentTarget: { getBoundingClientRect: () => ({ left: 0, top: 0 }) }, preventDefault() {} })
    w.unmount()
    _beweeg(50, 50)
    expect(w.vm.pos).toEqual({ x: 0, y: 0 }) // onveranderd ná unmount
  })
})
