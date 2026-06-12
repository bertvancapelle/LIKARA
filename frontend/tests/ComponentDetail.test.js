/** Tests — ComponentDetail (detail + Opbouw + Contracten; ADR-021 Fase D, CD054b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    componenten: {
      haal: vi.fn(),
      structuur: vi.fn(),
      contracten: vi.fn(),
      opties: vi.fn(),
      verwijder: vi.fn(),
    },
    componentStructuren: { maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
    componentContracten: { maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
    contractconfig: { opties: vi.fn() },
    contracten: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import ComponentDetail from '@modules/bwb_ontvlechting/frontend/views/ComponentDetail.vue'
import { useAuthStore } from '@/store/auth'

const ID = 'db-1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/componenten/:id', name: 'component-detail', component: ComponentDetail, props: true },
      { path: '/componenten/:id/bewerken', name: 'component-bewerken', component: { template: '<div/>' } },
      { path: '/componenten', name: 'component-lijst', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push('/componenten/db-1')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ComponentDetail, {
    props: { id: ID },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

const _component = (over = {}) => ({
  id: ID,
  naam: 'Oracle FIN-DB',
  componenttype: 'database',
  componenttype_label: 'Database',
  hostingmodel: 'on_premise',
  eigenaar_organisatie: 'Gemeente Veldendam',
  eigenaar_naam: null,
  leverancier: 'Oracle',
  beschrijving: null,
  heeft_applicatie_subtype: false,
  ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.componenten.haal.mockResolvedValue(_component())
  api.componenten.structuur.mockResolvedValue({
    draait_op: [],
    gebruikt_door: [
      {
        structuur_id: 's-1',
        component_id: 'app-9',
        naam: 'Belastingsysteem',
        componenttype: 'applicatie',
        relatietype: 'draait_op',
        relatietype_label: 'Draait op',
        omschrijving: null,
      },
    ],
  })
  api.componenten.contracten.mockResolvedValue([
    {
      koppeling_id: 'k-1',
      contract_id: 'c-1',
      contractnaam: 'Oracle licentie',
      contracttype: 'los_contract',
      leverancier_naam: 'Oracle',
      relatie_rol: 'valt_onder',
      relatie_rol_label: 'Valt onder',
      begindatum: null,
      einddatum: null,
    },
  ])
  api.componenten.opties.mockResolvedValue({ componenttype: [], structuurrelatie_type: [] })
  api.contractconfig.opties.mockResolvedValue({ relatie_rol: [] })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ComponentDetail', () => {
  it('toont velden + type-label en de Opbouw-sectie (beide richtingen)', async () => {
    const { w } = await mountDetail()
    expect(w.find('#detail-titel').text()).toContain('Oracle FIN-DB')
    expect(w.find('[data-testid="detail-type"]').text()).toContain('Database')
    // Opbouw (StructuurSectie-child): "Gebruikt door" toont Belastingsysteem.
    expect(w.find('[data-testid="st-tabel-gebruikt-door"]').text()).toContain('Belastingsysteem')
  })

  it('toont de Contracten-sectie (gegeneraliseerde ContractSectie) met de koppeling', async () => {
    const { w } = await mountDetail()
    expect(w.find('[data-testid="ct-tabel"]').text()).toContain('Oracle licentie')
    expect(api.componenten.contracten).toHaveBeenCalledWith(ID)
  })

  it('verwijderen met 409 IN_GEBRUIK wordt afgevangen (blijft op het detail)', async () => {
    api.componenten.verwijder.mockRejectedValueOnce({ status: 409, code: 'IN_GEBRUIK', message: 'In gebruik.' })
    const { w, router } = await mountDetail()
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.componenten.verwijder).toHaveBeenCalledWith(ID)
    expect(router.currentRoute.value.name).toBe('component-detail')
  })

  it('verwijderen lukt → navigeert naar de lijst', async () => {
    api.componenten.verwijder.mockResolvedValueOnce({})
    const { w, router } = await mountDetail()
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('component-lijst')
  })

  it('applicatie-subtype: hint naar ApplicatieDetail, geen bewerk-/verwijderknop', async () => {
    api.componenten.haal.mockResolvedValue(
      _component({ componenttype: 'applicatie', componenttype_label: 'Applicatie', heeft_applicatie_subtype: true }),
    )
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detail-subtype-hint"]').exists()).toBe(true)
    expect(w.find('[data-testid="bewerken-knop"]').exists()).toBe(false)
    expect(w.find('[data-testid="verwijder-knop"]').exists()).toBe(false)
  })
})
