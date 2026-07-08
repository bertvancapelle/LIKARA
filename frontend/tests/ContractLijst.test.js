/** Tests — ContractLijst (module-view via @modules). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  api: {
    contracten: { lijst: vi.fn() },
    leveranciers: { lijst: vi.fn() },
    contractconfig: { opties: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ContractLijst from '@modules/bwb_ontvlechting/frontend/views/ContractLijst.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/contracten', name: 'contract-lijst', component: ContractLijst },
      { path: '/contracten/nieuw', name: 'contract-nieuw', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountLijst({ rollen = ['medewerker'] } = {}) {
  const router = maakRouter()
  await router.push('/contracten')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ContractLijst, { global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] } })
  await flushPromises()
  return w
}

const _con = (naam, id) => ({
  id, contractnaam: naam, contracttype: 'los_contract',
  leverancier_id: 'l1', leverancier_naam: 'Acme BV', mantelcontract_id: null,
  begindatum: '2026-01-01', einddatum: null, vernieuwingsdatum: null,
})

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // lijststaat (useLijstStaat) mag niet tussen tests lekken
  api.leveranciers.lijst.mockResolvedValue({ items: [{ id: 'l1', naam: 'Acme BV' }], volgende_cursor: null })
  api.contractconfig.opties.mockResolvedValue({
    dekking: [{ optie_sleutel: 'hosting', label: 'Hosting', volgorde: 0 }],
    kostenmodel: [{ optie_sleutel: 'volume', label: 'Volumemodel', volgorde: 0 }],
    relatie_rol: [],
  })
})
afterEach(() => vi.restoreAllMocks())

describe('ContractLijst', () => {
  it('rendert contracten met type-label en leverancier', async () => {
    api.contracten.lijst.mockResolvedValueOnce({ items: [_con('Onderhoud 2026', 'c1')], volgende_cursor: null })
    const w = await mountLijst()
    expect(w.text()).toContain('Onderhoud 2026')
    expect(w.text()).toContain('Acme BV')
    expect(w.text()).toContain('Los contract') // labels.js
  })

  it('"Meer laden" pagineert met de cursor', async () => {
    api.contracten.lijst
      .mockResolvedValueOnce({ items: [_con('Eerste', 'c1')], volgende_cursor: 'cur-1' })
      .mockResolvedValueOnce({ items: [_con('Tweede', 'c2')], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="meer-laden"]').trigger('click')
    await flushPromises()
    expect(api.contracten.lijst).toHaveBeenLastCalledWith({ limit: 25, after: 'cur-1' })
  })

  it('dekking-filter → refetch met dekking-sleutel + cursor-reset', async () => {
    api.contracten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-dekking"]').setValue('hosting')
    await flushPromises()
    expect(api.contracten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ dekking: 'hosting', after: undefined }))
  })

  it('lege status + foutstatus', async () => {
    api.contracten.lijst.mockResolvedValueOnce({ items: [], volgende_cursor: null })
    expect((await mountLijst()).find('[data-testid="lijst-leeg"]').exists()).toBe(true)
    api.contracten.lijst.mockRejectedValueOnce(new Error('x'))
    expect((await mountLijst()).find('[data-testid="lijst-fout"]').attributes('role')).toBe('alert')
  })
})

describe('ContractLijst — lijststaat behouden bij terugnavigeren (useLijstStaat)', () => {
  it('herstelt de bewaarde lijststaat end-to-end in de eerste API-aanroep', async () => {
    sessionStorage.setItem(
      'lijst-state:contract-lijst',
      JSON.stringify({
        filterLeverancier: 'l1',
        filterType: 'los_contract',
        filterDekking: 'hosting',
        filterZoek: 'onderhoud',
        sortVeld: 'contractnaam',
        sortRichting: 'desc',
      }),
    )
    api.contracten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst()
    // V012-les: bewijs de keten — de herstelde stand belandt in de api-call.
    expect(api.contracten.lijst).toHaveBeenCalledWith(
      expect.objectContaining({
        leverancierId: 'l1',
        contracttype: 'los_contract',
        dekking: 'hosting',
        zoek: 'onderhoud',
        sort: 'contractnaam',
        order: 'desc',
      }),
    )
  })

  it('pruned bewaarde bron-sleutels die niet (meer) bestaan (geen onzichtbaar filter)', async () => {
    sessionStorage.setItem(
      'lijst-state:contract-lijst',
      JSON.stringify({ filterLeverancier: 'weg-leverancier', filterDekking: 'weg-dekking', filterZoek: 'onderhoud' }),
    )
    api.contracten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst()
    const params = api.contracten.lijst.mock.calls[0][0]
    expect(params.leverancierId).toBeUndefined()
    expect(params.dekking).toBeUndefined()
    expect(params.zoek).toBe('onderhoud') // geldige velden blijven hersteld
  })

  it('bewaart een wijziging ná herstel (beforeunload-pad = F5-gedrag)', async () => {
    api.contracten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-dekking"]').setValue('hosting')
    await flushPromises()
    window.dispatchEvent(new Event('beforeunload'))
    const bewaard = JSON.parse(sessionStorage.getItem('lijst-state:contract-lijst'))
    expect(bewaard.filterDekking).toBe('hosting')
    w.unmount()
  })
})
