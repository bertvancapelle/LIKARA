/** Tests — IdentiteitLabel + partijIdentiteit (LI040): DE identiteitsvorm voor
 *  afdelingen en personen. Vaste vorm `afdeling — organisatie` /
 *  `persoon — afdeling — organisatie`; nooit ingekort; het deel ná de naam is de
 *  gedempte leeslaag (bestaand muted-token) op dezelfde regel. Het component en de
 *  string-helper leveren dezelfde volledige tekst (picker-input = string, lijst =
 *  component) — afwijking tussen die twee is precies de bug die deze bouwsteen weert. */
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import { partijIdentiteit } from '@modules/bwb_ontvlechting/frontend/labels'
import IdentiteitLabel from '@modules/bwb_ontvlechting/frontend/views/IdentiteitLabel.vue'

describe('partijIdentiteit (labels.js)', () => {
  it('afdeling: "afdeling — organisatie"', () => {
    expect(partijIdentiteit('Burgerzaken', null, 'Gemeente Tiel')).toBe('Burgerzaken — Gemeente Tiel')
  })
  it('persoon: "persoon — afdeling — organisatie"', () => {
    expect(partijIdentiteit('J. de Vries', 'Burgerzaken', 'Gemeente Tiel'))
      .toBe('J. de Vries — Burgerzaken — Gemeente Tiel')
  })
  it('persoon zonder afdeling: "persoon — organisatie"', () => {
    expect(partijIdentiteit('J. de Vries', null, 'Gemeente Tiel')).toBe('J. de Vries — Gemeente Tiel')
  })
  it('alleen een naam blijft een kale naam (organisatie zelf)', () => {
    expect(partijIdentiteit('Gemeente Tiel', null, null)).toBe('Gemeente Tiel')
  })
})

describe('IdentiteitLabel.vue', () => {
  it('levert dezelfde volledige tekst als de string-helper (lijst = input)', () => {
    const w = mount(IdentiteitLabel, {
      props: { naam: 'J. de Vries', afdeling: 'Burgerzaken', organisatie: 'Gemeente Tiel' },
    })
    expect(w.text().replace(/\s+/g, ' ')).toBe(partijIdentiteit('J. de Vries', 'Burgerzaken', 'Gemeente Tiel'))
  })

  it('dempt het deel ná de naam met het bestaande muted-token, op dezelfde regel', () => {
    const w = mount(IdentiteitLabel, { props: { naam: 'Studenten', organisatie: 'Burgers Culemborg' } })
    const rest = w.find('[data-testid="identiteit-rest"]')
    expect(rest.text()).toBe('— Burgers Culemborg')
    expect(rest.classes().join(' ')).toContain('text-[var(--lk-color-text-muted)]')
    // De naam zelf staat NIET in het gedempte deel (scanlaag blijft primair).
    expect(rest.text()).not.toContain('Studenten')
  })

  it('kapt nooit af: geen truncate, wél wrappen toegestaan', () => {
    const w = mount(IdentiteitLabel, {
      props: { naam: 'Afdeling met een hele lange naam', organisatie: 'Gemeenschappelijke Regeling Bedrijfsvoering' },
    })
    expect(w.html()).not.toContain('truncate')
    expect(w.classes().join(' ')).toContain('whitespace-normal')
  })

  it('LI040-harding: een lege naam rendert een zichtbare faal-marker + console.error (nooit stil)', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const w = mount(IdentiteitLabel, { props: { naam: '', organisatie: 'Gemeente Tiel' } })
    expect(w.find('[data-testid="identiteit-naam-ontbreekt"]').text()).toContain('naam ontbreekt')
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })

  it('zonder context-delen: alleen de naam, geen leeg streepje', () => {
    const w = mount(IdentiteitLabel, { props: { naam: 'Gemeente Tiel' } })
    expect(w.text()).toBe('Gemeente Tiel')
    expect(w.find('[data-testid="identiteit-rest"]').exists()).toBe(false)
  })
})
