/** Tests — ContractDetail (§1 deelcontracten, §2 gekoppelde applicaties). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    contracten: { haal: vi.fn(), deelcontracten: vi.fn(), applicaties: vi.fn(), verwijder: vi.fn() },
    // ADR-024 slice 2b — VerantwoordelijkheidSectie (náást de leverancier-weergave).
    roltoewijzingen: {
      lijst: vi.fn(() => Promise.resolve([])),
      rollen: vi.fn(() => Promise.resolve([])),
      maak: vi.fn(),
      verwijder: vi.fn(),
    },
    partijen: { lijst: vi.fn(() => Promise.resolve({ items: [] })) },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ContractDetail from '@modules/bwb_ontvlechting/frontend/views/ContractDetail.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/contracten', name: 'contract-lijst', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: ContractDetail, props: true },
      { path: '/contracten/:id/bewerken', name: 'contract-bewerken', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push('/contracten/c1')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ContractDetail, {
    props: { id: 'c1' },
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router] },
  })
  await flushPromises()
  return w
}

const _contract = (extra = {}) => ({
  id: 'c1', contractnaam: 'Mantel X', contracttype: 'mantelcontract', leverancier_naam: 'Acme BV',
  mantelcontract_id: null, extern_contract_id: null, leverancier_contract_id: null,
  begindatum: null, einddatum: null, vernieuwingsdatum: null,
  dekking: [], kostenmodel: [], omschrijving: null, toelichting: null, ...extra,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.contracten.deelcontracten.mockResolvedValue([])
  api.contracten.applicaties.mockResolvedValue([])
})
afterEach(() => vi.restoreAllMocks())

describe('ContractDetail — parent-context in header (valt onder)', () => {
  it('toont de "Valt onder"-subtitel met mantelcontract-link bij een deelcontract', async () => {
    api.contracten.haal.mockImplementation((id) =>
      Promise.resolve(
        id === 'c1'
          ? _contract({ id: 'c1', contractnaam: 'Deel A', contracttype: 'los_contract', mantelcontract_id: 'm9' })
          : _contract({ id: 'm9', contractnaam: 'Mantel Groot', mantelcontract_id: null }),
      ),
    )
    const w = await mountDetail()
    expect(w.find('[data-testid="contract-valt-onder"]').exists()).toBe(true)
    const link = w.find('[data-testid="valt-onder-link"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toContain('Mantel Groot')
  })

  it('verbergt de "Valt onder"-subtitel zonder mantelcontract', async () => {
    api.contracten.haal.mockResolvedValue(_contract())  // mantelcontract_id: null
    const w = await mountDetail()
    expect(w.find('[data-testid="contract-valt-onder"]').exists()).toBe(false)
  })
})

describe('ContractDetail — §1 deelcontracten', () => {
  it('toont de deelcontracten-sectie met dekking-Tags en rij-navigatie (mantel)', async () => {
    api.contracten.haal.mockResolvedValue(_contract())
    api.contracten.deelcontracten.mockResolvedValue([
      { id: 'd1', contractnaam: 'Deel A', begindatum: '2026-01-01', einddatum: null, dekking: [{ optie_sleutel: 'hosting', label: 'Hosting', actief: true }] },
    ])
    const w = await mountDetail()
    expect(w.find('[data-testid="deelcontracten-sectie"]').exists()).toBe(true)
    const tabel = w.find('[data-testid="deelcontracten-tabel"]')
    expect(tabel.text()).toContain('Deel A')
    expect(tabel.text()).toContain('Hosting') // dekking-label als Tag
    expect(w.find('[data-testid="deel-link"]').attributes('href')).toContain('/contracten/d1')
  })

  it('geen deelcontracten-sectie bij een niet-mantelcontract', async () => {
    api.contracten.haal.mockResolvedValue(_contract({ contracttype: 'los_contract' }))
    const w = await mountDetail()
    expect(w.find('[data-testid="deelcontracten-sectie"]').exists()).toBe(false)
    expect(api.contracten.deelcontracten).not.toHaveBeenCalled()
  })

  it('lege-staat: "Geen deelcontracten."', async () => {
    api.contracten.haal.mockResolvedValue(_contract())
    const w = await mountDetail()
    expect(w.find('[data-testid="deelcontracten-leeg"]').exists()).toBe(true)
  })
})

describe('ContractDetail — §2 gekoppelde applicaties', () => {
  it('rendert applicatie, rol-label en lifecycle-Tag, met rij-navigatie', async () => {
    api.contracten.haal.mockResolvedValue(_contract({ contracttype: 'los_contract' }))
    api.contracten.applicaties.mockResolvedValue([
      { koppeling_id: 'k1', applicatie_id: 'a1', applicatie_naam: 'Zaaksysteem', lifecycle_status: 'geblokkeerd', relatie_rol: 'valt_onder', relatie_rol_label: 'Valt onder / aanschaf' },
    ])
    const w = await mountDetail()
    const tabel = w.find('[data-testid="gekoppelde-apps-tabel"]')
    expect(tabel.text()).toContain('Zaaksysteem')
    expect(tabel.text()).toContain('Valt onder / aanschaf')
    expect(tabel.text()).toContain('Geblokkeerd') // lifecycle-label (labels.js)
    expect(w.find('[data-testid="app-link"]').attributes('href')).toContain('/componenten/a1')
  })

  it('lege-staat: "Geen gekoppelde applicaties."', async () => {
    api.contracten.haal.mockResolvedValue(_contract({ contracttype: 'los_contract' }))
    const w = await mountDetail()
    expect(w.find('[data-testid="gekoppelde-apps-leeg"]').exists()).toBe(true)
  })
})

describe('ContractDetail — ADR-024 slice 2b verantwoordelijkheden', () => {
  it('toont de Verantwoordelijkheden-sectie náást de leverancier-weergave', async () => {
    api.contracten.haal.mockResolvedValue(_contract({ contracttype: 'los_contract' }))
    const w = await mountDetail()
    expect(w.find('[data-testid="vw-sectie"]').exists()).toBe(true)
    expect(api.roltoewijzingen.lijst).toHaveBeenCalledWith({ object_id: 'c1' })
  })
})
