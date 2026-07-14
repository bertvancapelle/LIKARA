/** Tests — WerkvoorraadPlekView (ADR-051 gate 3, venster 2: de centrale werkvoorraad per plek).
 * Teller en lijst delen één filterwaarheid (uit `plek_standen`); "nog niet beoordeeld" is een
 * eigen, vindbare stand (filter), gebundeld per systeem. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('@/api', () => ({
  api: {
    bedrijfsfuncties: { lijst: vi.fn() },
    functievervullingen: { standen: vi.fn(), dekking: vi.fn() },
  },
}))

import { api } from '@/api'
import WerkvoorraadPlekView from '@modules/bwb_ontvlechting/frontend/views/WerkvoorraadPlekView.vue'

const _f = (id, naam) => ({ id, naam, ouder_ids: [], vervallen: false })

beforeEach(() => {
  vi.clearAllMocks()
  api.bedrijfsfuncties.lijst.mockResolvedValue({
    items: [_f('tz', 'Toezicht'), _f('mi', 'Milieu'), _f('uv', 'Uitvoering')], volgende_cursor: null,
  })
  api.functievervullingen.standen.mockResolvedValue({ plekken: [], tellers: {} })
  api.functievervullingen.dekking.mockResolvedValue([])
})
afterEach(() => vi.restoreAllMocks())

async function mountView() {
  const w = mount(WerkvoorraadPlekView)
  await flushPromises()
  return w
}

describe('WerkvoorraadPlekView', () => {
  it('teller en lijst delen één filterwaarheid (gat + via_boven uit de gedeelde tellers)', async () => {
    api.functievervullingen.standen.mockResolvedValue({
      plekken: [
        { functie_id: 'tz', ouder_functie_id: 'mi', stand: 'gat', via_functie_id: null, via_aantal: 0 },
        { functie_id: 'tz', ouder_functie_id: 'uv', stand: 'via_boven', via_functie_id: 'uv', via_aantal: 1 },
      ],
      tellers: { gat: 1, via_boven: 1, hier: 5, niets: 2, zonder_oordeel: 3 },
    })
    const w = await mountView()
    expect(w.find('[data-testid="werkvoorraad-teller"]').text()).toContain('2 plekken vragen aandacht')
    // De lijst toont exact die twee plekken, met echte namen + de stand-cue.
    expect(w.find('[data-testid="werkvoorraad-rij-tz|mi"]').text()).toContain('nog niet vastgelegd waarmee')
    expect(w.find('[data-testid="werkvoorraad-rij-tz|uv"]').text()).toContain('ondersteund via Uitvoering — hier niet bevestigd')
    expect(w.findAll('[data-testid^="werkvoorraad-rij-"]').length).toBe(2) // teller == lijst
  })

  it('"nog niet beoordeeld" is een eigen filter, gebundeld per systeem', async () => {
    api.functievervullingen.standen.mockResolvedValue({ plekken: [], tellers: { gat: 0, via_boven: 0, zonder_oordeel: 2 } })
    api.functievervullingen.dekking.mockResolvedValue([
      { functie_id: 'tz', ouder_functie_id: 'mi', herkomst: 'grof', componenten: [{ vervulling_id: 'v1', component_id: 'c1', component_naam: 'G-schijf', oordeel: null }] },
      { functie_id: 'tz', ouder_functie_id: 'uv', herkomst: 'fijn', componenten: [{ vervulling_id: 'v2', component_id: 'c1', component_naam: 'G-schijf', oordeel: null }] },
    ])
    const w = await mountView()
    expect(w.find('[data-testid="werkvoorraad-teller"]').text()).toContain('0 plekken vragen')
    // Filter dicht → geen lijst; open → de bundeling per systeem (G-schijf draagt 2 plekken).
    expect(w.find('[data-testid="werkvoorraad-onbeoordeeld-lijst"]').exists()).toBe(false)
    await w.find('[data-testid="werkvoorraad-filter-onbeoordeeld"]').setValue(true)
    expect(w.find('[data-testid="werkvoorraad-onbeoordeeld-G-schijf"]').text()).toContain('draagt 2 plekken zonder oordeel')
  })
})
