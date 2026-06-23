/**
 * Tests — ArchitectuurView (cross-element laagprojectie, F-2).
 * api gemockt; render van de gelaagde lijst (naam/type/laag/aspect/element) + de
 * laag/aspect/type-filters (server-side: param meegestuurd + cursor-reset).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  api: { architectuur: { elementen: vi.fn() } },
}))

import { api } from '@/api'
import ArchitectuurView from '@/views/ArchitectuurView.vue'

const STUB = { template: '<div/>' }
function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: STUB },
      { path: '/componenten/:id', name: 'component-detail', component: STUB },
      { path: '/contracten/:id', name: 'contract-detail', component: STUB },
      { path: '/partijen/:id', name: 'partij-detail', component: STUB },
      { path: '/migratie/plateaus/:id', name: 'plateau-detail', component: STUB },
      { path: '/migratie/gaps/:id', name: 'gap-detail', component: STUB },
      { path: '/migratie/werkpakketten/:id', name: 'work-package-detail', component: STUB },
      { path: '/migratie/deliverables/:id', name: 'deliverable-detail', component: STUB },
    ],
  })
}

const _items = () => [
  { id: 'c1', element_type: 'component', naam: 'Zaaksysteem', naam_secundair: null, archimate_element: 'application_component', laag: 'application', aspect: 'active' },
  { id: 'k1', element_type: 'contract', naam: 'Oracle licentie', naam_secundair: null, archimate_element: 'contract', laag: 'business', aspect: 'passive' },
  { id: 'd1', element_type: 'datatype', naam: 'gestructureerd_db', naam_secundair: 'Klantgegevens', archimate_element: 'data_object', laag: 'application', aspect: 'passive' },
]

async function mountView({ tab = 'tabel' } = {}) {
  const pinia = createPinia()
  const router = maakRouter()
  await router.push('/')
  await router.isReady()
  const w = mount(ArchitectuurView, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  // Component-default is 'lagen'; tabel-tests schakelen naar de Tabel-tab
  // (localStorage werkt niet in deze test-env, dus via de toggle-knop).
  if (tab === 'tabel') {
    await w.find('[data-testid="arch-weergave-tabel"]').trigger('click')
    await flushPromises()
  }
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.architectuur.elementen.mockResolvedValue({ items: _items(), volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('ArchitectuurView', () => {
  it('rendert elementen met laag/aspect/element en de secundaire naamregel', async () => {
    const w = await mountView()
    const tekst = w.find('[data-testid="arch-tabel"]').text()
    expect(tekst).toContain('Zaaksysteem')
    expect(tekst).toContain('Oracle licentie')
    // laag-/aspect-labels (NL) + datatype-secundair (omschrijving).
    expect(tekst).toContain('Applicatie')
    expect(tekst).toContain('Business')
    expect(tekst).toContain('Passieve structuur')
    expect(tekst).toContain('Klantgegevens')
  })

  it('B2: rij-doorklik naar het detail per element-type; datatype zonder eigen detail krijgt geen link', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="arch-link-c1"]').attributes('href')).toContain('/componenten/c1')
    expect(w.find('[data-testid="arch-link-k1"]').attributes('href')).toContain('/contracten/k1')
    expect(w.find('[data-testid="arch-link-d1"]').exists()).toBe(false) // datatype: geen detailpagina
  })

  it('B3: kolom heet "Soort", niet "ArchiMate-element"', async () => {
    const w = await mountView()
    const tabel = w.find('[data-testid="arch-tabel"]').text()
    expect(tabel).toContain('Soort')
    expect(tabel).not.toContain('ArchiMate-element')
  })

  it('laag-filter stuurt de param mee en reset de cursor', async () => {
    const w = await mountView()
    await w.find('[data-testid="arch-filter-laag"]').setValue('technology')
    await flushPromises()
    expect(api.architectuur.elementen).toHaveBeenLastCalledWith(
      expect.objectContaining({ laag: 'technology', after: undefined }),
    )
  })

  it('B2: kolom-sorteerklik stuurt sort/order mee en reset de cursor (server-side)', async () => {
    const w = await mountView()
    const dt = w.findComponent({ name: 'DataTable' })
    // Naam aflopend.
    dt.vm.$emit('sort', { sortField: 'naam', sortOrder: -1 })
    await flushPromises()
    expect(api.architectuur.elementen).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: 'naam', order: 'desc', after: undefined }),
    )
    // Laag oplopend.
    dt.vm.$emit('sort', { sortField: 'laag', sortOrder: 1 })
    await flushPromises()
    expect(api.architectuur.elementen).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: 'laag', order: 'asc', after: undefined }),
    )
  })

  it('aspect- en type-filter worden meegestuurd', async () => {
    const w = await mountView()
    await w.find('[data-testid="arch-filter-aspect"]').setValue('behavior')
    await flushPromises()
    expect(api.architectuur.elementen).toHaveBeenLastCalledWith(expect.objectContaining({ aspect: 'behavior' }))
    await w.find('[data-testid="arch-filter-type"]').setValue('plateau')
    await flushPromises()
    expect(api.architectuur.elementen).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'plateau' }))
  })
})

describe('ArchitectuurView — lagenweergave (LI025)', () => {
  async function mountLagen() {
    return mountView({ tab: 'lagen' })
  }

  it('toont de lagen-bands met klikbare element-pills (default Lagen)', async () => {
    const w = await mountLagen()
    expect(w.find('[data-testid="arch-weergave-lagen"]').attributes('aria-pressed')).toBe('true')
    expect(w.find('[data-testid="arch-lagen"]').exists()).toBe(true)
    expect(w.find('[data-testid="arch-band-business"]').exists()).toBe(true)
    expect(w.find('[data-testid="arch-band-application"]').exists()).toBe(true)
    const pill = w.find('[data-testid="arch-pill-c1"]')
    expect(pill.exists()).toBe(true)
    expect(pill.text()).toContain('Zaaksysteem')
    expect(w.find('[data-testid="arch-tabel"]').exists()).toBe(false) // tabel niet gerenderd in lagen-modus
  })

  it('migratie-toggle verbergt de migratie-band', async () => {
    const w = await mountLagen()
    expect(w.find('[data-testid="arch-band-implementation_migration"]').exists()).toBe(true)
    await w.find('[data-testid="arch-lagen-migratie"]').setValue(false)
    await flushPromises()
    expect(w.find('[data-testid="arch-band-implementation_migration"]').exists()).toBe(false)
  })
})
