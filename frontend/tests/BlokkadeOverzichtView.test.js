/**
 * Tests — BlokkadeOverzichtView (CD016, #12): tenant-breed sorteerbaar overzicht.
 *
 * api gemockt; memory-router voor de applicatie-links + route-query (statusfilter
 * voorselectie). Gedekt: render + applicatie-link, statusfilter→refetch+reset,
 * sorteerklik→refetch+reset+`aria-sort`, laad/leeg/fout, query-voorselectie.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  api: { blokkades: { overzicht: vi.fn() } },
}))

import { api } from '@/api'
import { DataTable } from '@/primevue'
import BlokkadeOverzichtView from '@/views/BlokkadeOverzichtView.vue'

const _item = (naam, id) => ({
  id,
  applicatie_id: `app-${id}`,
  applicatie_naam: naam,
  vraag_code: 'A1',
  status: 'open',
  toelichting: null,
  eigenaar: null,
  opgelost_op: null,
  gewijzigd_op: '2026-06-07T10:00:00Z',
})

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/blokkades', name: 'blokkades', component: BlokkadeOverzichtView },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountOverzicht({ query = '' } = {}) {
  const router = maakRouter()
  await router.push(`/blokkades${query}`)
  await router.isReady()
  const pinia = createPinia()
  const wrapper = mount(BlokkadeOverzichtView, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  api.blokkades.overzicht.mockResolvedValue({
    items: [_item('Zaaksysteem', 'b1'), _item('Archief', 'b2')],
    volgende_cursor: null,
  })
})
afterEach(() => {
  vi.clearAllMocks()
})

describe('BlokkadeOverzichtView — render', () => {
  it('rendert blokkades met applicatie-link en default-filter actief', async () => {
    const w = await mountOverzicht()
    expect(w.text()).toContain('Zaaksysteem')
    const link = w.find('[data-testid="blokkade-app-link"]')
    expect(link.attributes('href')).toContain('/applicaties/app-b1')
    // eerste call: default sort applicatie_naam asc + status actief
    expect(api.blokkades.overzicht).toHaveBeenLastCalledWith({
      limit: 25,
      after: undefined,
      status: 'actief',
      sort: 'applicatie_naam',
      order: 'asc',
    })
  })

  it('selecteert het statusfilter voor uit de route-query', async () => {
    const w = await mountOverzicht({ query: '?status=opgelost' })
    expect(w.find('[data-testid="status-filter"]').element.value).toBe('opgelost')
    expect(api.blokkades.overzicht).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'opgelost' }),
    )
  })
})

describe('BlokkadeOverzichtView — filter & sortering', () => {
  it('herlaadt met nieuw statusfilter en reset de cursor', async () => {
    const w = await mountOverzicht()
    const select = w.find('[data-testid="status-filter"]')
    await select.setValue('opgelost')
    await flushPromises()
    expect(api.blokkades.overzicht).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'opgelost', after: undefined }),
    )
  })

  it('herlaadt met sort/order + cursor-reset bij een sorteerklik', async () => {
    const w = await mountOverzicht()
    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'opgelost_op', sortOrder: -1 })
    await flushPromises()
    expect(api.blokkades.overzicht).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: 'opgelost_op', order: 'desc', after: undefined }),
    )
  })

  it('zet aria-sort op de actieve kolomheader', async () => {
    const w = await mountOverzicht()
    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'status', sortOrder: 1 })
    await flushPromises()
    const gesorteerd = w.findAll('th').filter(
      (th) => th.attributes('aria-sort') && th.attributes('aria-sort') !== 'none',
    )
    expect(gesorteerd.length).toBeGreaterThan(0)
  })
})

describe('BlokkadeOverzichtView — laad/leeg/fout', () => {
  it('toont een lege-status zonder items', async () => {
    api.blokkades.overzicht.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountOverzicht()
    expect(w.find('[data-testid="overzicht-leeg"]').exists()).toBe(true)
  })

  it('toont een foutmelding in role="alert" bij een fout', async () => {
    api.blokkades.overzicht.mockRejectedValue(new Error('Boem'))
    const w = await mountOverzicht()
    const fout = w.find('[data-testid="overzicht-fout"]')
    expect(fout.exists()).toBe(true)
    expect(fout.attributes('role')).toBe('alert')
    expect(fout.text()).toContain('Boem')
  })
})
