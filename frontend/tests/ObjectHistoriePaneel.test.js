/** Tests — ObjectHistoriePaneel ('i'-knop, ADR-029): naam + diff, openen laadt, geen rol-gating. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({ api: { objecthistorie: { lijst: vi.fn() } } }))

import { api } from '@/api'
import ObjectHistoriePaneel from '@modules/bwb_ontvlechting/frontend/views/ObjectHistoriePaneel.vue'

const _historie = () => ({
  items: [{
    correlatie_id: 'c1', tijdstip: '2026-06-19T10:00:00Z',
    actor_naam: 'Jan de Vries', actor_email: 'jan@org.nl',
    records: [{
      id: 'r1', entiteit_type: 'applicatie', actie: 'update', actor_naam: 'Jan de Vries',
      wijziging: { beschrijving: { oud: 'A', nieuw: 'B' } },
    }],
  }],
  volgende_cursor: null,
})

function mountPaneel(props = { entiteitType: 'applicatie', entiteitId: 'app-1' }) {
  return mount(ObjectHistoriePaneel, {
    props,
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }]], stubs: { teleport: true } },
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  api.objecthistorie.lijst.mockResolvedValue(_historie())
})
afterEach(() => vi.restoreAllMocks())

describe('ObjectHistoriePaneel', () => {
  it("'i'-knop is altijd zichtbaar (geen rol-gating)", () => {
    const w = mountPaneel()
    expect(w.find('[data-testid="oh-knop"]').exists()).toBe(true)
  })

  it('laadt pas bij openen (niet op mount)', async () => {
    const w = mountPaneel()
    await flushPromises()
    expect(api.objecthistorie.lijst).not.toHaveBeenCalled()
    await w.find('[data-testid="oh-knop"]').trigger('click')
    await flushPromises()
    expect(api.objecthistorie.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ entiteitType: 'applicatie', entiteitId: 'app-1' }),
    )
  })

  it('toont gebeurtenissen met naam én de detail-diff per record', async () => {
    const w = mountPaneel()
    await w.find('[data-testid="oh-knop"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="oh-wie"]').text()).toContain('Jan de Vries')
    const diff = w.find('[data-testid="oh-diff"]').text()
    expect(diff).toContain('Beschrijving')   // humanize van het veld
    expect(diff).toContain('A')
    expect(diff).toContain('B')               // oud → nieuw
  })

  it('toont een nette foutmelding bij een API-fout', async () => {
    api.objecthistorie.lijst.mockRejectedValueOnce(Object.assign(new Error('Mislukt'), { status: 500 }))
    const w = mountPaneel()
    await w.find('[data-testid="oh-knop"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="oh-fout"]').exists()).toBe(true)
  })

  it('gebruikt de NL-veldlabels in de diff (niet de ruwe veldnaam)', async () => {
    api.objecthistorie.lijst.mockResolvedValue({
      items: [{
        correlatie_id: 'c1', tijdstip: '2026-06-19T10:00:00Z', actor_naam: 'Jan',
        records: [{ id: 'r1', entiteit_type: 'component', actie: 'update',
                    wijziging: { lifecycle_status: { oud: 'concept', nieuw: 'in_inventarisatie' } } }],
      }],
      volgende_cursor: null,
    })
    const w = mountPaneel({ entiteitType: 'component', entiteitId: 'comp-1' })
    await w.find('[data-testid="oh-knop"]').trigger('click')
    await flushPromises()
    // ADR-046 — 'Levensfase' is het echte `levensfase`-veld; de engine-status heet in de diff
    // 'Beoordelingsstatus' (VELD_LABELS, LI043 naam-fix — was 'Registratiestatus'), niet de ruwe veldnaam.
    expect(w.find('[data-testid="oh-diff"]').text()).toContain('Beoordelingsstatus')
  })

  it('"Meer laden" haalt de volgende pagina op en voegt toe', async () => {
    api.objecthistorie.lijst
      .mockResolvedValueOnce({ ..._historie(), volgende_cursor: 'C1' })
      .mockResolvedValueOnce({
        items: [{ correlatie_id: 'c2', tijdstip: '2026-06-18T10:00:00Z', actor_naam: 'Piet', records: [] }],
        volgende_cursor: null,
      })
    const w = mountPaneel()
    await w.find('[data-testid="oh-knop"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="oh-meer"]').exists()).toBe(true)
    await w.find('[data-testid="oh-meer"]').trigger('click')
    await flushPromises()
    expect(api.objecthistorie.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ after: 'C1' }))
    expect(w.findAll('[data-testid="oh-gebeurtenis"]').length).toBe(2) // geappend
    expect(w.find('[data-testid="oh-meer"]').exists()).toBe(false)     // cursor null → knop weg
  })
})

describe('ObjectHistoriePaneel — LI048: wegwijzer als teken', () => {
  it('de knop draagt het klokje, met een uitgesproken naam', () => {
    // Alle zeven detailschermen erven deze knop, dus dit is één plek voor zeven schermen.
    const w = mountPaneel()
    const knop = w.get('[data-testid="oh-knop"]')
    expect(knop.find('svg[data-icoon="geschiedenis"]').exists()).toBe(true)
    // Een schermlezer moet "Geschiedenis" horen, niet "knop".
    expect(knop.attributes('aria-label')).toBe('Geschiedenis')
    expect(knop.attributes('aria-label')).not.toBe('')
    // De tooltip komt uit `title`; die is niet hetzelfde als aria-label en beide zijn nodig —
    // een tooltip verschijnt pas bij hangen (op een tablet nooit), en een schermlezer leest
    // `title` niet betrouwbaar voor.
    expect(knop.attributes('title')).toBe('Geschiedenis')
  })

  it('draagt geen dode icoon-verwijzing meer', () => {
    // Hier stond `icon="pi pi-info-circle"` — een klasse die nergens bestaat, dus er rendeerde
    // niets. Niet ingevuld maar vervangen: deze knop hoort een klokje te dragen, geen "i".
    const w = mountPaneel()
    expect(w.html()).not.toContain('pi-info-circle')
  })
})
