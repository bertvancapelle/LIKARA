/** Tests — PartijDetail (ADR-024 slice 2a): aard-tag, soort, contracten-sectie alleen voor
 *  externe partij, verwijderen (409 IN_GEBRUIK blijft op detail). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { partijen: { haal: vi.fn(), verwijder: vi.fn() }, contracten: { lijst: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import PartijDetail from '@modules/bwb_ontvlechting/frontend/views/PartijDetail.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/partijen', name: 'partij-lijst', component: { template: '<div/>' } },
      { path: '/partijen/:id', name: 'partij-detail', component: PartijDetail, props: true },
      { path: '/partijen/:id/bewerken', name: 'partij-bewerken', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'], id = 'p1' } = {}) {
  const router = maakRouter()
  await router.push(`/partijen/${id}`)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(PartijDetail, {
    props: { id },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

const _partij = (over = {}) => ({
  id: 'p1', aard: 'externe_partij', naam: 'Acme BV', soort: 'leverancier',
  straat_huisnummer: null, postcode: null, plaats: 'Tiel', contactpersoon: null,
  telefoon: null, mobiel: null, email: null, omschrijving: null, ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.contracten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('PartijDetail', () => {
  it('toont naam + aard-tag + soort', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    const { w } = await mountDetail()
    expect(w.find('#partij-detail-titel').text()).toContain('Acme BV')
    expect(w.find('[data-testid="detail-aard"]').text()).toContain('Externe partij')
    expect(w.text()).toContain('leverancier')  // soort-rij
  })

  it('contracten-sectie + contractenlaad ALLEEN voor een externe partij', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'persoon', naam: 'J. de Vries', soort: null }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detail-aard"]').text()).toContain('Persoon')
    expect(w.find('[data-testid="partij-contracten-sectie"]').exists()).toBe(false)
    expect(api.contracten.lijst).not.toHaveBeenCalled()
  })

  it('externe partij: contracten-sectie zichtbaar + contracten geladen', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-contracten-sectie"]').exists()).toBe(true)
    expect(api.contracten.lijst).toHaveBeenCalledWith(expect.objectContaining({ leverancierId: 'p1' }))
  })

  it('verwijderen 409 IN_GEBRUIK blijft op het detail', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    api.partijen.verwijder.mockRejectedValueOnce({ status: 409, code: 'IN_GEBRUIK', message: 'In gebruik.' })
    const { w, router } = await mountDetail()
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.partijen.verwijder).toHaveBeenCalledWith('p1')
    expect(router.currentRoute.value.name).toBe('partij-detail')
  })

  it('verwijderen lukt → navigeert naar de partijenlijst', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    api.partijen.verwijder.mockResolvedValueOnce({})
    const { w, router } = await mountDetail()
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('partij-lijst')
  })

  it('rol-gating: viewer ziet geen bewerk-/verwijder-knop', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="bewerken-knop"]').exists()).toBe(false)
    expect(w.find('[data-testid="verwijder-knop"]').exists()).toBe(false)
  })
})
