/** Tests — GapLijstView (migratielaag: lijst + aanmaken met baseline/doel; UX-A4-4). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { gaps: { lijst: vi.fn(), maak: vi.fn() }, plateaus: { lijst: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import GapLijstView from '@/views/migratie/GapLijstView.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/migratie/gaps', name: 'gap-lijst', component: GapLijstView },
      { path: '/migratie/gaps/:id', name: 'gap-detail', component: { template: '<div/>' }, props: true },
    ],
  })
}

async function mountLijst({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push('/migratie/gaps')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(GapLijstView, {
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

beforeEach(() => {
  vi.clearAllMocks()
  api.gaps.lijst.mockResolvedValue({ items: [{ id: 'g1', naam: 'Kloof A', toelichting: null }], volgende_cursor: null })
  api.plateaus.lijst.mockResolvedValue({
    items: [{ id: 'pb', naam: 'Baseline' }, { id: 'pd', naam: 'Doel' }], volgende_cursor: null,
  })
})
afterEach(() => vi.restoreAllMocks())

describe('GapLijstView', () => {
  it('toont de gaps + "+ Nieuwe gap" voor beheerder', async () => {
    const { w } = await mountLijst()
    expect(w.text()).toContain('Kloof A')
    expect(w.find('[data-testid="gap-nieuw"]').exists()).toBe(true)
  })

  it('viewer ziet geen "+ Nieuwe gap" (rol-gating)', async () => {
    const { w } = await mountLijst({ rollen: ['viewer'] })
    expect(w.find('[data-testid="gap-nieuw"]').exists()).toBe(false)
  })

  it('baseline + doel zijn verplicht: zonder beide geen API-call', async () => {
    const { w } = await mountLijst()
    await w.find('[data-testid="gap-nieuw"]').trigger('click')
    await w.find('[data-testid="gn-naam"]').setValue('Kloof B')
    await w.find('[data-testid="gap-nieuw-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="gn-fout-baseline"]').exists()).toBe(true)
    expect(w.find('[data-testid="gn-fout-doel"]').exists()).toBe(true)
    expect(api.gaps.maak).not.toHaveBeenCalled()
  })

  it('baseline == doel wordt geweigerd', async () => {
    const { w } = await mountLijst()
    await w.find('[data-testid="gap-nieuw"]').trigger('click')
    await w.find('[data-testid="gn-naam"]').setValue('Kloof B')
    await kiesZoek(w, 'gn-baseline-zoek', 'pb')
    await kiesZoek(w, 'gn-doel-zoek', 'pb')
    await w.find('[data-testid="gap-nieuw-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="gn-fout-doel"]').exists()).toBe(true)
    expect(api.gaps.maak).not.toHaveBeenCalled()
  })

  it('aanmaken met baseline + doel roept maak aan en navigeert', async () => {
    api.gaps.maak.mockResolvedValueOnce({ id: 'g9' })
    const { w, router } = await mountLijst()
    await w.find('[data-testid="gap-nieuw"]').trigger('click')
    await w.find('[data-testid="gn-naam"]').setValue('Kloof B')
    await kiesZoek(w, 'gn-baseline-zoek', 'pb')
    await kiesZoek(w, 'gn-doel-zoek', 'pd')
    await w.find('[data-testid="gap-nieuw-form"]').trigger('submit')
    await flushPromises()
    expect(api.gaps.maak).toHaveBeenCalledWith({
      naam: 'Kloof B', toelichting: null, baseline_plateau_id: 'pb', doel_plateau_id: 'pd',
    })
    expect(router.currentRoute.value.params.id).toBe('g9')
  })

  it('lege lijst toont een actie-uitleg voor wie mag aanmaken', async () => {
    api.gaps.lijst.mockResolvedValueOnce({ items: [], volgende_cursor: null })
    const { w } = await mountLijst()
    const leeg = w.find('[data-testid="gap-lijst-leeg"]')
    expect(leeg.exists()).toBe(true)
    expect(leeg.text()).toContain('+ Nieuwe gap')
  })
})
