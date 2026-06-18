/** Tests — ApplicatieFormulier (aanmaken/bewerken, module-view via @modules). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    applicaties: {
      opties: vi.fn(),
      haal: vi.fn(),
      maak: vi.fn(),
      werkBij: vi.fn(),
    },
    // UX-B6-b — ZoekSelect voor de eigenaar-organisatie (partijen, aard=organisatie).
    partijen: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import ApplicatieFormulier from '@modules/bwb_ontvlechting/frontend/views/ApplicatieFormulier.vue'

const OPTIES = {
  hostingmodel: ['on_premise', 'saas', 'onbekend'],
  migratiepad: ['herbouw', 'vervangen', 'onbekend'],
  complexiteit: ['laag', 'midden', 'hoog'],
  prioriteit: ['laag', 'midden', 'hoog'],
}

async function mountForm({ id = null } = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/applicaties', name: 'applicatie-lijst', component: { template: '<div/>' } },
      { path: '/applicaties/nieuw', name: 'applicatie-nieuw', component: ApplicatieFormulier },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' }, props: true },
    ],
  })
  await router.push(id ? `/applicaties/${id}/bewerken` : '/applicaties/nieuw')
  await router.isReady()
  const pushSpy = vi.spyOn(router, 'push')

  const wrapper = mount(ApplicatieFormulier, {
    props: { id },
    global: { plugins: [[PrimeVue, { unstyled: true }], ToastService, router] },
  })
  await flushPromises()
  return { wrapper, pushSpy }
}

async function kiesOrganisatie(wrapper) {
  await wrapper.find('[data-testid="veld-eigenaar-organisatie-input"]').trigger('focus')
  await flushPromises()
  await wrapper.find('[data-testid="veld-eigenaar-organisatie-optie-org-1"]').trigger('mousedown')
  await flushPromises()
}

async function vulGeldig(wrapper) {
  await wrapper.find('[data-testid="veld-naam"]').setValue('Zaaksysteem')
  await kiesOrganisatie(wrapper)
  await wrapper.find('[data-testid="veld-hostingmodel"]').setValue('saas')
  await wrapper.find('[data-testid="veld-migratiepad"]').setValue('herbouw')
  await wrapper.find('[data-testid="veld-complexiteit"]').setValue('midden')
  await wrapper.find('[data-testid="veld-prioriteit"]').setValue('hoog')
}

beforeEach(() => {
  vi.clearAllMocks()
  api.applicaties.opties.mockResolvedValue(OPTIES)
  api.partijen.lijst.mockResolvedValue({ items: [{ id: 'org-1', naam: 'Gemeente Veldendam', aard: 'organisatie' }], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('ApplicatieFormulier', () => {
  it('vult de dropdowns met de opties uit de backend (met NL-labels)', async () => {
    const { wrapper } = await mountForm()
    const opties = wrapper.find('[data-testid="veld-hostingmodel"]').findAll('option')
    const teksten = opties.map((o) => o.text())
    expect(teksten).toContain('SaaS') // gelabeld
    expect(teksten).toContain('On-premise')
  })

  it('B4: enum-velden tonen gecureerde veldlabels', async () => {
    const { wrapper } = await mountForm()
    const tekst = wrapper.text()
    expect(tekst).toContain('Hostingmodel')
    expect(tekst).toContain('Migratiepad')
    expect(tekst).toContain('Complexiteit')
    expect(tekst).toContain('Prioriteit')
  })

  it('verduidelijkt het leverancier-veld als inventarisatie-notitie (a11y-gekoppeld; ADR-023 Fase D)', async () => {
    const { wrapper } = await mountForm()
    const help = wrapper.find('[data-testid="leverancier-help"]')
    expect(help.exists()).toBe(true)
    expect(help.text()).toContain('contractuele')
    expect(wrapper.find('[data-testid="veld-leverancier"]').attributes('aria-describedby')).toBe('f-leverancier-help')
  })

  it('weigert opslaan bij een lege verplichte naam (clientvalidatie)', async () => {
    const { wrapper } = await mountForm()
    await wrapper.find('[data-testid="applicatie-form"]').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[data-testid="fout-naam"]').exists()).toBe(true)
    expect(api.applicaties.maak).not.toHaveBeenCalled()
  })

  it('roept maak() aan met de payload en navigeert naar detail bij geldige invoer', async () => {
    api.applicaties.maak.mockResolvedValueOnce({ id: 'nieuw-id' })
    const { wrapper, pushSpy } = await mountForm()
    await vulGeldig(wrapper)
    await wrapper.find('[data-testid="applicatie-form"]').trigger('submit')
    await flushPromises()

    expect(api.applicaties.maak).toHaveBeenCalledTimes(1)
    const payload = api.applicaties.maak.mock.calls[0][0]
    expect(payload).toMatchObject({
      naam: 'Zaaksysteem',
      eigenaar_organisatie_id: 'org-1',
      hostingmodel: 'saas',
      migratiepad: 'herbouw',
      complexiteit: 'midden',
      prioriteit: 'hoog',
      beschrijving: null,
    })
    expect(pushSpy).toHaveBeenCalledWith({ name: 'applicatie-detail', params: { id: 'nieuw-id' } })
  })

  it('toont 422-veldfouten van de backend op het juiste veld', async () => {
    const err = new Error('Validatie')
    err.status = 422
    err.detail = [{ loc: ['body', 'naam'], msg: 'te lang' }]
    api.applicaties.maak.mockRejectedValueOnce(err)

    const { wrapper } = await mountForm()
    await vulGeldig(wrapper)
    await wrapper.find('[data-testid="applicatie-form"]').trigger('submit')
    await flushPromises()

    const fout = wrapper.find('[data-testid="fout-naam"]')
    expect(fout.exists()).toBe(true)
    expect(fout.text()).toContain('te lang')
  })

  it('laadt bestaande waarden in de bewerk-modus', async () => {
    api.applicaties.haal.mockResolvedValueOnce({
      id: 'app-9',
      naam: 'Bestaand',
      beschrijving: 'x',
      hostingmodel: 'on_premise',
      eigenaar_organisatie: 'Org',
      eigenaar_naam: null,
      leverancier: null,
      migratiepad: 'vervangen',
      complexiteit: 'hoog',
      prioriteit: 'laag',
    })
    const { wrapper } = await mountForm({ id: 'app-9' })
    expect(wrapper.find('[data-testid="veld-naam"]').element.value).toBe('Bestaand')
    expect(wrapper.find('[data-testid="veld-hostingmodel"]').element.value).toBe('on_premise')
  })
})
