/**
 * Tests — ArchitectuurView (cross-element laagprojectie, F-2).
 * api gemockt; render van de gelaagde lijst (naam/type/laag/aspect/element) + de
 * laag/aspect/type-filters (server-side: param meegestuurd + cursor-reset).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  api: { architectuur: { elementen: vi.fn() } },
}))

import { api } from '@/api'
import ArchitectuurView from '@/views/ArchitectuurView.vue'

const _items = () => [
  { id: 'c1', element_type: 'component', naam: 'Zaaksysteem', naam_secundair: null, archimate_element: 'application_component', laag: 'application', aspect: 'active' },
  { id: 'k1', element_type: 'contract', naam: 'Oracle licentie', naam_secundair: null, archimate_element: 'contract', laag: 'business', aspect: 'passive' },
  { id: 'd1', element_type: 'datatype', naam: 'gestructureerd_db', naam_secundair: 'Klantgegevens', archimate_element: 'data_object', laag: 'application', aspect: 'passive' },
]

async function mountView() {
  const pinia = createPinia()
  const w = mount(ArchitectuurView, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }]] },
  })
  await flushPromises()
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

  it('laag-filter stuurt de param mee en reset de cursor', async () => {
    const w = await mountView()
    await w.find('[data-testid="arch-filter-laag"]').setValue('technology')
    await flushPromises()
    expect(api.architectuur.elementen).toHaveBeenLastCalledWith(
      expect.objectContaining({ laag: 'technology', after: undefined }),
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
