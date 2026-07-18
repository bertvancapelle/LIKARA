/** Tests — SignaleringView (ADR-035 Slice 2): twee tabs; Registratiegaten gegroepeerd per ernst. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.mock('@/api', () => ({
  api: {
    signalering: { registratiegaten: vi.fn() },
    signalen: { plaatsing: vi.fn() }, // PlaatsingSignalenView (ingebedde tab) roept dit op mount aan
    componentNormen: { verschovenLat: vi.fn() }, // slice 4a — de verschoven-lat-sectie
  },
}))

import { api } from '@/api'
import SignaleringView from '@/views/SignaleringView.vue'

const GATEN = () => ({
  kritiek: {
    component_zonder_eigenaar: [{ id: 'c1', naam: 'Zaaksysteem', lifecycle_status: 'concept' }],
    component_zonder_verantwoordelijke: [],
    // ADR-028 slice 4 — nieuw kritiek signaal.
    biv_classificatie_onvolledig: [{ id: 'c3', naam: 'BRP', lifecycle_status: 'in_inventarisatie' }],
  },
  aandacht: {
    component_zonder_gebruikersgroep: [],
    component_geisoleerd: [{ id: 'c2', naam: 'Solo' }],
    contract_zonder_component: [{ id: 'k1', naam: 'Contract X' }],
    gebruikersgroep_zonder_organisatie: [{ id: 'g1', naam: 'Burgerzaken' }],
    object_zonder_roltoewijzing: [{ id: 'k1', naam: 'Contract X', entiteit_type: 'contract' }],
  },
})

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountView() {
  const router = maakRouter()
  await router.push('/')
  await router.isReady()
  const w = mount(SignaleringView, { global: { plugins: [router] } })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.signalen.plaatsing.mockResolvedValue([])
  api.signalering.registratiegaten.mockResolvedValue(GATEN())
  api.componentNormen.verschovenLat.mockResolvedValue([])
})
afterEach(() => vi.restoreAllMocks())

describe('SignaleringView', () => {
  it('toont twee tabs en laadt de registratiegaten op mount', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="sig-tab-registratiegaten"]').exists()).toBe(true)
    expect(w.find('[data-testid="sig-tab-plaatsing"]').exists()).toBe(true)
    expect(api.signalering.registratiegaten).toHaveBeenCalled()
  })

  it('groepeert per ernst: kritiek (component zonder eigenaar) + aandacht (geïsoleerd/contract)', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="sig-ernst-kritiek"]').exists()).toBe(true)
    expect(w.find('[data-testid="sig-ernst-aandacht"]').exists()).toBe(true)
    expect(w.find('[data-testid="sig-component_zonder_eigenaar-c1"]').text()).toContain('Zaaksysteem')
    expect(w.find('[data-testid="sig-component_geisoleerd-c2"]').exists()).toBe(true)
    expect(w.find('[data-testid="sig-contract_zonder_component-k1"]').exists()).toBe(true)
    // lege groep rendert geen sectie
    expect(w.find('[data-testid="sig-groep-component_zonder_verantwoordelijke"]').exists()).toBe(false)
  })

  it('ADR-028: "BIV-classificatie onvolledig" staat in de kritieke sectie met teller + component-doorklik', async () => {
    const w = await mountView()
    const groep = w.find('[data-testid="sig-groep-biv_classificatie_onvolledig"]')
    expect(groep.exists()).toBe(true)
    expect(groep.text()).toContain('BIV-classificatie onvolledig')
    expect(groep.text()).toContain('(1)') // teller
    // doorklik naar het component-detail
    expect(w.find('[data-testid="sig-biv_classificatie_onvolledig-c3"] a').attributes('href')).toContain('/componenten/c3')
  })

  it('contract-link wijst naar contract-detail; gebruikersgroep-rij heeft geen link', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="sig-contract_zonder_component-k1"] a').attributes('href')).toContain('/contracten/k1')
    // gebruikersgroep zonder organisatie → geen <a> (geen detail-pagina)
    expect(w.find('[data-testid="sig-gebruikersgroep_zonder_organisatie-g1"] a').exists()).toBe(false)
  })

  it('alles leeg → groene "geen registratiegaten"-staat', async () => {
    api.signalering.registratiegaten.mockResolvedValue({ kritiek: { component_zonder_eigenaar: [], component_zonder_verantwoordelijke: [] }, aandacht: {} })
    const w = await mountView()
    expect(w.find('[data-testid="sig-leeg"]').exists()).toBe(true)
  })

  it('tab "Plaatsing" toont de bestaande plaatsingssignalen-view (ingebed)', async () => {
    const w = await mountView()
    await w.find('[data-testid="sig-tab-plaatsing"]').trigger('click')
    expect(w.find('[data-testid="sig-panel-plaatsing"]').exists()).toBe(true)
    expect(api.signalen.plaatsing).toHaveBeenCalled()
  })

  it('slice 4a — verschoven lat: eigen neutrale sectie met feit, aantal en component-doorklik', async () => {
    api.componentNormen.verschovenLat.mockResolvedValue([
      { feit: 'bedoeling', aantal: 2, componenten: [{ id: 'c1', naam: 'Archiefbeheer' }, { id: 'c2', naam: 'DMS' }] },
    ])
    const w = await mountView()
    const sec = w.find('[data-testid="sig-verschoven-lat"]')
    expect(sec.exists()).toBe(true)
    expect(sec.text()).toContain('De lat is verschoven')
    const rij = w.find('[data-testid="sig-verschoven-bedoeling"]')
    expect(rij.text()).toContain('Bedoeling (migratiepad)')
    expect(rij.text()).toContain('2 systemen')
    expect(w.find('[data-testid="sig-verschoven-bedoeling-c1"] a').attributes('href')).toContain('/componenten/c1')
  })

  it('slice 4a — geen verschoven lat → sectie afwezig', async () => {
    const w = await mountView() // default mock = []
    expect(w.find('[data-testid="sig-verschoven-lat"]').exists()).toBe(false)
  })

  it('slice 4b — de werkvoorraadregel toont wanneer/door wie de lat verschoof (uit audit)', async () => {
    api.componentNormen.verschovenLat.mockResolvedValue([
      { feit: 'bedoeling', aantal: 1, componenten: [{ id: 'c1', naam: 'Archiefbeheer' }], verschoven_door: 'J. de Vries', verschoven_op: '2026-07-18T10:00:00+00:00' },
    ])
    const w = await mountView()
    const meta = w.find('[data-testid="sig-verschoven-meta-bedoeling"]')
    expect(meta.exists()).toBe(true)
    expect(meta.text()).toContain('J. de Vries')
  })
})
