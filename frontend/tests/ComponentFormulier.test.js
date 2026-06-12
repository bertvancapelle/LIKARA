/** Tests — ComponentFormulier (aanmaken/bewerken niet-applicatie-componenten; CD054b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { componenten: { opties: vi.fn(), haal: vi.fn(), maak: vi.fn(), werkBij: vi.fn() } },
}))

import { api } from '@/api'
import ComponentFormulier from '@modules/bwb_ontvlechting/frontend/views/ComponentFormulier.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/componenten/nieuw', name: 'component-nieuw', component: ComponentFormulier },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
      { path: '/componenten/:id/bewerken', name: 'component-bewerken', component: ComponentFormulier, props: true },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
      { path: '/componenten', name: 'component-lijst', component: { template: '<div/>' } },
    ],
  })
}

async function mountForm({ props = {} } = {}) {
  const router = maakRouter()
  await router.push('/componenten/nieuw')
  await router.isReady()
  const pinia = createPinia()
  const w = mount(ComponentFormulier, {
    props,
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

beforeEach(() => {
  vi.clearAllMocks()
  api.componenten.opties.mockResolvedValue({
    componenttype: [
      { optie_sleutel: 'database', label: 'Database' },
      { optie_sleutel: 'fileshare', label: 'Fileshare' },
      { optie_sleutel: 'applicatie', label: 'Applicatie' },
    ],
    structuurrelatie_type: [],
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ComponentFormulier', () => {
  it('de type-select bevat "applicatie" (convergente aanmaak)', async () => {
    const { w } = await mountForm()
    const opties = w.find('[data-testid="veld-componenttype"]').findAll('option')
    const waarden = opties.map((o) => o.attributes('value'))
    expect(waarden).toContain('database')
    expect(waarden).toContain('fileshare')
    expect(waarden).toContain('applicatie')
  })

  it('aanmaken met type "applicatie" leidt door naar ApplicatieDetail (convergentie)', async () => {
    api.componenten.maak.mockResolvedValueOnce({ id: 'app-new', heeft_applicatie_subtype: true })
    const { w, router } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('Nieuwe applicatie')
    await w.find('[data-testid="veld-componenttype"]').setValue('applicatie')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.maak).toHaveBeenCalledWith(
      expect.objectContaining({ naam: 'Nieuwe applicatie', componenttype: 'applicatie' }),
    )
    expect(router.currentRoute.value.name).toBe('applicatie-detail')
    expect(router.currentRoute.value.params.id).toBe('app-new')
  })

  it('naam is verplicht (geen API-call bij leeg)', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-componenttype"]').setValue('database')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-naam"]').exists()).toBe(true)
    expect(api.componenten.maak).not.toHaveBeenCalled()
  })

  it('aanmaken stuurt de payload en navigeert naar het detail', async () => {
    api.componenten.maak.mockResolvedValueOnce({ id: 'new-1' })
    const { w, router } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('Geo-fileshare')
    await w.find('[data-testid="veld-componenttype"]').setValue('fileshare')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.maak).toHaveBeenCalledWith(
      expect.objectContaining({ naam: 'Geo-fileshare', componenttype: 'fileshare' }),
    )
    expect(router.currentRoute.value.name).toBe('component-detail')
  })

  it('foutmapping: 422-veldfout van de backend landt op het veld', async () => {
    api.componenten.maak.mockRejectedValueOnce({
      status: 422,
      detail: [{ loc: ['body', 'naam'], msg: 'Ongeldige naam.' }],
    })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('x')
    await w.find('[data-testid="veld-componenttype"]').setValue('database')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-naam"]').text()).toContain('Ongeldige naam.')
  })

  it('GEBRUIK_APPLICATIE_PAD wordt afgevangen (geen crash, geen veldfout)', async () => {
    api.componenten.maak.mockRejectedValueOnce({
      status: 409,
      code: 'GEBRUIK_APPLICATIE_PAD',
      message: 'Beheer via de applicatie.',
    })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('Iets')
    await w.find('[data-testid="veld-componenttype"]').setValue('database')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.maak).toHaveBeenCalled()
    expect(w.find('[data-testid="fout-naam"]').exists()).toBe(false)
  })

  it('bewerken van een applicatie-subtype wordt omgeleid naar ApplicatieDetail', async () => {
    api.componenten.haal.mockResolvedValueOnce({
      id: 'app-1',
      naam: 'Belastingsysteem',
      componenttype: 'applicatie',
      hostingmodel: 'saas',
      heeft_applicatie_subtype: true,
    })
    const router = maakRouter()
    await router.push('/componenten/app-1/bewerken')
    await router.isReady()
    const pinia = createPinia()
    mount(ComponentFormulier, {
      props: { id: 'app-1' },
      attachTo: document.body,
      global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
    })
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('applicatie-detail')
    expect(api.componenten.maak).not.toHaveBeenCalled()
  })
})
