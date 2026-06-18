/** Tests — DeliverableLijstView (migratielaag: lijst + aanmaken; UX-A4-3). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { deliverables: { lijst: vi.fn(), maak: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import DeliverableLijstView from '@/views/migratie/DeliverableLijstView.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/migratie/deliverables', name: 'deliverable-lijst', component: DeliverableLijstView },
      { path: '/migratie/deliverables/:id', name: 'deliverable-detail', component: { template: '<div/>' }, props: true },
    ],
  })
}

async function mountLijst({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push('/migratie/deliverables')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(DeliverableLijstView, {
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

beforeEach(() => {
  vi.clearAllMocks()
  api.deliverables.lijst.mockResolvedValue({ items: [{ id: 'd1', naam: 'Overgezette DB', toelichting: null }], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('DeliverableLijstView', () => {
  it('toont de deliverables + "+ Nieuwe deliverable" voor beheerder', async () => {
    const { w } = await mountLijst()
    expect(w.text()).toContain('Overgezette DB')
    expect(w.find('[data-testid="del-nieuw"]').exists()).toBe(true)
  })

  it('viewer ziet geen "+ Nieuwe deliverable" (rol-gating)', async () => {
    const { w } = await mountLijst({ rollen: ['viewer'] })
    expect(w.find('[data-testid="del-nieuw"]').exists()).toBe(false)
  })

  it('naam leeg ⇒ validatiefout, geen API-call', async () => {
    const { w } = await mountLijst()
    await w.find('[data-testid="del-nieuw"]').trigger('click')
    await w.find('[data-testid="del-nieuw-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="dl-fout-naam"]').exists()).toBe(true)
    expect(api.deliverables.maak).not.toHaveBeenCalled()
  })

  it('aanmaken roept maak aan en navigeert naar het detail', async () => {
    api.deliverables.maak.mockResolvedValueOnce({ id: 'd9' })
    const { w, router } = await mountLijst()
    await w.find('[data-testid="del-nieuw"]').trigger('click')
    await w.find('[data-testid="dl-naam"]').setValue('Gemigreerd rapportagepakket')
    await w.find('[data-testid="del-nieuw-form"]').trigger('submit')
    await flushPromises()
    expect(api.deliverables.maak).toHaveBeenCalledWith({ naam: 'Gemigreerd rapportagepakket', toelichting: null })
    expect(router.currentRoute.value.params.id).toBe('d9')
  })

  it('lege lijst toont een actie-uitleg voor wie mag aanmaken', async () => {
    api.deliverables.lijst.mockResolvedValueOnce({ items: [], volgende_cursor: null })
    const { w } = await mountLijst()
    const leeg = w.find('[data-testid="del-lijst-leeg"]')
    expect(leeg.exists()).toBe(true)
    expect(leeg.text()).toContain('+ Nieuwe deliverable')
  })
})
