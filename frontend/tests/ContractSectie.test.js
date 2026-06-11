/** Tests — ContractSectie (app↔contract-koppeling in ApplicatieDetail). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    applicaties: { contracten: vi.fn() },
    contractconfig: { opties: vi.fn() },
    contracten: { lijst: vi.fn() },
    applicatieContracten: { maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ContractSectie from '@modules/bwb_ontvlechting/frontend/views/ContractSectie.vue'

const APP = 'app-1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } }],
  })
}

async function mountSectie({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push('/contracten/c1') // initiële navigatie → isReady resolvet
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ContractSectie, {
    props: { applicatieId: APP },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

const _rij = () => ({
  koppeling_id: 'k1', contract_id: 'c1', contractnaam: 'Contract A',
  contracttype: 'los_contract', leverancier_id: 'l1', leverancier_naam: 'Acme',
  relatie_rol: 'valt_onder', relatie_rol_label: 'Valt onder / aanschaf',
})

beforeEach(() => {
  vi.clearAllMocks()
  api.applicaties.contracten.mockResolvedValue([_rij()])
  api.contractconfig.opties.mockResolvedValue({
    dekking: [], kostenmodel: [],
    relatie_rol: [
      { optie_sleutel: 'valt_onder', label: 'Valt onder / aanschaf' },
      { optie_sleutel: 'onderhoud', label: 'Onderhoud' },
    ],
  })
  api.contracten.lijst.mockResolvedValue({
    items: [
      { id: 'c1', contractnaam: 'Contract A', leverancier_naam: 'Acme' },
      { id: 'c2', contractnaam: 'Contract B', leverancier_naam: 'Globex' },
    ],
    volgende_cursor: null,
  })
})
afterEach(() => vi.restoreAllMocks())

describe('ContractSectie', () => {
  it('rendert gekoppelde contracten', async () => {
    const w = await mountSectie()
    expect(w.find('[data-testid="ct-tabel"]').exists()).toBe(true)
    expect(w.text()).toContain('Contract A')
  })

  it('rol-gating: viewer geen koppel-knop, geen rol-select, geen ontkoppelen', async () => {
    const w = await mountSectie({ rollen: ['viewer'] })
    expect(w.find('[data-testid="ct-koppelen"]').exists()).toBe(false)
    expect(w.find('[data-testid="ct-rol-k1"]').exists()).toBe(false)
    expect(w.find('[data-testid="ct-ontkoppel-k1"]').exists()).toBe(false)
  })

  it('koppelen vereist een rol (geen API-call zonder rol)', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="ct-koppelen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="ct-veld-contract"]').setValue('c2')
    await w.find('[data-testid="ct-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="ct-fout-rol"]').exists()).toBe(true)
    expect(api.applicatieContracten.maak).not.toHaveBeenCalled()
  })

  it('koppelt met contract+rol en ververst de sectie', async () => {
    api.applicatieContracten.maak.mockResolvedValueOnce({ id: 'k2' })
    const w = await mountSectie()
    const voor = api.applicaties.contracten.mock.calls.length
    await w.find('[data-testid="ct-koppelen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="ct-veld-contract"]').setValue('c2')
    await w.find('[data-testid="ct-veld-rol"]').setValue('onderhoud')
    await w.find('[data-testid="ct-form"]').trigger('submit')
    await flushPromises()
    expect(api.applicatieContracten.maak).toHaveBeenCalledWith({ applicatie_id: APP, contract_id: 'c2', relatie_rol: 'onderhoud' })
    expect(api.applicaties.contracten.mock.calls.length).toBe(voor + 1) // refetch
  })

  it('409 KOPPELING_BESTAAT: geen refetch', async () => {
    api.applicatieContracten.maak.mockRejectedValueOnce({ status: 409, code: 'KOPPELING_BESTAAT', message: 'al gekoppeld' })
    const w = await mountSectie()
    const voor = api.applicaties.contracten.mock.calls.length
    await w.find('[data-testid="ct-koppelen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="ct-veld-contract"]').setValue('c2')
    await w.find('[data-testid="ct-veld-rol"]').setValue('onderhoud')
    await w.find('[data-testid="ct-form"]').trigger('submit')
    await flushPromises()
    expect(api.applicatieContracten.maak).toHaveBeenCalledTimes(1)
    expect(api.applicaties.contracten.mock.calls.length).toBe(voor)
  })

  it('rol-wijzigen via inline select → werkBij + refetch', async () => {
    api.applicatieContracten.werkBij.mockResolvedValueOnce({})
    const w = await mountSectie()
    const voor = api.applicaties.contracten.mock.calls.length
    await w.find('[data-testid="ct-rol-k1"]').setValue('onderhoud')
    await flushPromises()
    expect(api.applicatieContracten.werkBij).toHaveBeenCalledWith('k1', { relatie_rol: 'onderhoud' })
    expect(api.applicaties.contracten.mock.calls.length).toBe(voor + 1)
  })

  it('ontkoppelen via bevestiging → verwijder + refetch', async () => {
    api.applicatieContracten.verwijder.mockResolvedValueOnce(null)
    const w = await mountSectie()
    const voor = api.applicaties.contracten.mock.calls.length
    await w.find('[data-testid="ct-ontkoppel-k1"]').trigger('click')
    await w.find('[data-testid="ct-ontkoppel-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.applicatieContracten.verwijder).toHaveBeenCalledWith('k1')
    expect(api.applicaties.contracten.mock.calls.length).toBe(voor + 1)
  })
})

describe('ContractSectie — §3 valt-onder-samenvatting', () => {
  it('één valt_onder-koppeling toont de samenvatting met link', async () => {
    const w = await mountSectie()
    const s = w.find('[data-testid="ct-valt-onder"]')
    expect(s.text()).toContain('Valt onder:')
    expect(s.text()).toContain('Contract A')
  })

  it('geen koppeling met rol valt_onder → expliciete melding', async () => {
    api.applicaties.contracten.mockResolvedValueOnce([
      { ..._rij(), relatie_rol: 'onderhoud', relatie_rol_label: 'Onderhoud' },
    ])
    const w = await mountSectie()
    expect(w.find('[data-testid="ct-valt-onder"]').text()).toContain('Geen valt-onder-contract geregistreerd')
  })

  it('meerdere valt_onder-koppelingen → alle getoond (conventie A)', async () => {
    api.applicaties.contracten.mockResolvedValueOnce([
      { ..._rij(), koppeling_id: 'k1', contract_id: 'c1', contractnaam: 'Contract A' },
      { ..._rij(), koppeling_id: 'k2', contract_id: 'c2', contractnaam: 'Contract B' },
    ])
    const w = await mountSectie()
    const t = w.find('[data-testid="ct-valt-onder"]').text()
    expect(t).toContain('Contract A')
    expect(t).toContain('Contract B')
  })
})
