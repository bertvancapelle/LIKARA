/** Tests — DeliverableDetailView (migratielaag: wijzigen/verwijderen + realisatieketen; UX-A4-3). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    deliverables: {
      haal: vi.fn(), keten: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn(),
      koppelWerkpakket: vi.fn(), ontkoppelWerkpakket: vi.fn(),
      koppelPlateau: vi.fn(), ontkoppelPlateau: vi.fn(),
    },
    workPackages: { lijst: vi.fn() },
    plateaus: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import DeliverableDetailView from '@/views/migratie/DeliverableDetailView.vue'

const ID = 'd1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/migratie/deliverables', name: 'deliverable-lijst', component: { template: '<div/>' } },
      { path: '/migratie/deliverables/:id', name: 'deliverable-detail', component: DeliverableDetailView, props: true },
      { path: '/migratie/werkpakketten/:id', name: 'work-package-detail', component: { template: '<div/>' } },
      { path: '/migratie/plateaus/:id', name: 'plateau-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push(`/migratie/deliverables/${ID}`)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(DeliverableDetailView, {
    props: { id: ID },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

async function kiesZoek(w, prefix, id) {
  await w.find(`[data-testid="${prefix}-input"]`).trigger('focus')
  await flushPromises()
  await w.find(`[data-testid="${prefix}-optie-${id}"]`).trigger('mousedown')
  await flushPromises()
}

const _keten = () => ({
  werkpakketten: [{ relatie_id: 'rw1', element_id: 'w1', naam: 'WP-migratie' }],
  plateaus: [{ relatie_id: 'rp1', element_id: 'p1', naam: 'Doelplateau' }],
})

beforeEach(() => {
  vi.clearAllMocks()
  api.deliverables.haal.mockResolvedValue({ id: ID, naam: 'Overgezette DB', toelichting: 'klaar' })
  api.deliverables.keten.mockResolvedValue(_keten())
  api.workPackages.lijst.mockResolvedValue({ items: [{ id: 'w2', naam: 'WP-rapportages' }], volgende_cursor: null })
  api.plateaus.lijst.mockResolvedValue({ items: [{ id: 'p2', naam: 'Eindplateau' }], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('DeliverableDetailView — render + rol-gating', () => {
  it('toont beide ketenkanten + beheer-knoppen', async () => {
    const { w } = await mountDetail()
    expect(w.find('[data-testid="del-werkpakketten-tabel"]').text()).toContain('WP-migratie')
    expect(w.find('[data-testid="del-plateaus-tabel"]').text()).toContain('Doelplateau')
    expect(w.find('[data-testid="del-wp-koppelen"]').exists()).toBe(true)
    expect(w.find('[data-testid="del-pl-koppelen"]').exists()).toBe(true)
  })

  it('viewer ziet geen beheer-/koppel-acties', async () => {
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="del-bewerken"]').exists()).toBe(false)
    expect(w.find('[data-testid="del-verwijderen"]').exists()).toBe(false)
    expect(w.find('[data-testid="del-wp-koppelen"]').exists()).toBe(false)
    expect(w.find('[data-testid="del-pl-koppelen"]').exists()).toBe(false)
    expect(w.find('[data-testid="del-wp-ontkoppel-rw1"]').exists()).toBe(false)
  })
})

describe('DeliverableDetailView — wijzigen/verwijderen', () => {
  it('bewerken stuurt werkBij', async () => {
    api.deliverables.werkBij.mockResolvedValueOnce({ id: ID, naam: 'Overgezette DB (v2)', toelichting: 'klaar' })
    const { w } = await mountDetail()
    await w.find('[data-testid="del-bewerken"]').trigger('click')
    await w.find('[data-testid="de-naam"]').setValue('Overgezette DB (v2)')
    await w.find('[data-testid="del-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.deliverables.werkBij).toHaveBeenCalledWith(ID, { naam: 'Overgezette DB (v2)', toelichting: 'klaar' })
  })

  it('verwijderen navigeert naar de lijst', async () => {
    api.deliverables.verwijder.mockResolvedValueOnce(null)
    const { w, router } = await mountDetail()
    await w.find('[data-testid="del-verwijderen"]').trigger('click')
    await w.find('[data-testid="del-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.deliverables.verwijder).toHaveBeenCalledWith(ID)
    expect(router.currentRoute.value.name).toBe('deliverable-lijst')
  })
})

describe('DeliverableDetailView — realisatieketen', () => {
  it('koppelt een werkpakket en ververst de keten', async () => {
    api.deliverables.koppelWerkpakket.mockResolvedValueOnce({ relatie_id: 'rw2', element_id: 'w2', naam: 'WP-rapportages' })
    const { w } = await mountDetail()
    const voor = api.deliverables.keten.mock.calls.length
    await w.find('[data-testid="del-wp-koppelen"]').trigger('click')
    await kiesZoek(w, 'del-wp-zoek', 'w2')
    await w.find('[data-testid="del-wp-form"]').trigger('submit')
    await flushPromises()
    expect(api.deliverables.koppelWerkpakket).toHaveBeenCalledWith(ID, 'w2')
    expect(api.deliverables.keten.mock.calls.length).toBe(voor + 1)
  })

  it('koppelt een plateau', async () => {
    api.deliverables.koppelPlateau.mockResolvedValueOnce({ relatie_id: 'rp2', element_id: 'p2', naam: 'Eindplateau' })
    const { w } = await mountDetail()
    await w.find('[data-testid="del-pl-koppelen"]').trigger('click')
    await kiesZoek(w, 'del-pl-zoek', 'p2')
    await w.find('[data-testid="del-pl-form"]').trigger('submit')
    await flushPromises()
    expect(api.deliverables.koppelPlateau).toHaveBeenCalledWith(ID, 'p2')
  })

  it('koppelen vereist een keuze (geen API-call zonder werkpakket)', async () => {
    const { w } = await mountDetail()
    await w.find('[data-testid="del-wp-koppelen"]').trigger('click')
    await w.find('[data-testid="del-wp-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="del-wp-fout"]').exists()).toBe(true)
    expect(api.deliverables.koppelWerkpakket).not.toHaveBeenCalled()
  })

  it('ontkoppelt een werkpakket en ververst de keten', async () => {
    api.deliverables.ontkoppelWerkpakket.mockResolvedValueOnce(null)
    const { w } = await mountDetail()
    const voor = api.deliverables.keten.mock.calls.length
    await w.find('[data-testid="del-wp-ontkoppel-rw1"]').trigger('click')
    await flushPromises()
    expect(api.deliverables.ontkoppelWerkpakket).toHaveBeenCalledWith(ID, 'rw1')
    expect(api.deliverables.keten.mock.calls.length).toBe(voor + 1)
  })

  it('409 dubbel: geen keten-refetch (blijft op het scherm)', async () => {
    api.deliverables.koppelWerkpakket.mockRejectedValueOnce({ status: 409, code: 'REALISATIE_BESTAAT', message: 'bestaat al' })
    const { w } = await mountDetail()
    const voor = api.deliverables.keten.mock.calls.length
    await w.find('[data-testid="del-wp-koppelen"]').trigger('click')
    await kiesZoek(w, 'del-wp-zoek', 'w2')
    await w.find('[data-testid="del-wp-form"]').trigger('submit')
    await flushPromises()
    expect(api.deliverables.keten.mock.calls.length).toBe(voor) // geen refetch
  })

  it('lege keten toont actie + "optioneel"-uitleg', async () => {
    api.deliverables.keten.mockResolvedValue({ werkpakketten: [], plateaus: [] })
    const { w } = await mountDetail()
    expect(w.find('[data-testid="del-werkpakketten-leeg"]').text()).toContain('optioneel')
    expect(w.find('[data-testid="del-plateaus-leeg"]').text()).toContain('optioneel')
  })
})
