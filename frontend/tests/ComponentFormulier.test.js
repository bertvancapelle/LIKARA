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
    // ADR-028 — rol-opties + BIV-niveaus (ordinaal).
    componentrol_opties: [
      { optie_sleutel: 'interne_applicatie', label: 'Interne applicatie' },
      { optie_sleutel: 'externe_dataprovider', label: 'Externe dataprovider' },
    ],
    biv_niveaus: [
      { optie_sleutel: 'laag', label: 'Laag' },
      { optie_sleutel: 'midden', label: 'Midden' },
      { optie_sleutel: 'hoog', label: 'Hoog' },
    ],
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

  it('aanmaken met type "applicatie" opent het generieke ComponentDetail (LI059)', async () => {
    api.componenten.maak.mockResolvedValueOnce({ id: 'app-new', heeft_applicatie_subtype: true })
    const { w, router } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('Nieuwe applicatie')
    await w.find('[data-testid="veld-componenttype"]').setValue('applicatie')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.maak).toHaveBeenCalledWith(
      expect.objectContaining({ naam: 'Nieuwe applicatie', componenttype: 'applicatie' }),
    )
    expect(router.currentRoute.value.name).toBe('component-detail')
    expect(router.currentRoute.value.params.id).toBe('app-new')
  })

  it('toont de transitie-selects en stuurt ze mee in de payload (LI059)', async () => {
    api.componenten.maak.mockResolvedValueOnce({ id: 'c-1' })
    const { w } = await mountForm()
    expect(w.find('[data-testid="veld-migratiepad"]').exists()).toBe(true)
    expect(w.find('[data-testid="veld-complexiteit"]').exists()).toBe(true)
    expect(w.find('[data-testid="veld-prioriteit"]').exists()).toBe(true)
    await w.find('[data-testid="veld-naam"]').setValue('DB1')
    await w.find('[data-testid="veld-componenttype"]').setValue('database')
    await w.find('[data-testid="veld-migratiepad"]').setValue('uitfaseren')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.maak).toHaveBeenCalledWith(
      expect.objectContaining({ migratiepad: 'uitfaseren', complexiteit: 'midden', prioriteit: 'midden' }),
    )
  })

  it('toont de vrije-tekstvelden eigenaar (naam) en leverancier niet meer (ADR-024)', async () => {
    const { w } = await mountForm()
    expect(w.find('[data-testid="veld-leverancier"]').exists()).toBe(false)
    expect(w.find('[data-testid="veld-eigenaar-naam"]').exists()).toBe(false)
    expect(w.find('[data-testid="leverancier-help"]').exists()).toBe(false)
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

  // ── ADR-028 — rol + BIV ──────────────────────────────────────────────────────
  it('rol staat bij aanmaken standaard op Intern; BIV heeft een lege optie', async () => {
    const { w } = await mountForm()
    expect(w.find('[data-testid="veld-componentrol"]').element.value).toBe('interne_applicatie')
    const bivB = w.find('[data-testid="veld-biv_beschikbaarheid"]')
    expect(bivB.exists()).toBe(true)
    expect(bivB.element.value).toBe('') // niet geclassificeerd
    const legeOptie = bivB.findAll('option').find((o) => o.attributes('value') === '')
    expect(legeOptie.text()).toContain('Niet geclassificeerd')
  })

  it('stuurt rol mee en zet lege BIV op null; een gekozen BIV gaat als sleutel mee', async () => {
    api.componenten.maak.mockResolvedValueOnce({ id: 'c-biv' })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('Koppelbus')
    await w.find('[data-testid="veld-componenttype"]').setValue('fileshare')
    await w.find('[data-testid="veld-componentrol"]').setValue('externe_dataprovider')
    await w.find('[data-testid="veld-biv_vertrouwelijkheid"]').setValue('hoog')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.maak).toHaveBeenCalledWith(
      expect.objectContaining({
        componentrol: 'externe_dataprovider',
        biv_beschikbaarheid: null,
        biv_integriteit: null,
        biv_vertrouwelijkheid: 'hoog',
      }),
    )
  })

  it('foutmapping: 422 ONGELDIGE_ROL landt op het rol-veld, ONGELDIGE_BIV op het BIV-blok', async () => {
    api.componenten.maak.mockRejectedValueOnce({ status: 422, code: 'ONGELDIGE_ROL', message: 'Kies een geldige rol.' })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('X')
    await w.find('[data-testid="veld-componenttype"]').setValue('fileshare')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-componentrol"]').text()).toContain('Kies een geldige rol.')

    api.componenten.maak.mockRejectedValueOnce({ status: 422, code: 'ONGELDIGE_BIV', message: 'Kies een geldige BIV-waarde.' })
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-biv"]').text()).toContain('Kies een geldige BIV-waarde.')
  })

  it('bewerken laadt de bestaande rol + BIV in het formulier', async () => {
    api.componenten.haal.mockResolvedValueOnce({
      id: 'c-9', naam: 'Extern koppelpunt', componenttype: 'fileshare', hostingmodel: 'onbekend',
      heeft_applicatie_subtype: false, migratiepad: 'onbekend', complexiteit: 'midden', prioriteit: 'midden',
      eigenaar_organisatie_id: null, eigenaar_organisatie_naam: '', beschrijving: '',
      componentrol: 'externe_dataprovider', biv_beschikbaarheid: 'laag', biv_integriteit: null, biv_vertrouwelijkheid: 'hoog',
    })
    const router = maakRouter()
    await router.push('/componenten/c-9/bewerken')
    await router.isReady()
    const w = mount(ComponentFormulier, {
      props: { id: 'c-9' },
      attachTo: document.body,
      global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
    })
    await flushPromises()
    expect(w.find('[data-testid="veld-componentrol"]').element.value).toBe('externe_dataprovider')
    expect(w.find('[data-testid="veld-biv_beschikbaarheid"]').element.value).toBe('laag')
    expect(w.find('[data-testid="veld-biv_integriteit"]').element.value).toBe('') // niet geclassificeerd
    expect(w.find('[data-testid="veld-biv_vertrouwelijkheid"]').element.value).toBe('hoog')
  })

  it('bewerken van een applicatie laadt in hetzelfde formulier (geen redirect, LI059)', async () => {
    api.componenten.haal.mockResolvedValueOnce({
      id: 'app-1',
      naam: 'Belastingsysteem',
      componenttype: 'applicatie',
      hostingmodel: 'saas',
      heeft_applicatie_subtype: true,
      migratiepad: 'herbouw',
      complexiteit: 'hoog',
      prioriteit: 'laag',
      eigenaar_organisatie_id: null,
      eigenaar_organisatie_naam: '',
      beschrijving: '',
    })
    const router = maakRouter()
    await router.push('/componenten/app-1/bewerken')
    await router.isReady()
    const pinia = createPinia()
    const w = mount(ComponentFormulier, {
      props: { id: 'app-1' },
      attachTo: document.body,
      global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
    })
    await flushPromises()
    // Geen redirect meer: het applicatie-component wordt hier bewerkt (LI059 Slice 4).
    expect(router.currentRoute.value.name).toBe('component-bewerken')
    expect(w.find('[data-testid="veld-naam"]').element.value).toBe('Belastingsysteem')
    expect(w.find('[data-testid="veld-migratiepad"]').element.value).toBe('herbouw')
    expect(w.find('[data-testid="veld-complexiteit"]').element.value).toBe('hoog')
  })
})
