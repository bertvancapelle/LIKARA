/** Tests — SignaleringView (ADR-035 Slice 2): twee tabs; Registratiegaten gegroepeerd per ernst. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

vi.mock('@/api', () => ({
  api: {
    signalering: { registratiegaten: vi.fn() },
    signalen: { plaatsing: vi.fn() }, // PlaatsingSignalenView (ingebedde tab) roept dit op mount aan
  },
}))

import { api } from '@/api'
import SignaleringView from '@/views/SignaleringView.vue'

const GATEN = () => ({
  kritiek: {
    component_zonder_eigenaar: [{ id: 'c1', naam: 'Zaaksysteem', lifecycle_status: 'concept' }],
    component_zonder_verantwoordelijke: [],
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
})
