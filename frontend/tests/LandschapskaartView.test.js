/** Tests — LandschapskaartView (ADR-025, overlay-layout; Ego- + Impact-modus). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('@/api', () => ({ api: { landschapskaart: { haalGrafdata: vi.fn() } } }))

import { api } from '@/api'
import LandschapskaartView from '@modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue'

const GRAF = () => ({
  nodes: [
    { id: 'a1', naam: 'App1', element_type: 'applicatie', laag: 'application', lifecycle_status: 'geblokkeerd' },
    { id: 'a2', naam: 'App2', element_type: 'applicatie', laag: 'application', lifecycle_status: 'migratieklaar' },
    { id: 'p1', naam: 'Org', element_type: 'partij', laag: 'business', soort: 'organisatie' },
    { id: 'k1', naam: 'Contract', element_type: 'contract', laag: 'business' },
  ],
  edges: [
    { bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
    { bron_id: 'a1', doel_id: 'k1', relatietype: 'association', label: 'valt onder', ring: 'contracten' },
    { bron_id: 'p1', doel_id: 'a1', relatietype: 'roltoewijzing', label: 'Eigenaar', ring: 'beheerorganisatie' },
  ],
})

async function mountView() {
  const w = mount(LandschapskaartView)
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.landschapskaart.haalGrafdata.mockResolvedValue(GRAF())
})
afterEach(() => vi.restoreAllMocks())

describe('LandschapskaartView', () => {
  it('rendert in Ego-modus met full-bleed canvas en nodes (overlay-layout)', async () => {
    const w = await mountView()
    // SVG vult de container; modus-toggle en filterknop zweven als overlay.
    expect(w.find('[data-testid="lk-svg"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-modus-ego"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-filter-toggle"]').exists()).toBe(true)
    // Startpunt = eerste applicatie (a1) centraal; buren (a2/k1/p1) gerenderd.
    expect(w.find('[data-testid="lk-node-a1"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-node-a2"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-node-k1"]').exists()).toBe(true)
  })

  it('houdt het filterpaneel standaard ingeklapt en toggelt het via de filterknop', async () => {
    const w = await mountView()
    // Standaard dicht: geen paneel, startpunt-dropdown niet zichtbaar.
    expect(w.find('[data-testid="lk-paneel"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-startpunt"]').exists()).toBe(false)
    // Openen.
    await w.find('[data-testid="lk-filter-toggle"]').trigger('click')
    expect(w.find('[data-testid="lk-paneel"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-startpunt"]').exists()).toBe(true)
    // Weer sluiten.
    await w.find('[data-testid="lk-filter-toggle"]').trigger('click')
    expect(w.find('[data-testid="lk-paneel"]').exists()).toBe(false)
  })

  it('mapt lifecycle-status naar de node-achtergrondkleur', async () => {
    const w = await mountView()
    // a1 = geblokkeerd → #fee2e2 (lichtrood) als rect-fill.
    const rect = w.find('[data-testid="lk-node-a1"] rect')
    expect(rect.attributes('data-fill')).toBe('#fee2e2')
  })

  it('schakelt naar Impact-modus en toont de samenvatting-teller als overlay', async () => {
    const w = await mountView()
    await w.find('[data-testid="lk-modus-impact"]').trigger('click')
    await flushPromises()
    const samenvatting = w.find('[data-testid="impact-samenvatting"]')
    expect(samenvatting.exists()).toBe(true)
    expect(samenvatting.text()).toBe('0 in set · 0 raakvlakken · 0 grensoverschrijdende koppelingen')
  })

  it('telt set/raakvlakken/grensoverschrijdend bij selectie in Impact-modus', async () => {
    const w = await mountView()
    await w.find('[data-testid="lk-modus-impact"]').trigger('click')
    await flushPromises()
    // Migratieset-chips zitten in het filterpaneel → eerst openen.
    await w.find('[data-testid="lk-filter-toggle"]').trigger('click')
    await w.find('[data-testid="lk-migratie-a1"]').setValue(true)
    await flushPromises()
    // a1 in de set; flow a1→a2 wordt grensoverschrijdend en a2 een raakvlak.
    expect(w.find('[data-testid="impact-samenvatting"]').text()).toBe('1 in set · 1 raakvlakken · 1 grensoverschrijdende koppelingen')
  })

  it('toont een lege staat als de API geen nodes teruggeeft', async () => {
    api.landschapskaart.haalGrafdata.mockResolvedValueOnce({ nodes: [], edges: [] })
    const w = await mountView()
    expect(w.find('[data-testid="lk-leeg"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-svg"]').exists()).toBe(false)
  })
})
