/**
 * Tests — ProcesDiagram (LI038 gate 1, proces-only structuurbeeld).
 *
 * Cytoscape gemockt (kaart-testpatroon): getest worden de lege staat, de focus-set-bedrading
 * (zoek → centrum → keten/zusjes/subboom), de gap-cue-doorgifte en de proces-only borging
 * (de component is api-vrij: alles komt uit de props — er is géén '@/api'-mock nodig en er
 * kán dus ook geen component-/vervuller-fetch plaatsvinden).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { createPinia } from 'pinia'

const _cyInstanties = []
vi.mock('@/composables/cytoscape', () => ({
  default: vi.fn(() => {
    const inst = {
      add: vi.fn(),
      layout: vi.fn(() => ({ run: vi.fn() })),
      fit: vi.fn(), resize: vi.fn(), destroy: vi.fn(), on: vi.fn(),
      zoom: () => 1,
      nodes: () => ({ updateStyle: vi.fn(), forEach: vi.fn(), removeClass: vi.fn() }),
      elements: () => ({ remove: vi.fn() }),
      getElementById: () => ({ length: 0, addClass: vi.fn() }),
    }
    _cyInstanties.push(inst)
    return inst
  }),
}))

import ProcesDiagram from '@modules/bwb_ontvlechting/frontend/views/ProcesDiagram.vue'

// Boom: Vergunningverlening → Aanvraag behandelen → Besluit vastleggen
//                           → Toezicht houden → Controle uitvoeren
// plus een losse tweede boom Burgerzaken → Verhuizing verwerken.
const _p = (id, naam, ouder_id = null) => ({ id, naam, ouder_id })
const PROCESSEN = [
  _p('vv', 'Vergunningverlening'),
  _p('ab', 'Aanvraag behandelen', 'vv'),
  _p('bv', 'Besluit vastleggen', 'ab'),
  _p('th', 'Toezicht houden', 'vv'),
  _p('cu', 'Controle uitvoeren', 'th'),
  _p('bz', 'Burgerzaken'),
  _p('verh', 'Verhuizing verwerken', 'bz'),
]

function mountDiagram(props = {}) {
  return mount(ProcesDiagram, {
    props: { processen: PROCESSEN, gapIds: null, ...props },
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
}

beforeEach(() => { _cyInstanties.length = 0 })
afterEach(() => vi.clearAllMocks())

describe('ProcesDiagram — leeg openen + focus-set', () => {
  it('opent leeg met de uitnodiging om te zoeken', async () => {
    const w = mountDiagram()
    await flushPromises()
    expect(w.find('[data-testid="diagram-leeg"]').text()).toContain('Zoek een proces om te beginnen.')
    // Geen elementen getekend op de lege staat.
    const cy = _cyInstanties[0]
    expect(cy.add).not.toHaveBeenCalled()
  })

  it('centrum kiezen toont keten (boven) + subboom (beneden) + zusjes (opzij), zonder andere bomen', async () => {
    const w = mountDiagram()
    await flushPromises()
    w.vm.kiesCentrum({ id: 'ab' })
    await flushPromises()
    // Keten: vv. Subboom: bv. Zusje: th — maar diens subboom (cu) niet; andere boom (bz) niet.
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'vv', 'bv', 'th']))
    expect(w.find('[data-testid="diagram-leeg"]').exists()).toBe(false)
    // De getekende elementen zijn exact de focus-set + de echte ouder→kind-lijnen daarbinnen.
    const cy = _cyInstanties[0]
    expect(cy.add).toHaveBeenCalled()
    const elementen = cy.add.mock.calls.at(-1)[0]
    const nodeIds = elementen.filter((e) => !e.data.source).map((e) => e.data.id)
    const edges = elementen.filter((e) => e.data.source).map((e) => `${e.data.source}>${e.data.target}`)
    expect(new Set(nodeIds)).toEqual(new Set(['ab', 'vv', 'bv', 'th']))
    expect(new Set(edges)).toEqual(new Set(['ab>vv', 'bv>ab', 'th>vv']))
  })

  it('wortel-centrum: geen valse ouder-lijn boven de wortel', async () => {
    const w = mountDiagram()
    await flushPromises()
    w.vm.kiesCentrum({ id: 'bz' })
    await flushPromises()
    expect(w.vm.zichtbareIds).toEqual(new Set(['bz', 'verh']))
    const cy = _cyInstanties[0]
    const elementen = cy.add.mock.calls.at(-1)[0]
    const edges = elementen.filter((e) => e.data.source).map((e) => `${e.data.source}>${e.data.target}`)
    // Alleen de echte kind→ouder-lijn; niets boven de wortel, geen stam naar de andere boom.
    expect(edges).toEqual(['verh>bz'])
  })

  it('geeft de gap-cue (procesGap) alleen mee aan processen in de gap-set', async () => {
    const w = mountDiagram({ gapIds: new Set(['th', 'cu']) })
    await flushPromises()
    w.vm.kiesCentrum({ id: 'ab' })
    await flushPromises()
    const cy = _cyInstanties[0]
    const elementen = cy.add.mock.calls.at(-1)[0]
    const perId = new Map(elementen.filter((e) => !e.data.source).map((e) => [e.data.id, e.data]))
    expect(perId.get('th').procesGap).toBe(true)
    expect(perId.get('ab').procesGap).toBeUndefined() // undefined, niet false (CY-selector-conventie)
    expect(perId.get('vv').procesGap).toBeUndefined()
  })

  // ── LI038 gate 1 v2 — gekozen proces = label, geen slot-op-de-keuze ─────────────────────────
  it('v2 — heropenen ná een keuze biedt de VOLLEDIGE lijst aan; het diagram blijft staan', async () => {
    const w = mountDiagram()
    await flushPromises()
    // Kies via het echte zoekveld (focus → optie-mousedown, zoals de gebruiker).
    const input = w.find('[data-testid="diagram-zoek-input"]')
    await input.trigger('focus')
    await flushPromises()
    await w.find('[data-testid="diagram-zoek-optie-ab"]').trigger('mousedown')
    await flushPromises()
    expect(w.vm.centrumId).toBe('ab')
    expect(input.element.value).toBe('Aanvraag behandelen — Vergunningverlening')
    // Heropenen: de input hield focus → klik (geen focus-event) → volledige set, geen filter.
    await input.trigger('click')
    await flushPromises()
    expect(w.findAll('[role="option"]').length).toBe(PROCESSEN.length)
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'vv', 'bv', 'th'])) // diagram ongewijzigd
  })

  it('v2 — typen vervangt en filtert vers; het centrum wijzigt pas bij een NIEUWE keuze', async () => {
    const w = mountDiagram()
    await flushPromises()
    const input = w.find('[data-testid="diagram-zoek-input"]')
    await input.trigger('focus')
    await flushPromises()
    await w.find('[data-testid="diagram-zoek-optie-ab"]').trigger('mousedown')
    await flushPromises()
    // Typen (vervangt de voorgevulde tekst) → vers filteren; het diagram blijft op 'ab'.
    vi.useFakeTimers()
    await input.setValue('burger')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await flushPromises()
    expect(w.vm.centrumId).toBe('ab') // focus/typen wisselt het beeld niet
    const opties = w.findAll('[role="option"]')
    expect(opties.length).toBe(1) // soepel gefilterd op het nieuwe fragment
    // Pas de nieuwe keuze wisselt het diagram.
    await w.find('[data-testid="diagram-zoek-optie-bz"]').trigger('mousedown')
    await flushPromises()
    expect(w.vm.centrumId).toBe('bz')
    expect(w.vm.zichtbareIds).toEqual(new Set(['bz', 'verh']))
  })

  it('v2 — het ×-wis-gebaar leegt het veld en toont de volledige lijst; het diagram blijft tot een nieuwe keuze', async () => {
    const w = mountDiagram()
    await flushPromises()
    const input = w.find('[data-testid="diagram-zoek-input"]')
    await input.trigger('focus')
    await flushPromises()
    await w.find('[data-testid="diagram-zoek-optie-ab"]').trigger('mousedown')
    await flushPromises()
    await w.find('[data-testid="diagram-zoek-wis"]').trigger('click')
    await flushPromises()
    expect(input.element.value).toBe('')
    expect(w.findAll('[role="option"]').length).toBe(PROCESSEN.length) // volledige lijst open
    expect(w.vm.centrumId).toBe('ab') // diagram staat nog — wisselt pas bij een nieuwe keuze
    expect(w.vm.zichtbareIds.size).toBe(4)
  })

  it('verdwijnt het centrum uit de set (bv. verwijderd), dan valt het beeld terug naar de lege staat', async () => {
    const w = mountDiagram()
    await flushPromises()
    w.vm.kiesCentrum({ id: 'verh' })
    await flushPromises()
    expect(w.vm.zichtbareIds.size).toBe(2)
    await w.setProps({ processen: PROCESSEN.filter((p) => p.id !== 'verh') })
    await flushPromises()
    expect(w.vm.zichtbareIds.size).toBe(0)
    expect(w.find('[data-testid="diagram-leeg"]').exists()).toBe(true)
  })
})
