/** Tests — SignaleringBadge (ADR-035 Slice 1): 🔴 bij kritiek, 🟡 bij alleen aandacht, niets bij 0. */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SignaleringBadge from '@modules/bwb_ontvlechting/frontend/views/SignaleringBadge.vue'

describe('SignaleringBadge', () => {
  it('kritiek=2 → toont "🔴 2"', () => {
    const w = mount(SignaleringBadge, { props: { kritiek: 2, aandacht: 0 } })
    expect(w.find('[data-testid="signalering-badge"]').exists()).toBe(true)
    expect(w.text()).toContain('🔴 2')
  })

  it('aandacht=1, kritiek=0 → toont "🟡 1"', () => {
    const w = mount(SignaleringBadge, { props: { kritiek: 0, aandacht: 1 } })
    expect(w.text()).toContain('🟡 1')
  })

  it('kritiek heeft voorrang op aandacht', () => {
    const w = mount(SignaleringBadge, { props: { kritiek: 1, aandacht: 3 } })
    expect(w.text()).toContain('🔴 1')
    expect(w.text()).not.toContain('🟡')
  })

  it('beide 0 → geen badge', () => {
    const w = mount(SignaleringBadge, { props: { kritiek: 0, aandacht: 0 } })
    expect(w.find('[data-testid="signalering-badge"]').exists()).toBe(false)
  })

  it('ADR-028: signalen-sleutels → sprekende tooltip met de signaalnamen', () => {
    const w = mount(SignaleringBadge, {
      props: { kritiek: 1, aandacht: 0, signalen: ['biv_classificatie_onvolledig'] },
    })
    expect(w.find('[data-testid="signalering-badge"]').attributes('title')).toBe('BIV-classificatie onvolledig')
  })

  it('zonder signalen valt de tooltip terug op de generieke telling', () => {
    const w = mount(SignaleringBadge, { props: { kritiek: 2, aandacht: 0 } })
    expect(w.find('[data-testid="signalering-badge"]').attributes('title')).toContain('2 kritiek')
  })
})
