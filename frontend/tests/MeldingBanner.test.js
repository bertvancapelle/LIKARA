/** Tests — MeldingBanner (gedeeld meldingspatroon op de actieplek, LI035). */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MeldingBanner from '@/components/MeldingBanner.vue'

describe('MeldingBanner', () => {
  it('warn: role=status (polite), ⚠-icoon en warn-kleur — nooit alléén kleur', () => {
    const w = mount(MeldingBanner, { props: { soort: 'warn', tekst: 'Bestaat al.' } })
    const p = w.find('[data-testid="melding-banner"]')
    expect(p.attributes('role')).toBe('status')
    expect(w.find('[data-testid="melding-banner-icoon"]').text()).toBe('⚠')
    // LI030-les: assert de visuele staat, niet alleen de payload.
    expect(p.classes().join(' ')).toContain('lk-color-warning')
    expect(p.text()).toContain('Bestaat al.')
  })

  it('danger: role=alert (assertive) en danger-kleur', () => {
    const w = mount(MeldingBanner, { props: { soort: 'danger', tekst: 'Mislukt.' } })
    const p = w.find('[data-testid="melding-banner"]')
    expect(p.attributes('role')).toBe('alert')
    expect(p.classes().join(' ')).toContain('lk-color-danger')
  })

  it('info: role=status, ℹ-icoon en primary-tint', () => {
    const w = mount(MeldingBanner, { props: { soort: 'info', tekst: 'Ter info.' } })
    const p = w.find('[data-testid="melding-banner"]')
    expect(p.attributes('role')).toBe('status')
    expect(w.find('[data-testid="melding-banner-icoon"]').text()).toBe('ℹ')
    expect(p.classes().join(' ')).toContain('lk-color-primary')
  })

  it('scroll-vangnet: scrollIntoView bij verschijnen (mount), NIET bij een props-update', async () => {
    const spy = vi.fn()
    const origineel = Element.prototype.scrollIntoView
    Element.prototype.scrollIntoView = spy
    try {
      const w = mount(MeldingBanner, { props: { soort: 'warn', tekst: 'Eerste.' } })
      expect(spy).toHaveBeenCalledTimes(1)
      expect(spy).toHaveBeenCalledWith({ block: 'nearest', behavior: 'smooth' })
      // Props-update zonder zichtbaarheidswissel (geen re-mount) → geen tweede scroll.
      await w.setProps({ tekst: 'Tweede.' })
      expect(spy).toHaveBeenCalledTimes(1)
    } finally {
      Element.prototype.scrollIntoView = origineel
    }
  })

  it('default-slot gaat boven de tekst-prop; testid is instelbaar', () => {
    const w = mount(MeldingBanner, {
      props: { tekst: 'genegeerd', testid: 'eigen-id' },
      slots: { default: 'Rijkere <strong>inhoud</strong>' },
    })
    expect(w.find('[data-testid="eigen-id"]').text()).toContain('Rijkere')
    expect(w.text()).not.toContain('genegeerd')
  })
})
