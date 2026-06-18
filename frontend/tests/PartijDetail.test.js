/** Tests — PartijDetail (ADR-024 slice 2a): aard-tag, soort, contracten-sectie alleen voor
 *  externe partij, verwijderen (409 IN_GEBRUIK blijft op detail). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import DataTable from 'primevue/datatable'

vi.mock('@/api', () => ({
  api: {
    partijen: { haal: vi.fn(), verwijder: vi.fn(), lijst: vi.fn() },
    contracten: { lijst: vi.fn() },
    // ADR-024 slice 2b — PartijRollenSectie (alleen-lezen) laadt bij mount.
    roltoewijzingen: { lijst: vi.fn(() => Promise.resolve([])) },
  },
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
  api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })  // leden-overzicht
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

  it('toont de alleen-lezen "Rollen op objecten"-sectie (ADR-024 slice 2b)', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    const { w } = await mountDetail()
    expect(w.find('[data-testid="pr-sectie"]').exists()).toBe(true)
    expect(api.roltoewijzingen.lijst).toHaveBeenCalledWith({ partij_id: 'p1' })
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

  it('organisatie: onderdelen-sectie toont afdelingen + personen ("hoort bij", andere kant)', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    api.partijen.lijst.mockResolvedValue({
      items: [
        { id: 'a1', naam: 'Afdeling I&A', aard: 'organisatie_eenheid' },
        { id: 'pp1', naam: 'J. Jansen', aard: 'persoon' },
      ],
      volgende_cursor: null,
    })
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-leden-sectie"]').exists()).toBe(true)
    expect(api.partijen.lijst).toHaveBeenCalledWith(expect.objectContaining({ organisatie_id: 'p1' }))
    expect(w.text()).toContain('Afdeling I&A')
    expect(w.text()).toContain('J. Jansen')
  })

  it('leden-blok sorteert server-side (Aard) met cursor-reset', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const { w } = await mountDetail()
    // initiële load: organisatie-filter + default sort naam/asc
    expect(api.partijen.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ organisatie_id: 'p1', sort: 'naam', order: 'asc', after: undefined }),
    )
    // @sort op de Aard-kolom (aflopend) → refetch met sort=aard/desc en gereset cursor
    await w.findComponent(DataTable).vm.$emit('sort', { sortField: 'aard', sortOrder: -1 })
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ organisatie_id: 'p1', sort: 'aard', order: 'desc', after: undefined }),
    )
  })

  it('leden-blok pagineert met de keyset-cursor ("Meer laden")', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    api.partijen.lijst
      .mockResolvedValueOnce({ items: [{ id: 'a1', naam: 'Afd', aard: 'organisatie_eenheid' }], volgende_cursor: 'cur-1' })
      .mockResolvedValueOnce({ items: [{ id: 'pp1', naam: 'Jan', aard: 'persoon' }], volgende_cursor: null })
    const { w } = await mountDetail()
    expect(w.find('[data-testid="leden-meer-laden"]').exists()).toBe(true)
    await w.find('[data-testid="leden-meer-laden"]').trigger('click')
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ organisatie_id: 'p1', after: 'cur-1' }))
    expect(w.find('[data-testid="leden-meer-laden"]').exists()).toBe(false)  // cursor op null
    expect(w.text()).toContain('Afd')
    expect(w.text()).toContain('Jan')
  })

  it('externe partij zonder leden → leden-blok is leeg', async () => {
    api.partijen.haal.mockResolvedValue(_partij())  // externe_partij, organisatie-achtig
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-leden-sectie"]').exists()).toBe(true)
    expect(w.find('[data-testid="partij-leden-leeg"]').exists()).toBe(true)
    expect(api.partijen.lijst).toHaveBeenCalledWith(expect.objectContaining({ organisatie_id: 'p1' }))
  })

  it('afdeling: personen-sectie + "hoort bij" de organisatie', async () => {
    api.partijen.haal.mockImplementation((id) =>
      id === 'p1'
        ? Promise.resolve(_partij({ aard: 'organisatie_eenheid', naam: 'Afdeling I&A', soort: null, organisatie_id: 'org9' }))
        : Promise.resolve(_partij({ id: 'org9', aard: 'organisatie', naam: 'Gemeente X' })),
    )
    api.partijen.lijst.mockResolvedValue({ items: [{ id: 'pp1', naam: 'J. Jansen', aard: 'persoon' }], volgende_cursor: null })
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-leden-sectie"]').exists()).toBe(true)
    expect(api.partijen.lijst).toHaveBeenCalledWith(expect.objectContaining({ afdeling_id: 'p1' }))
    expect(w.find('[data-testid="partij-hoortbij"]').text()).toContain('Gemeente X')
    expect(w.text()).toContain('J. Jansen')
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
