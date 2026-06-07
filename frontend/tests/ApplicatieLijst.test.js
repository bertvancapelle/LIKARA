/**
 * Tests — ApplicatieLijst (module-view, via @modules-alias).
 *
 * Module-views staan in modules/<module>/frontend/views; hun tests staan onder
 * frontend/tests/ (binnen vitest-root) en importeren de view via de @modules-alias.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

// api gemockt — geen echte fetch.
vi.mock('@/api', () => ({
  api: { applicaties: { lijst: vi.fn() } },
}))

import { api } from '@/api'
import { DataTable } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import ApplicatieLijst from '@modules/bwb_ontvlechting/frontend/views/ApplicatieLijst.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/applicaties', name: 'applicatie-lijst', component: ApplicatieLijst },
      { path: '/applicaties/nieuw', name: 'applicatie-nieuw', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountLijst({ rollen = ['medewerker'] } = {}) {
  const router = maakRouter()
  await router.push('/applicaties')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const wrapper = mount(ApplicatieLijst, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  return wrapper
}

const _app = (naam, id) => ({
  id,
  naam,
  eigenaar_organisatie: 'Gemeente Veldendam',
  hostingmodel: 'saas',
  complexiteit: 'midden',
  prioriteit: 'hoog',
  lifecycle_status: 'concept',
})

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ApplicatieLijst', () => {
  it('rendert de geladen applicaties', async () => {
    api.applicaties.lijst.mockResolvedValueOnce({
      items: [_app('Zaaksysteem', 'id-1'), _app('Archief', 'id-2')],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    expect(w.text()).toContain('Zaaksysteem')
    expect(w.text()).toContain('Archief')
    // labels uit de frontend-labelmap
    expect(w.text()).toContain('SaaS')
  })

  it('toont "Meer laden" alleen bij een volgende_cursor en pagineert ermee', async () => {
    api.applicaties.lijst
      .mockResolvedValueOnce({ items: [_app('Eerste', 'id-1')], volgende_cursor: 'cursor-1' })
      .mockResolvedValueOnce({ items: [_app('Tweede', 'id-2')], volgende_cursor: null })

    const w = await mountLijst()
    const meer = w.find('[data-testid="meer-laden"]')
    expect(meer.exists()).toBe(true)

    await meer.trigger('click')
    await flushPromises()

    // tweede call gebruikt de cursor van de eerste pagina
    expect(api.applicaties.lijst).toHaveBeenCalledTimes(2)
    expect(api.applicaties.lijst).toHaveBeenLastCalledWith({ limit: 25, after: 'cursor-1' })
    expect(w.text()).toContain('Eerste')
    expect(w.text()).toContain('Tweede')
    // geen volgende cursor meer → knop weg
    expect(w.find('[data-testid="meer-laden"]').exists()).toBe(false)
  })

  it('linkt elke rij naar de detail-route', async () => {
    api.applicaties.lijst.mockResolvedValueOnce({
      items: [_app('Zaaksysteem', 'id-42')],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    const link = w.find('[data-testid="rij-link"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toContain('/applicaties/id-42')
  })

  it('toont een lege-status zonder items', async () => {
    api.applicaties.lijst.mockResolvedValueOnce({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    expect(w.find('[data-testid="lijst-leeg"]').exists()).toBe(true)
  })

  it('toont een foutmelding bij een API-fout', async () => {
    api.applicaties.lijst.mockRejectedValueOnce(new Error('Netwerkfout'))
    const w = await mountLijst()
    const fout = w.find('[data-testid="lijst-fout"]')
    expect(fout.exists()).toBe(true)
    expect(fout.attributes('role')).toBe('alert')
  })

  it('toont de aanmaak-knop voor Medewerker+ maar niet voor Viewer', async () => {
    api.applicaties.lijst.mockResolvedValue({ items: [], volgende_cursor: null })

    const medewerker = await mountLijst({ rollen: ['medewerker'] })
    expect(medewerker.find('[data-testid="nieuwe-applicatie"]').exists()).toBe(true)

    const viewer = await mountLijst({ rollen: ['viewer'] })
    expect(viewer.find('[data-testid="nieuwe-applicatie"]').exists()).toBe(false)
  })
})

describe('ApplicatieLijst — server-side sortering (ADR-017)', () => {
  it('haalt opnieuw op met sort/order en reset de cursor bij een sorteerklik', async () => {
    api.applicaties.lijst
      .mockResolvedValueOnce({ items: [_app('Eerste', 'id-1')], volgende_cursor: 'cursor-1' })
      .mockResolvedValueOnce({ items: [_app('Archief', 'id-2')], volgende_cursor: null })

    const w = await mountLijst()
    // eerste (default) call stuurt géén sort/order mee → backwards-compatible
    expect(api.applicaties.lijst).toHaveBeenLastCalledWith({ limit: 25, after: undefined })

    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'naam', sortOrder: -1 })
    await flushPromises()

    // refetch met sort/order én cursor-reset (after: undefined)
    expect(api.applicaties.lijst).toHaveBeenLastCalledWith({
      limit: 25,
      after: undefined,
      sort: 'naam',
      order: 'desc',
    })
  })

  it('vertaalt sortOrder 1 naar asc', async () => {
    api.applicaties.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()

    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'eigenaar_organisatie', sortOrder: 1 })
    await flushPromises()

    expect(api.applicaties.lijst).toHaveBeenLastCalledWith({
      limit: 25,
      after: undefined,
      sort: 'eigenaar_organisatie',
      order: 'asc',
    })
  })

  it('zet aria-sort op de actieve kolomheader', async () => {
    api.applicaties.lijst.mockResolvedValue({
      items: [_app('Zaaksysteem', 'id-1')],
      volgende_cursor: null,
    })
    const w = await mountLijst()

    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'naam', sortOrder: -1 })
    await flushPromises()

    const gesorteerd = w.findAll('th').filter(
      (th) => th.attributes('aria-sort') && th.attributes('aria-sort') !== 'none',
    )
    expect(gesorteerd.length).toBeGreaterThan(0)
  })
})
