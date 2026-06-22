/** Tests — WorkPackageDetailView (migratielaag: wijzigen/verwijderen + sub-werkpakketten; UX-A4-2). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    workPackages: {
      haal: vi.fn(), subboom: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn(), lijst: vi.fn(),
    },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import WorkPackageDetailView from '@/views/migratie/WorkPackageDetailView.vue'

const ID = 'w1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/migratie/werkpakketten', name: 'work-package-lijst', component: { template: '<div/>' } },
      { path: '/migratie/werkpakketten/:id', name: 'work-package-detail', component: WorkPackageDetailView, props: true },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push(`/migratie/werkpakketten/${ID}`)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(WorkPackageDetailView, {
    props: { id: ID },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

beforeEach(() => {
  vi.clearAllMocks()
  api.workPackages.haal.mockResolvedValue({ id: ID, naam: 'Financieel domein', toelichting: 'root', bovenliggend_id: null })
  api.workPackages.subboom.mockResolvedValue([
    { id: 'w2', naam: 'Oracle-DB overzetten', bovenliggend_id: ID, niveau: 1, pad: ['Financieel domein', 'Oracle-DB overzetten'] },
  ])
  api.workPackages.lijst.mockResolvedValue({ items: [{ id: 'w0', naam: 'Programma' }], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('WorkPackageDetailView — parent-context in header', () => {
  it('toont "Onderdeel van" met link bij een sub-werkpakket', async () => {
    api.workPackages.haal.mockImplementation((id) =>
      Promise.resolve(
        id === ID
          ? { id: ID, naam: 'Oracle-DB overzetten', toelichting: null, bovenliggend_id: 'parent9' }
          : { id: 'parent9', naam: 'Financieel domein', toelichting: null, bovenliggend_id: null },
      ),
    )
    const { w } = await mountDetail()
    expect(w.find('[data-testid="wp-ouder"]').exists()).toBe(true)
    const link = w.find('[data-testid="wp-ouder-link"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toContain('Financieel domein')
  })

  it('verbergt "Onderdeel van" bij een top-niveau werkpakket', async () => {
    // default-mock: bovenliggend_id: null
    const { w } = await mountDetail()
    expect(w.find('[data-testid="wp-ouder"]').exists()).toBe(false)
  })
})

describe('WorkPackageDetailView — render + rol-gating', () => {
  it('toont naam, subpakketten en beheer-knoppen', async () => {
    const { w } = await mountDetail()
    expect(w.find('[data-testid="wp-naam"]').text()).toBe('Financieel domein')
    expect(w.text()).toContain('Oracle-DB overzetten')
    expect(w.text()).toContain('1 direct')
    expect(w.find('[data-testid="wp-bewerken"]').exists()).toBe(true)
    expect(w.find('[data-testid="wp-sub-toevoegen"]').exists()).toBe(true)
  })

  it('viewer ziet geen beheer-acties', async () => {
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="wp-bewerken"]').exists()).toBe(false)
    expect(w.find('[data-testid="wp-verwijderen"]').exists()).toBe(false)
    expect(w.find('[data-testid="wp-sub-toevoegen"]').exists()).toBe(false)
  })
})

describe('WorkPackageDetailView — wijzigen/verwijderen', () => {
  it('bewerken stuurt werkBij (incl. bovenliggend leeg = top-niveau)', async () => {
    api.workPackages.werkBij.mockResolvedValueOnce({ id: ID, naam: 'Financieel domein (2026)', toelichting: 'root', bovenliggend_id: null })
    const { w } = await mountDetail()
    await w.find('[data-testid="wp-bewerken"]').trigger('click')
    await w.find('[data-testid="we-naam"]').setValue('Financieel domein (2026)')
    await w.find('[data-testid="wp-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.workPackages.werkBij).toHaveBeenCalledWith(ID, {
      naam: 'Financieel domein (2026)', toelichting: 'root', bovenliggend_id: null,
    })
  })

  it('cyclus-fout (422) bij bewerken blijft op het scherm (dialog open)', async () => {
    api.workPackages.werkBij.mockRejectedValueOnce({ status: 422, code: 'CYCLISCHE_HIERARCHIE', message: 'kring' })
    const { w } = await mountDetail()
    await w.find('[data-testid="wp-bewerken"]').trigger('click')
    await w.find('[data-testid="we-naam"]').setValue('X')
    await w.find('[data-testid="wp-edit-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="wp-edit-dialog"]').exists()).toBe(true) // niet gesloten
  })

  it('verwijderen navigeert naar de lijst', async () => {
    api.workPackages.verwijder.mockResolvedValueOnce(null)
    const { w, router } = await mountDetail()
    await w.find('[data-testid="wp-verwijderen"]').trigger('click')
    await w.find('[data-testid="wp-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.workPackages.verwijder).toHaveBeenCalledWith(ID)
    expect(router.currentRoute.value.name).toBe('work-package-lijst')
  })

  it('409 (heeft subpakketten) bij verwijderen blijft op het detail', async () => {
    api.workPackages.verwijder.mockRejectedValueOnce({ status: 409, code: 'HEEFT_SUBPAKKETTEN', message: 'heeft subs' })
    const { w, router } = await mountDetail()
    await w.find('[data-testid="wp-verwijderen"]').trigger('click')
    await w.find('[data-testid="wp-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('work-package-detail') // geen navigatie
  })
})

describe('WorkPackageDetailView — sub-werkpakket toevoegen', () => {
  it('voegt een sub-werkpakket toe met dit werkpakket als bovenliggend + ververst de subboom', async () => {
    api.workPackages.maak.mockResolvedValueOnce({ id: 'w3' })
    const { w } = await mountDetail()
    const voor = api.workPackages.subboom.mock.calls.length
    await w.find('[data-testid="wp-sub-toevoegen"]').trigger('click')
    await w.find('[data-testid="ws-naam"]').setValue('Rapportages herbouwen')
    await w.find('[data-testid="wp-sub-form"]').trigger('submit')
    await flushPromises()
    expect(api.workPackages.maak).toHaveBeenCalledWith({ naam: 'Rapportages herbouwen', toelichting: null, bovenliggend_id: ID })
    expect(api.workPackages.subboom.mock.calls.length).toBe(voor + 1) // subboom herladen
  })

  it('leeg (geen subpakketten) toont een actie-uitleg', async () => {
    api.workPackages.subboom.mockResolvedValue([])
    const { w } = await mountDetail()
    const leeg = w.find('[data-testid="wp-subboom-leeg"]')
    expect(leeg.exists()).toBe(true)
    expect(leeg.text()).toContain('+ Sub-werkpakket')
  })
})
