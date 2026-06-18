/** Tests — PartijFormulier (ADR-024 slice 2a): aard-keuze bij aanmaken, soort optioneel,
 *  naam verplicht client-side, 422-veldfout-mapping. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { partijen: { maak: vi.fn(), werkBij: vi.fn(), haal: vi.fn(), soorten: vi.fn() } },
}))

import { api } from '@/api'
import PartijFormulier from '@modules/bwb_ontvlechting/frontend/views/PartijFormulier.vue'

function maakRouter() {
  const r = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/partijen', name: 'partij-lijst', component: { template: '<div/>' } },
      { path: '/partijen/nieuw', name: 'partij-nieuw', component: PartijFormulier },
      { path: '/partijen/:id', name: 'partij-detail', component: { template: '<div/>' } },
      { path: '/partijen/:id/bewerken', name: 'partij-bewerken', component: PartijFormulier, props: true },
    ],
  })
  return r
}

async function mountForm({ id = null } = {}) {
  const router = maakRouter()
  await router.push(id ? `/partijen/${id}/bewerken` : '/partijen/nieuw')
  await router.isReady()
  const w = mount(PartijFormulier, {
    props: { id },
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

beforeEach(() => {
  vi.clearAllMocks()
  api.partijen.soorten.mockResolvedValue([{ optie_sleutel: 'leverancier', label: 'Leverancier' }])
})
afterEach(() => vi.restoreAllMocks())

describe('PartijFormulier — aanmaken', () => {
  it('naam leeg ⇒ validatiefout, geen API-call', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    expect(w.find('[data-testid="fout-naam"]').exists()).toBe(true)
    expect(api.partijen.maak).not.toHaveBeenCalled()
  })

  it('aard verplicht bij aanmaken', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('J. de Vries')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    expect(w.find('[data-testid="fout-aard"]').exists()).toBe(true)
    expect(api.partijen.maak).not.toHaveBeenCalled()
  })

  it('aanmaken persoon stuurt aard + naam + soort', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'p1' })
    const { w, router } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    await w.find('[data-testid="veld-naam"]').setValue('J. de Vries')
    await w.find('[data-testid="veld-soort"]').setValue('leverancier')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(api.partijen.maak).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'persoon', naam: 'J. de Vries', soort: 'leverancier' }),
    )
    expect(router.currentRoute.value.name).toBe('partij-detail')
  })

  it('soort-dropdown wordt gevuld uit de catalogus', async () => {
    const { w } = await mountForm()
    const opties = w.find('[data-testid="veld-soort"]').findAll('option').map((o) => o.text())
    expect(opties).toContain('Leverancier')
  })

  it('422-veldfout van de backend landt op het juiste veld', async () => {
    api.partijen.maak.mockRejectedValueOnce({ status: 422, detail: [{ loc: ['body', 'naam'], msg: 'Te lang.' }] })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('organisatie')
    await w.find('[data-testid="veld-naam"]').setValue('X')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-naam"]').text()).toContain('Te lang.')
  })
})

describe('PartijFormulier — bewerken', () => {
  it('aard is read-only (geen keuzeveld) en niet in de payload', async () => {
    api.partijen.haal.mockResolvedValueOnce({ id: 'p1', aard: 'organisatie_eenheid', naam: 'Afdeling I&A', soort: null })
    api.partijen.werkBij.mockResolvedValueOnce({ id: 'p1' })
    const { w } = await mountForm({ id: 'p1' })
    expect(w.find('[data-testid="veld-aard"]').exists()).toBe(false)
    expect(w.find('[data-testid="aard-readonly"]').text()).toContain('Afdeling')
    await w.find('[data-testid="veld-naam"]').setValue('Afdeling I&A (gewijzigd)')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    const payload = api.partijen.werkBij.mock.calls[0][1]
    expect('aard' in payload).toBe(false)
  })
})
