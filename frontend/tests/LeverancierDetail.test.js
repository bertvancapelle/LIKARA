/** Tests — LeverancierDetail (verwijderen; 409 IN_GEBRUIK blijft op detail). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { leveranciers: { haal: vi.fn(), verwijder: vi.fn() }, contracten: { lijst: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import LeverancierDetail from '@modules/bwb_ontvlechting/frontend/views/LeverancierDetail.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/leveranciers', name: 'leverancier-lijst', component: { template: '<div/>' } },
      { path: '/leveranciers/:id', name: 'leverancier-detail', component: LeverancierDetail, props: true },
      { path: '/leveranciers/:id/bewerken', name: 'leverancier-bewerken', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push('/leveranciers/l1')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(LeverancierDetail, {
    props: { id: 'l1' },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

beforeEach(() => {
  vi.clearAllMocks()
  api.leveranciers.haal.mockResolvedValue({ id: 'l1', naam: 'Acme BV', plaats: 'Tiel' })
  api.contracten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('LeverancierDetail', () => {
  it('verwijdert en navigeert naar de lijst bij succes', async () => {
    api.leveranciers.verwijder.mockResolvedValueOnce(null)
    const { w, router } = await mountDetail()
    const push = vi.spyOn(router, 'push')
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.leveranciers.verwijder).toHaveBeenCalledWith('l1')
    expect(push).toHaveBeenCalledWith({ name: 'leverancier-lijst' })
  })

  it('409 IN_GEBRUIK: blijft op detail (geen navigatie)', async () => {
    api.leveranciers.verwijder.mockRejectedValueOnce({ status: 409, code: 'IN_GEBRUIK', message: 'heeft contracten' })
    const { w, router } = await mountDetail()
    const push = vi.spyOn(router, 'push')
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.leveranciers.verwijder).toHaveBeenCalledTimes(1)
    expect(push).not.toHaveBeenCalled() // geen navigatie weg van het detail
  })

  it('rol-gating: viewer ziet geen verwijder-knop', async () => {
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="verwijder-knop"]').exists()).toBe(false)
  })
})

describe('LeverancierDetail — §4 contractenketen', () => {
  const _c = (naam, id, extra = {}) => ({
    id, contractnaam: naam, contracttype: 'los_contract', begindatum: null, einddatum: null, ...extra,
  })

  it('toont de contracten van de leverancier met type-Tag en rij-link', async () => {
    api.contracten.lijst.mockResolvedValueOnce({ items: [_c('Onderhoud 2026', 'c1')], volgende_cursor: null })
    const { w } = await mountDetail()
    expect(api.contracten.lijst).toHaveBeenCalledWith({ leverancierId: 'l1', limit: 25, after: undefined })
    expect(w.find('[data-testid="lev-contracten-tabel"]').text()).toContain('Onderhoud 2026')
    expect(w.find('[data-testid="lev-contract-link"]').attributes('href')).toContain('/contracten/c1')
  })

  it('"Meer laden" pagineert met de cursor', async () => {
    api.contracten.lijst
      .mockResolvedValueOnce({ items: [_c('Eerste', 'c1')], volgende_cursor: 'cur-1' })
      .mockResolvedValueOnce({ items: [_c('Tweede', 'c2')], volgende_cursor: null })
    const { w } = await mountDetail()
    await w.find('[data-testid="lev-contracten-meer"]').trigger('click')
    await flushPromises()
    expect(api.contracten.lijst).toHaveBeenLastCalledWith({ leverancierId: 'l1', limit: 25, after: 'cur-1' })
  })

  it('lege-staat: "Geen contracten van deze leverancier."', async () => {
    const { w } = await mountDetail()
    expect(w.find('[data-testid="lev-contracten-leeg"]').exists()).toBe(true)
  })
})
